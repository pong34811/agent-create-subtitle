"""Offline batch ASR sidecars. Never approves captions or calls Resolve.

Requires a locally cached faster-whisper model (local_files_only=True).
Timeline end is exclusive; WAV zero is timeline start, NOT frame zero.
"""
import argparse
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import site
import wave

from aomimama_caption_core import build_cues, render_srt, validate

TRANSCRIBE_OPTIONS = {
    'language': 'th', 'word_timestamps': True, 'beam_size': 5,
    'temperature': [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    'condition_on_previous_text': False, 'vad_filter': True,
    'vad_parameters': {'min_silence_duration_ms': 400, 'speech_pad_ms': 200},
}
DRAFT_POLICY = {'max_glyphs': 36, 'target_seconds': 4.0, 'pause_seconds': 0.5}


_DLL_HANDLES = []  # retain handles for the lifetime of native inference


def cuda_dll_directories(package_roots):
    directories = []
    for package_root in package_roots:
        root = Path(package_root)
        candidates = [root / 'torch' / 'lib', *sorted((root / 'nvidia').glob('*/bin'))]
        for candidate in candidates:
            if candidate.is_dir() and candidate not in directories:
                directories.append(candidate)
    return directories


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--indices', type=int, nargs='+', help='manifest indices; default all')
    parser.add_argument('--model', default='large-v3')
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--compute', choices=('int8', 'float16'), default='int8')
    return parser.parse_args(argv)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def _wav_metadata(path):
    with wave.open(str(path), 'rb') as wav:
        frames, rate = wav.getnframes(), wav.getframerate()
        channels, width = wav.getnchannels(), wav.getsampwidth()
        if wav.getcomptype() != 'NONE' or frames <= 0 or rate <= 0:
            raise ValueError(f'invalid PCM WAV: {path}')
        remaining = frames * channels * width
        while remaining:
            block = wav.readframes(min(65536, max(1, remaining // (channels*width))))
            if not block:
                raise ValueError(f'truncated WAV data: {path}')
            remaining -= len(block)
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            digest.update(block)
    return {'sha256': digest.hexdigest(), 'frames': frames, 'sample_rate': rate,
            'channels': channels, 'sample_width': width, 'duration_seconds': frames/rate}


def validate_transcript(raw):
    """Reject incomplete/corrupt sidecars; explicit [] alone means no speech."""
    def number(value):
        return type(value) in (int, float) and math.isfinite(value)

    def require(condition):
        if not condition:
            raise ValueError('invalid raw transcript schema; human reconciliation required')

    require(isinstance(raw, dict))
    metadata = raw.get('metadata')
    require(isinstance(metadata, dict) and type(metadata.get('schema_version')) is int
            and metadata['schema_version'] == 1)
    for key in ('project', 'model', 'device', 'compute_type', 'faster_whisper_version'):
        require(isinstance(metadata.get(key), str) and bool(metadata[key]))
    for key in ('timeline', 'transcribe_options', 'audio'):
        require(isinstance(metadata.get(key), dict))
    audio, timeline = metadata['audio'], metadata['timeline']
    require(isinstance(audio.get('sha256'), str) and len(audio['sha256']) == 64
            and all(c in '0123456789abcdef' for c in audio['sha256']))
    for key in ('frames', 'sample_rate', 'channels', 'sample_width'):
        require(type(audio.get(key)) is int and audio[key] > 0)
    require(number(audio.get('duration_seconds')) and audio['duration_seconds'] > 0
            and audio['duration_seconds'] == audio['frames'] / audio['sample_rate'])
    require(type(timeline.get('index')) is int and isinstance(timeline.get('id'), str)
            and bool(timeline['id']) and isinstance(timeline.get('name'), str))
    for key in ('start', 'end', 'fps'):
        require(number(timeline.get(key)))
    require(timeline['fps'] > 0 and timeline['end'] > timeline['start'])
    require(set(TRANSCRIBE_OPTIONS).issubset(metadata['transcribe_options']))
    require(number(raw.get('duration_seconds')) and raw['duration_seconds'] > 0)
    info = raw.get('info')
    require(isinstance(info, dict) and isinstance(info.get('language'), str))
    for key in ('language_probability', 'duration', 'duration_after_vad'):
        require(number(info.get(key)))
    require(0 <= info['language_probability'] <= 1
            and 0 <= info['duration_after_vad'] <= info['duration'])
    require(isinstance(raw.get('segments'), list))
    for segment in raw['segments']:
        require(isinstance(segment, dict))
        for key in ('id', 'seek'):
            require(type(segment.get(key)) is int and segment[key] >= 0)
        for key in ('start', 'end', 'avg_logprob', 'no_speech_prob', 'compression_ratio', 'temperature'):
            require(number(segment.get(key)))
        require(0 <= segment['start'] <= segment['end']
                and 0 <= segment['no_speech_prob'] <= 1)
        require(isinstance(segment.get('text'), str) and isinstance(segment.get('words'), list))
        for word in segment['words']:
            require(isinstance(word, dict) and isinstance(word.get('word'), str))
            for key in ('start', 'end', 'probability'):
                require(number(word.get(key)))
            require(0 <= word['start'] <= word['end'] and 0 <= word['probability'] <= 1)
    return True


def run(args, *, model_factory=None):
    root = args.run_root
    if not root.is_absolute():
        raise ValueError('--run-root must be absolute')
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    timelines = manifest['timelines']
    if len({t['id'] for t in timelines}) != len(timelines) or len({t['index'] for t in timelines}) != len(timelines):
        raise ValueError('duplicate timeline id or index in manifest')
    requested = set(args.indices) if args.indices else None
    selected = [t for t in timelines if requested is None or t['index'] in requested]
    if requested is not None and requested != {t['index'] for t in selected}:
        raise ValueError('requested timeline index is not in manifest')
    jobs = []
    for timeline in selected:
        identifier = timeline['id']
        if not isinstance(identifier, str) or not identifier or any(c in identifier for c in '/\\:') or identifier in {'.', '..'}:
            raise ValueError('unsafe timeline id')
        fps = float(timeline['fps'])
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError(f'fps must be finite and positive: {identifier}')
        expected = (float(timeline['end']) - float(timeline['start'])) / fps
        wav = root / 'audio' / f'{identifier}.wav'
        audio = _wav_metadata(wav)
        if not math.isfinite(expected) or expected <= 0 or abs(audio['duration_seconds']-expected) > max(1/fps, 0.01):
            raise ValueError(f'WAV duration mismatch for {identifier}: {audio["duration_seconds"]} vs {expected}')
        metadata = {'schema_version': 1, 'project': manifest['project'], 'timeline': timeline,
                    'model': args.model, 'device': args.device, 'compute_type': args.compute,
                    'faster_whisper_version': version('faster-whisper'),
                    'transcribe_options': TRANSCRIBE_OPTIONS, 'audio': audio}
        jobs.append((timeline, wav, metadata, expected))
    model = None
    results = []
    for timeline, wav, metadata, duration in jobs:
        identifier = timeline['id']
        print(f'[{timeline["index"]}] {identifier}: starting', flush=True)
        raw_path = root / 'transcripts' / f'{identifier}.json'
        transcript = None
        if raw_path.exists():
            try:
                candidate = json.loads(raw_path.read_text(encoding='utf-8'))
            except (ValueError, UnicodeError) as error:
                raise ValueError(f'corrupt raw cache; human reconciliation required: {raw_path}') from error
            validate_transcript(candidate)
            if candidate.get('metadata') == metadata:
                if candidate['duration_seconds'] != duration:
                    raise ValueError('cached duration differs; human reconciliation required')
                transcript = candidate
                print(f'[{timeline["index"]}] {identifier}: resuming exact metadata', flush=True)
        if transcript is None:
            if model is None:
                if model_factory is None:
                    if os.name == 'nt' and args.device == 'cuda':
                        directories = cuda_dll_directories(site.getsitepackages())
                        for directory in directories:
                            _DLL_HANDLES.append(os.add_dll_directory(str(directory)))
                        if directories:
                            os.environ['PATH'] = os.pathsep.join(map(str, directories)) + os.pathsep + os.environ.get('PATH', '')
                    from faster_whisper import WhisperModel
                    model_factory = WhisperModel
                print(f'loading {args.model} on {args.device}/{args.compute} (local cache only)', flush=True)
                model = model_factory(args.model, device=args.device, compute_type=args.compute,
                                      local_files_only=True)
            segments, info = model.transcribe(str(wav), **TRANSCRIBE_OPTIONS)
            serialized = []
            for segment in segments:
                serialized.append({
                    'id': segment.id, 'seek': segment.seek, 'start': segment.start,
                    'end': segment.end, 'text': segment.text,
                    'avg_logprob': segment.avg_logprob, 'no_speech_prob': segment.no_speech_prob,
                    'compression_ratio': segment.compression_ratio, 'temperature': segment.temperature,
                    'words': [{'word': w.word, 'start': w.start, 'end': w.end,
                               'probability': w.probability} for w in (segment.words or [])],
                })
            if _wav_metadata(wav) != metadata['audio']:
                raise ValueError(f'WAV changed during decode: {identifier}')
            transcript = {'metadata': metadata, 'duration_seconds': duration,
                          'info': {'language': info.language, 'language_probability': info.language_probability,
                                   'duration': info.duration, 'duration_after_vad': info.duration_after_vad},
                          'segments': serialized}
            validate_transcript(transcript)
            if raw_path.exists():
                old_bytes = raw_path.read_bytes()
                old_hash = hashlib.sha256(old_bytes).hexdigest()
                archive = raw_path.parent / 'archive' / f'{identifier}.{old_hash}.json'
                archive.parent.mkdir(parents=True, exist_ok=True)
                if not archive.exists():
                    archive.write_bytes(old_bytes)
            _write_json(raw_path, transcript)
        cues = build_cues(transcript, duration, **DRAFT_POLICY)
        reviewed_path = root / 'reviewed' / f'{identifier}.json'
        draft = {'approved': False, 'metadata': metadata, 'draft_policy': DRAFT_POLICY,
                 'duration_seconds': duration, 'cues': cues,
                 'qc_required': True, 'status': 'unreviewed_draft'}
        if reviewed_path.exists():
            previous_draft = json.loads(reviewed_path.read_text(encoding='utf-8'))
            if previous_draft != draft:
                raise ValueError(f'existing review differs; preserve and reconcile manually: {reviewed_path}')
        else:
            _write_json(reviewed_path, draft)
        srt_path = root / 'srt' / f'{identifier}.draft.srt'
        srt_path.parent.mkdir(parents=True, exist_ok=True)
        srt_path.write_text(render_srt(cues), encoding='utf-8')
        validate(cues, duration)
        result = {'index': timeline['index'], 'id': identifier, 'cue_count': len(cues),
                  'transcript': str(raw_path), 'reviewed': str(reviewed_path), 'draft_srt': str(srt_path),
                  'approved': False}
        results.append(result)
        print(f'[{timeline["index"]}] {identifier}: {len(cues)} cues, unapproved draft written', flush=True)
    return results


def main(argv=None):
    args = parse_args(argv)
    run(args)


if __name__ == '__main__':
    main()
