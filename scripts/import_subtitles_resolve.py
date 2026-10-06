"""Import the drafted Thai SRTs into Resolve subtitle tracks, then verify by readback.

Sequence per timeline (order matters — see the thai-subtitles-resolve skill):
    ImportMedia([srt]) -> AddTrack('subtitle') -> AppendToTimeline([{mediaPoolItem}])
Adding the track AFTER the append, or appending twice to one track, both silently
misplace captions. Every import is verified by reading the track back.

Run with no flags first (dry run). Nothing is written without --apply.
"""
import argparse
import json
import re
import time
from pathlib import Path

RUN_ROOT = Path('C:/Users/warit/Desktop/agent-create-subtitle/runs/aomimama-2026-09-p1')
MANIFEST = RUN_ROOT / 'manifest.json'
SRT_DIR = RUN_ROOT / 'srt'
RESULTS = RUN_ROOT / 'import-results.json'
SLEEP_BETWEEN_APPENDS = 0.5


def srt_time(text):
    """'00:00:10,500' -> 10.5 seconds."""
    h, m, rest = text.split(':')
    s, ms = rest.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path):
    """Read an SRT into [{start, end, text}] with times in seconds."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = path.read_text(encoding='utf-8-sig')
    cues = []
    for block in raw.strip().split('\n\n'):
        lines = [ln for ln in block.split('\n') if ln.strip()]
        if len(lines) < 2:
            continue
        match = re.search(
            r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', block)
        if not match:
            continue
        body = lines[2:] if lines[0].strip().isdigit() else lines[1:]
        cues.append({'start': srt_time(match.group(1)), 'end': srt_time(match.group(2)),
                     'text': ' '.join(body).strip()})
    return cues


def plan_import(rows, live_track_counts, replace):
    """Decide per timeline: import, replace, or skip. Pure — no Resolve needed."""
    plan = []
    for row in rows:
        have = live_track_counts.get(row['id'], 0)
        if have and not replace:
            action = 'skip'
        elif have:
            action = 'replace'
        else:
            action = 'import'
        plan.append({'index': row['index'], 'id': row['id'], 'name': row['name'],
                     'action': action, 'existing_tracks': have})
    return plan


def connect():
    """Return (resolve, project, media_pool) using Resolve's own bridge."""
    import os
    api = r'C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting'
    lib = r'C:\Program Files\Blackmagic Design\DaVinci Resolve'
    os.environ['RESOLVE_SCRIPT_API'] = api
    os.environ['RESOLVE_SCRIPT_LIB'] = lib + r'\fusionscript.dll'
    os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + ';' + api + r'\Modules'
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(lib)
    import DaVinciResolveScript as dvr
    resolve = dvr.scriptapp('Resolve')
    if resolve is None:
        raise SystemExit('cannot reach Resolve — is it running with scripting enabled?')
    project = resolve.GetProjectManager().GetCurrentProject()
    return resolve, project, project.GetMediaPool()


def find_timeline(project, uid):
    for i in range(1, project.GetTimelineCount() + 1):
        tl = project.GetTimelineByIndex(i)
        if tl.GetUniqueId() == uid:
            return tl
    return None


def live_track_counts(project, rows):
    """Read how many subtitle tracks each timeline has right now."""
    counts = {}
    for row in rows:
        tl = find_timeline(project, row['id'])
        counts[row['id']] = tl.GetTrackCount('subtitle') if tl else -1
    return counts


def readback(tl, fps):
    """Return (count, first_start_s, last_start_s) for the highest subtitle track."""
    idx = tl.GetTrackCount('subtitle')
    if idx < 1:
        return 0, None, None
    items = tl.GetItemListInTrack('subtitle', idx) or []
    if not items:
        return 0, None, None
    starts = sorted(round(i.GetStart() / fps, 3) for i in items)
    return len(items), starts[0], starts[-1]


def import_one(project, media_pool, tl, srt_path, fps, replace):
    """Import one SRT into the timeline's subtitle track. Returns a result dict."""
    target = str(srt_path)
    if replace:
        for idx in range(tl.GetTrackCount('subtitle'), 0, -1):
            tl.DeleteTrack('subtitle', idx)
        stale = [c for c in media_pool.GetRootFolder().GetClipList()
                 if c.GetClipProperty('File Path') == target]
        if stale:
            media_pool.DeleteClips(stale)

    items = media_pool.ImportMedia([target])
    if not items:
        return {'ok': False, 'error': 'ImportMedia returned nothing'}
    item = items[0]
    kind = item.GetClipProperty('Type')
    if kind != 'Subtitle':
        return {'ok': False, 'error': f'imported as {kind!r}, expected Subtitle'}

    tl.AddTrack('subtitle')                       # MUST precede the append
    placed = media_pool.AppendToTimeline([{'mediaPoolItem': item}])
    if not placed:
        return {'ok': False, 'error': 'AppendToTimeline placed nothing'}

    time.sleep(SLEEP_BETWEEN_APPENDS)
    count, first, last = readback(tl, fps)
    expected = parse_srt(srt_path)
    return {'ok': count == len(expected),
            'expected_cues': len(expected), 'actual_cues': count,
            'expected_first': expected[0]['start'], 'actual_first': first,
            'expected_last': expected[-1]['start'], 'actual_last': last,
            'error': None if count == len(expected) else 'cue count mismatch'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='actually write to Resolve')
    ap.add_argument('--replace', action='store_true', help='delete existing tracks first')
    ap.add_argument('--only', type=int, nargs='*', help='timeline indexes to process')
    args = ap.parse_args()

    rows = json.loads(MANIFEST.read_text(encoding='utf-8'))['timelines']
    if args.only:
        rows = [r for r in rows if r['index'] in args.only]
    assert rows, 'no timelines selected'

    if not args.apply:
        print('DRY RUN — nothing will be written')
        missing = [r['index'] for r in rows if not (SRT_DIR / f"{r['id']}.draft.srt").is_file()]
        print(f'timelines: {len(rows)}  missing SRT: {missing or "none"}')
        for r in rows:
            cues = parse_srt(SRT_DIR / f"{r['id']}.draft.srt")
            duration = (r['end'] - r['start']) / r['fps']
            flag = 'OK' if cues[-1]['end'] <= duration + 0.05 else 'OVERRUN'
            print(f"  {r['index']:>3} {r['id'][:8]} cues={len(cues):>3} "
                  f"last={cues[-1]['end']:>7.2f}s dur={duration:>7.2f}s {flag}")
        return

    resolve, project, media_pool = connect()
    counts = live_track_counts(project, rows)
    plan = plan_import(rows, counts, args.replace)
    results = []
    for entry in plan:
        if entry['action'] == 'skip':
            print(f"  {entry['index']:>3} SKIP (already has {entry['existing_tracks']} track)")
            results.append({**entry, 'ok': True, 'skipped': True})
            continue
        tl = find_timeline(project, entry['id'])
        if tl is None:
            print(f"  {entry['index']:>3} MISSING TIMELINE {entry['id']}")
            results.append({**entry, 'ok': False, 'error': 'timeline not found'})
            continue
        fps = float(tl.GetSetting('timelineFrameRate') or 60)
        result = import_one(project, media_pool, tl, SRT_DIR / f"{entry['id']}.draft.srt",
                            fps, replace=entry['action'] == 'replace')
        results.append({**entry, **result, 'fps': fps})
        status = 'OK' if result['ok'] else f"FAIL {result.get('error')}"
        print(f"  {entry['index']:>3} {status} cues={result.get('actual_cues')}"
              f"/{result.get('expected_cues')}")
        time.sleep(SLEEP_BETWEEN_APPENDS)

    # MERGE with any earlier run so a targeted re-run cannot erase verified state.
    previous = {}
    if RESULTS.exists():
        for old in json.loads(RESULTS.read_text(encoding='utf-8')):
            previous[old['id']] = old
    for r in results:
        previous[r['id']] = r
    merged = sorted(previous.values(), key=lambda r: r['index'])
    RESULTS.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')

    ok = sum(1 for r in merged if r.get('ok'))
    print(f'\nTOTAL {ok}/{len(merged)} timelines verified in {RESULTS}')


if __name__ == '__main__':
    main()
