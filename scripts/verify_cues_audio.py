"""Check draft SRT cues against the audio's speech-band energy (no model, no network).

This is an objective plausibility check, NOT a substitute for listening: game audio
has music and effects, so energy only shows that *something* is audible. It catches
the failures that matter most for sync: cues over silence, cues whose onset is far
from the nearest audio onset, and cues that run past the end of the file.

  python scripts/verify_cues_audio.py                # every timeline with SRT + WAV
  python scripts/verify_cues_audio.py --only 36 8    # manifest indices
  python scripts/verify_cues_audio.py --srt X.srt --wav X.wav   # one pair

Writes <run>/audio-verification.json and prints one line per timeline. Exit code 1
when any cue is flagged, so it can gate a pipeline.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_subtitles_resolve import parse_srt  # noqa: E402  (stdlib-only at import time)

RUN_ROOT = Path(os.environ.get('AOMIMAMA_RUN_ROOT') or Path(__file__).resolve().parents[1] / 'runs' / 'aomimama-2026-09-p1')
RATE = 16000
FRAME_S = 0.05
BAND = 'highpass=f=100,lowpass=f=4000'   # speech band; drops rumble and hiss
MIN_ACTIVE_FRACTION = 0.35               # a cue over silence has almost no active frames
MAX_ONSET_DRIFT_S = 0.8                  # nearest audio onset vs cue start
SEARCH_S = 1.5


def load_energy(wav):
    """Decode to 16 kHz mono and return per-frame RMS in dB."""
    proc = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(wav), '-af', BAND, '-ac', '1', '-ar', str(RATE),
         '-f', 's16le', '-'], capture_output=True, check=True)
    samples = np.frombuffer(proc.stdout, dtype='<i2').astype(np.float32) / 32768.0
    size = int(RATE * FRAME_S)
    frames = len(samples) // size
    if frames == 0:
        return np.zeros(0), 0.0
    rms = np.sqrt((samples[:frames * size].reshape(frames, size) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms), len(samples) / RATE


def active_mask(db):
    """Frames louder than the clip's own noise floor (adaptive, not a fixed dB gate)."""
    if db.size == 0:
        return np.zeros(0, dtype=bool)
    floor = np.percentile(db, 20)
    top = np.percentile(db, 95)
    return db > floor + max(6.0, 0.25 * (top - floor))


def check_cues(cues, mask, duration):
    flags = []
    for i, cue in enumerate(cues, 1):
        a, b = int(cue['start'] / FRAME_S), max(int(cue['end'] / FRAME_S), int(cue['start'] / FRAME_S) + 1)
        window = mask[a:b]
        fraction = float(window.mean()) if window.size else 0.0
        lo, hi = max(0, int((cue['start'] - SEARCH_S) / FRAME_S)), int((cue['start'] + SEARCH_S) / FRAME_S)
        onsets = [j for j in range(lo, min(hi, mask.size)) if mask[j] and (j == 0 or not mask[j - 1])]
        drift = min((abs(j * FRAME_S - cue['start']) for j in onsets), default=None)
        problems = []
        if cue['end'] <= cue['start']:
            problems.append('non_positive_duration')
        if cue['end'] > duration + 0.05:
            problems.append('past_end_of_audio')
        if fraction < MIN_ACTIVE_FRACTION:
            problems.append('little_audio_under_cue')
        if drift is None or drift > MAX_ONSET_DRIFT_S:
            problems.append('no_audio_onset_near_start')
        if problems:
            flags.append({'cue': i, 'start': round(cue['start'], 2), 'end': round(cue['end'], 2),
                          'text': cue['text'], 'active_fraction': round(fraction, 2),
                          'onset_drift_s': None if drift is None else round(drift, 2),
                          'problems': problems})
    return flags


def verify_pair(srt, wav):
    cues = parse_srt(srt)
    db, duration = load_energy(wav)
    mask = active_mask(db)
    overlaps = sum(1 for a, b in zip(cues, cues[1:]) if b['start'] < a['end'] - 1e-6)
    flags = check_cues(cues, mask, duration)
    return {'cues': len(cues), 'audio_seconds': round(duration, 2), 'overlaps': overlaps,
            'flagged': len(flags), 'flags': flags}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--only', type=int, nargs='+')
    parser.add_argument('--srt', type=Path)
    parser.add_argument('--wav', type=Path)
    args = parser.parse_args()
    if args.srt or args.wav:
        if not (args.srt and args.wav):
            parser.error('--srt and --wav go together')
        result = verify_pair(args.srt, args.wav)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1 if result['flagged'] or result['overlaps'] else 0)
    rows = json.loads((RUN_ROOT / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    report, any_flag = {}, False
    for row in rows:
        if args.only and row['index'] not in args.only:
            continue
        srt = RUN_ROOT / 'srt' / f"{row['id']}.draft.srt"
        wav = RUN_ROOT / 'audio' / f"{row['id']}.wav"
        if not (srt.is_file() and wav.is_file()):
            print(row['index'], 'SKIP (need both srt and wav)')
            continue
        result = verify_pair(srt, wav)
        report[row['id']] = {'index': row['index'], 'name': row['name'], **result}
        any_flag |= bool(result['flagged'] or result['overlaps'])
        print(row['index'], f"cues={result['cues']} flagged={result['flagged']} overlaps={result['overlaps']}", flush=True)
    out = RUN_ROOT / 'audio-verification.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('wrote', out)
    sys.exit(1 if any_flag else 0)


if __name__ == '__main__':
    main()
