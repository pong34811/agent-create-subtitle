"""Transcribe long timelines in bounded chunks to stop timestamp drift.

Long clips (>~100s) make Gemini place the back half of the timeline past the end
of the file (a 116s clip came back with segments at 150s). Stating the duration in
the prompt fixes most files but not the longest ones, so here the audio is split
at its quietest points and each chunk is transcribed separately; timestamps are
then offset back into the parent timeline. Each request only has to track <=45s,
which the model does reliably.

Usage:  python scripts/transcribe_chunked.py <index> [<index> ...]
"""
import array
import json
import subprocess
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemini_direct_transcribe as g  # noqa: E402

RUN_ROOT = g.RUN_ROOT
CHUNK_SECONDS = 45.0


def energy_per_second(wav_path):
    with wave.open(str(wav_path)) as f:
        rate = f.getframerate()
        samples = array.array('h', f.readframes(f.getnframes()))
    out = []
    for i in range(0, len(samples) - rate, rate):
        block = samples[i:i + rate]
        out.append((sum(x * x for x in block) / len(block)) ** 0.5)
    return out, rate


def choose_splits(energy, total_seconds):
    """Pick cut points near each CHUNK_SECONDS multiple, at the local energy minimum.

    Cutting on a quiet second avoids slicing a word in half.
    """
    splits, target = [], CHUNK_SECONDS
    while target < total_seconds - 5:
        lo = max(0, int(target) - 8)
        hi = min(len(energy), int(target) + 8)
        if hi <= lo:
            splits.append(target)
        else:
            best = min(range(lo, hi), key=lambda i: energy[i])
            splits.append(float(best))
        target = splits[-1] + CHUNK_SECONDS
    return splits


def cut(wav_path, start, end, dest):
    subprocess.run(
        ['ffmpeg', '-y', '-v', 'error', '-ss', f'{start:.3f}', '-to', f'{end:.3f}',
         '-i', str(wav_path), '-ar', '16000', '-ac', '1', str(dest)],
        check=True)
    return dest


def transcribe(index, key):
    rows = json.loads((RUN_ROOT / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    row = next(r for r in rows if r['index'] == index)
    uid = row['id']
    wav = RUN_ROOT / 'audio' / f'{uid}.wav'
    energy, _ = energy_per_second(wav)
    with wave.open(str(wav)) as f:
        total = f.getnframes() / f.getframerate()

    bounds = [0.0] + choose_splits(energy, total) + [total]
    bounds = sorted(set(round(b, 3) for b in bounds))
    print(f'index {index} {uid[:8]} dur={total:.1f}s chunks={len(bounds)-1} '
          f'cuts={[round(b, 1) for b in bounds[1:-1]]}', flush=True)

    tmp = RUN_ROOT / 'audio' / 'chunks'
    tmp.mkdir(parents=True, exist_ok=True)
    merged, models = [], []
    for n, (a, b) in enumerate(zip(bounds, bounds[1:]), 1):
        piece = tmp / f'{uid}.part{n}.wav'
        cut(wav, a, b, piece)
        result, usage = g.call_with_fallback(key, piece, b - a)
        models.append(usage.get('model_used'))
        for s in result.get('segments') or []:
            merged.append({'start': round(s['start'] + a, 3), 'end': round(s['end'] + a, 3),
                           'text': s['text'], 'uncertain': bool(s.get('uncertain')),
                           'chunk': n})
        print(f'   chunk {n}: {a:.1f}-{b:.1f}s -> {result.get("segment_count", 0)} segments '
              f'[{usage.get("model_used")}]', flush=True)
        piece.unlink()
        time.sleep(3)

    merged.sort(key=lambda s: s['start'])
    over = [s for s in merged if s['end'] > total + 0.5]
    assert not over, f'chunked run still overruns: {over[:2]}'
    assert merged, 'no speech recovered'
    out = {'metadata': {'model': 'chunked:' + ','.join(sorted(set(models))),
                        'route': 'google-generativeai-direct',
                        'timeline_index': index, 'timeline_id': uid,
                        'timeline_name': row['name'],
                        'expected_duration_seconds': (row['end'] - row['start']) / row['fps'],
                        'chunk_seconds': CHUNK_SECONDS,
                        'chunk_boundaries': bounds},
           'duration_seconds': (row['end'] - row['start']) / row['fps'],
           'gemini': {'audio_available': True, 'duration_seconds': total,
                      'segments': merged, 'segment_count': len(merged)}}
    dest = RUN_ROOT / 'transcripts' / f'{uid}.gemini.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'   SAVED {len(merged)} segments, max end {max(s["end"] for s in merged):.1f}s '
          f'<= {total:.1f}s', flush=True)
    return len(merged)


def main():
    key = g.api_key()
    for arg in sys.argv[1:]:
        transcribe(int(arg), key)


if __name__ == '__main__':
    main()
