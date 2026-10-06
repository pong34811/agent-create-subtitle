# นำซับไทยเข้า Subtitle Track 1 ของทั้ง 49 Timeline — aomimama-2026-09-p1

## Goal

นำไฟล์ SRT 49 ไฟล์ที่สร้างเสร็จแล้ว (`runs/aomimama-2026-09-p1/srt/*.draft.srt`) เข้า
Subtitle Track 1 ของแต่ละ Timeline ในโปรเจกต์ Resolve `aomimama-2026-09-p1`
พร้อมตรวจสอบยืนยันด้วยการอ่านกลับ (readback) และใส่สไตล์ Mitr Font ให้ทุก track

## ตอบคำถามตั้งต้น (จากหลักฐานจริง ไม่ใช่ความจำ)

**คำถาม 1: การสร้าง subtitle เสร็จยัง**

| งาน | สถานะ |
|---|---|
| ถอดเสียง (transcripts) | เสร็จ 49/49 |
| สร้าง cue + SRT | เสร็จ 49 ไฟล์, 963 cues |
| ข้อความครบถ้วน | 100.00% (ตรวจแล้ว ไม่หายแม้แต่ตัวเดียว) |
| timestamp อยู่ในช่วงไฟล์ | ผ่านทุกไฟล์ (0 overrun) |
| เว้นวรรคผิดในคำไทย | 0 cue |
| **ตรวจจากคน (human review)** | **ยังไม่ได้ทำ — `approved: false` ทั้ง 49** |
| **นำเข้า Resolve** | **ยังไม่ได้ทำ** |

สรุป: **ไฟล์เสร็จ แต่ "งาน" ยังไม่จบ** เพราะยังไม่มีซับอยู่ในไทม์ไลน์

**คำถาม 2: Timeline ทั้งหมดยังไม่มี subtitle ใน track 1**

ถูกต้อง — ยืนยันจาก `runs/aomimama-2026-09-p1/manifest.json`:

```
subtitle_tracks values: Counter({0: 49})
```

ทั้ง 49 Timeline มีค่า `subtitle_tracks = 0` (ตรวจ ณ 2026-10-06 14:43)

## Current context / assumptions

- **Resolve**: กำลังเปิดอยู่ (Resolve.exe PID 14036), โปรเจกต์ `aomimama-2026-09-p1`,
  Studio 21.1.0.17, ฐานข้อมูลแบบ Disk
- **Timeline**: 49 อัน ทุกอัน 1920x1080 @ 60fps รวม 4473.8 วินาที
- **ไทม์ไลน์เริ่มที่ frame 0 ทุกอัน** (ตรวจแล้ว: ไม่มีอันใดมี `start != 0`)
  → **เวลาใน SRT = เวลาในไทม์ไลน์ ไม่ต้องบวก offset**
- **SRT ทุกไฟล์อยู่ในช่วงความยาวไทม์ไลน์** (ตรวจแล้ว: ไม่มีไฟล์ใดเกิน)
- **SRT เป็น UTF-8 BOM** — `ImportMedia` รองรับได้
- **สคริปต์ preset มีอยู่แล้ว**: `.agents/skills/resolve-mitr-subtitle-presets/scripts/load_subtitle_preset.py`
- **ทุก Timeline เป็นแนวนอน 1920x1080** → ใช้ preset `Mitr Font` (ไม่ต้องแยกแนวตั้ง)
- **ยังไม่มีสคริปต์นำเข้าในรีโป** — ต้องเขียนใหม่ (งานหลักของแผนนี้)

## Architecture / proposed approach

เขียนสคริปต์เดียว `scripts/import_subtitles_resolve.py` ที่เชื่อมต่อ Resolve ผ่าน
scripting bridge, หา Timeline จาก UUID ใน manifest, แล้วทำตามลำดับที่พิสูจน์แล้วว่าได้ผล:
`ImportMedia([srt])` → `AddTrack('subtitle')` → `AppendToTimeline([{'mediaPoolItem': item}])`
จากนั้นอ่านกลับด้วย `GetItemListInTrack('subtitle', 1)` เพื่อยืนยันจำนวน cue และเวลา
สุดท้ายเรียกสคริปต์ preset ที่มีอยู่เพื่อใส่สไตล์ Mitr Font

หลักการสำคัญ 3 ข้อ (มาจากข้อผิดพลาดที่เคยเกิดจริง):
1. **`AddTrack` ต้องมาก่อน `AppendToTimeline`** — ถ้าไม่มี subtitle track ก่อน
   `AppendToTimeline` จะคืนค่าเป็น list ที่ไม่ว่าง แต่**วางอะไรไม่ได้เลย**
2. **ห้าม append ซ้ำใน track เดียวกัน** — มันจะต่อท้ายแทนการใช้ timecode ของตัวเอง
   → ต้องตรวจก่อนว่ามี track อยู่แล้วหรือยัง
3. **เว้นจังหวะระหว่าง append** — การยิงติด ๆ กันทำให้ Resolve crash
   → sleep 0.5 วินาทีต่อ Timeline

## Step-by-step tasks

### Task 0: เตรียม worktree และยืนยันสถานะก่อนแตะ Resolve (อ่านเท่านั้น)

ทำงานในเวิร์กทรีที่มีอยู่แล้ว เพื่อไม่แตะรีโปหลัก:

```bash
cd "C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree"
git status --short
```

ถ้าว่างเปล่า ให้คัดลอก manifest มาเป็นข้อมูลอ้างอิง:

```bash
mkdir -p runs/aomimama-2026-09-p1
cp "C:/Users/warit/Desktop/agent-create-subtitle/runs/aomimama-2026-09-p1/manifest.json" runs/aomimama-2026-09-p1/
```

**ตรวจสอบ**: `ls runs/aomimama-2026-09-p1/manifest.json` ต้องมีไฟล์

### Task 1: เขียนเทสต์ที่ยังไม่ผ่าน (RED)

สร้างไฟล์ `tests/test_import_subtitles.py`:

```python
"""Tests for the Resolve subtitle import helper. No Resolve connection needed."""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import import_subtitles_resolve as imp  # noqa: E402

MAIN_RUN = Path('C:/Users/warit/Desktop/agent-create-subtitle/runs/aomimama-2026-09-p1')


def test_parse_srt_reads_every_cue():
    rows = json.loads((MAIN_RUN / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    checked = 0
    for row in rows:
        srt = MAIN_RUN / 'srt' / f"{row['id']}.draft.srt"
        cues = imp.parse_srt(srt)
        reviewed = json.loads(
            (MAIN_RUN / 'reviewed' / f"{row['id']}.gemini.json").read_text(encoding='utf-8'))
        assert len(cues) == len(reviewed['cues']), f"{row['id']} cue count differs"
        checked += 1
    assert checked == 49


def test_parse_srt_times_match_reviewed_cues():
    rows = json.loads((MAIN_RUN / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    row = rows[0]
    cues = imp.parse_srt(MAIN_RUN / 'srt' / f"{row['id']}.draft.srt")
    reviewed = json.loads(
        (MAIN_RUN / 'reviewed' / f"{row['id']}.gemini.json").read_text(encoding='utf-8'))
    for got, want in zip(cues, reviewed['cues']):
        assert abs(got['start'] - want['start']) < 0.002, (got, want)
        assert got['text'] == want['text']


def test_parse_srt_rejects_a_file_that_does_not_exist(tmp_path):
    with pytest.raises(FileNotFoundError):
        imp.parse_srt(tmp_path / 'nope.srt')


def test_plan_import_flags_timelines_that_already_have_a_track():
    rows = json.loads((MAIN_RUN / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    live = {r['id']: 0 for r in rows}
    live[rows[0]['id']] = 1                      # pretend one already imported
    plan = imp.plan_import(rows, live, replace=False)
    assert plan[0]['action'] == 'skip'
    assert all(p['action'] == 'import' for p in plan[1:])
    assert len(plan) == 49


def test_plan_import_with_replace_imports_everything():
    rows = json.loads((MAIN_RUN / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    live = {r['id']: 2 for r in rows}
    plan = imp.plan_import(rows, live, replace=True)
    assert all(p['action'] == 'replace' for p in plan)


def test_srt_cues_never_exceed_timeline_duration():
    rows = json.loads((MAIN_RUN / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    for row in rows:
        cues = imp.parse_srt(MAIN_RUN / 'srt' / f"{row['id']}.draft.srt")
        duration = (row['end'] - row['start']) / row['fps']
        assert cues[-1]['end'] <= duration + 0.05, row['id']


def test_srt_time_parses_milliseconds():
    assert imp.srt_time('00:00:10,500') == 10.5
    assert imp.srt_time('01:02:03,250') == 3723.25
```

รันเพื่อยืนยันว่าล้มเหลว (โมดูลยังไม่มี):

```bash
cd "C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree"
./../../../../Desktop/agent-create-subtitle/.venv-aomimama/Scripts/python.exe -m pytest tests/test_import_subtitles.py -x -q
```

**ผลที่ต้องเห็น**: `ModuleNotFoundError: No module named 'import_subtitles_resolve'`

ถ้าไม่มี pytest ให้ใช้ venv ของโปรเจกต์:
`"C:/Users/warit/Desktop/agent-create-subtitle/.venv-aomimama/Scripts/python.exe" -m pip install pytest`

### Task 2: เขียนสคริปต์ให้เทสต์ผ่าน (GREEN)

สร้าง `scripts/import_subtitles_resolve.py`:

```python
"""Import the drafted Thai SRTs into Resolve subtitle tracks, then verify by readback.

Sequence per timeline (order matters — see the thai-subtitles-resolve skill):
    ImportMedia([srt]) -> AddTrack('subtitle') -> AppendToTimeline([{mediaPoolItem}])
Adding the track AFTER the append, or appending twice to one track, both silently
misplace captions. Every import is verified by reading the track back.

Run with --dry-run first. Nothing is written without --apply.
"""
import argparse
import json
import re
import sys
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
    uid_path = str(srt_path)
    if replace:
        for idx in range(tl.GetTrackCount('subtitle'), 0, -1):
            tl.DeleteTrack('subtitle', idx)
        stale = [c for c in media_pool.GetRootFolder().GetClipList()
                 if c.GetClipProperty('File Path') == uid_path]
        if stale:
            media_pool.DeleteClips(stale)

    items = media_pool.ImportMedia([uid_path])
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
    assert len(rows) == 49 or args.only, f'expected 49 timelines, got {len(rows)}'

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
        row = next(r for r in rows if r['id'] == entry['id'])
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
```

รันเทสต์:

```bash
cd "C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree"
"C:/Users/warit/Desktop/agent-create-subtitle/.venv-aomimama/Scripts/python.exe" -m pytest tests/test_import_subtitles.py -q
```

**ผลที่ต้องเห็น**: `7 passed`

Commit:

```bash
git add scripts/import_subtitles_resolve.py tests/test_import_subtitles.py
git commit -m "feat(resolve): import drafted Thai SRTs into subtitle tracks with readback verification"
```

### Task 3: Dry run ก่อนแตะ Resolve

```bash
cd "C:/Users/warit/Desktop/agent-create-subtitle"
python scripts/import_subtitles_resolve.py
```

**ผลที่ต้องเห็น**:
- บรรทัดแรกว่า `DRY RUN — nothing will be written`
- `timelines: 49  missing SRT: none`
- ทั้ง 49 บรรทัดลงท้ายด้วย `OK` (ไม่มี `OVERRUN`)

ถ้ามี `OVERRUN` หรือ `missing SRT` ให้หยุดและรายงาน ห้ามไปต่อ

### Task 4: นำเข้าจริงชุดเล็กก่อน (3 Timeline)

ทำทีละน้อยเพื่อพิสูจน์ว่าไม่ crash:

```bash
cd "C:/Users/warit/Desktop/agent-create-subtitle"
python scripts/import_subtitles_resolve.py --apply --only 1 2 3
```

**ผลที่ต้องเห็น**: 3 บรรทัด `OK cues=N/N` แล้ว `TOTAL 3/3 timelines verified`

จากนั้น**ตรวจด้วยตาก่อนไปต่อ**: เปิด Timeline 1 ใน Resolve ดูว่ามีซับขึ้นจริง

### Task 5: นำเข้าที่เหลือทั้งหมด

```bash
cd "C:/Users/warit/Desktop/agent-create-subtitle"
python scripts/import_subtitles_resolve.py --apply
```

**ผลที่ต้องเห็น**: Timeline 1-3 ขึ้น `SKIP (already has 1 track)` และที่เหลือขึ้น `OK`
ปิดท้ายด้วย `TOTAL 49/49 timelines verified`

ถ้า Resolve crash กลางทาง ให้รันซ้ำคำสั่งเดิม — สคริปต์จะข้ามอันที่ทำแล้ว

### Task 6: ตรวจยืนยันแบบอ่านกลับทั้งโปรเจกต์

รัน dry run ซ้ำและอ่านผลจากไฟล์ผลลัพธ์:

```bash
cd /c/Users/warit/Desktop/agent-create-subtitle && python -c "
import json
from pathlib import Path
r=json.loads(Path('runs/aomimama-2026-09-p1/import-results.json').read_text(encoding='utf-8'))
print('timelines recorded:',len(r))
print('ok:',sum(1 for x in r if x.get('ok')))
bad=[x for x in r if not x.get('ok')]
for b in bad: print('  FAIL',b['index'],b.get('error'))
tot=sum(x.get('actual_cues',0) for x in r)
print('total cues in Resolve:',tot)
"
```

**ผลที่ต้องเห็น**: `timelines recorded: 49`, `ok: 49`, `total cues in Resolve: 963`

### Task 7: ใส่สไตล์ Mitr Font ให้ทุก track

หลัง import แล้ว track จะเป็น unstyled stub ต้องใส่ preset:

```bash
cd /c/Users/warit/Desktop/agent-create-subtitle
python .agents/skills/resolve-mitr-subtitle-presets/scripts/load_subtitle_preset.py \
  --preset "Mitr Font" --orientation horizontal
```

อ่านผล dry run ก่อน แล้วรันจริงพร้อม backup:

```bash
python .agents/skills/resolve-mitr-subtitle-presets/scripts/load_subtitle_preset.py \
  --preset "Mitr Font" --orientation horizontal --apply \
  --backup-dir "C:/Users/warit/Documents/resolve-subtitle-preset-backups"
```

**หมายเหตุ**: สคริปต์นี้จะปิด/เปิดโปรเจกต์และเขียน SQLite — ต้องได้อนุมัติจากผู้ใช้ก่อน
ถ้าผู้ใช้ยังไม่อนุมัติ ให้ข้าม Task นี้แล้วรายงานว่า "deferred"

**ผลที่ต้องเห็น**: `changed_tracks: 49` แล้วรัน dry run ซ้ำต้องได้
`0 of 49 subtitle track(s) would change.`

## Tests / validation

| ด่าน | คำสั่ง | ผลที่ต้องได้ |
|---|---|---|
| เทสต์หน่วย (7 ข้อ) | `pytest tests/test_import_subtitles.py -q` | `7 passed` |
| Dry run | `python scripts/import_subtitles_resolve.py` | 49 บรรทัด `OK`, ไม่มี `OVERRUN` |
| ชุดเล็ก | `--apply --only 1 2 3` | `TOTAL 3/3` |
| ทั้งหมด | `--apply` | `TOTAL 49/49` |
| อ่านกลับ | สคริปต์ใน Task 6 | `ok: 49`, `total cues: 963` |
| สไตล์ | preset dry run ซ้ำ | `0 of 49 would change` |

เกณฑ์ผ่านสุดท้าย: **ทุก Timeline มี `GetTrackCount('subtitle') >= 1` และจำนวน cue
ที่อ่านกลับได้ตรงกับจำนวน cue ใน SRT ทุกไฟล์**

## Risks, tradeoffs, and open questions

**ความเสี่ยงสูง**

1. **Resolve crash กลางชุด** — เคยเกิดจริงจากการยิง append ติดกัน กันด้วย sleep 0.5 วิ
   และสั่งรันแบบ resumable (ข้ามอันที่ทำแล้ว) ถ้า crash ให้เปิด Resolve ใหม่แล้วรันซ้ำ

2. **`AppendToTimeline` วางไม่ได้แต่คืนค่าไม่ว่าง** — ถ้าลืม `AddTrack` ก่อน
   สคริปต์ตรวจ `placed` และ `readback` จึงจับได้ ถ้าเจอ `AppendToTimeline placed nothing`
   ให้ตรวจว่ามี subtitle track อยู่จริง

3. **ImportMedia path-cached** — ถ้าต้อง import SRT เดิมซ้ำหลังแก้ไฟล์
   ต้องลบ pool item เก่าก่อน (อยู่ใน `import_one` แล้วเมื่อ `--replace`)

4. **สไตล์ track หายเมื่อ import** — `AddTrack` สร้าง style stub เปล่า
   ต้องรัน preset หลัง import (Task 7)

**ยังไม่ได้ตัดสิน (ต้องถามผู้ใช้)**

5. **การตรวจจากคน** — cue ทั้ง 49 ไฟล์ยัง `approved: false` และมี 14 cue ที่มี flag
   เรื่องเวลา (`timestamp_beyond_duration`, `start_clipped_to_previous`, `overlap_merged`)
   **คำถาม: นำเข้าทั้งหมดเลย หรือให้ตรวจ 14 cue ที่มี flag ก่อน?**

6. **9 ไฟล์ที่ใช้ `gemini-2.5-flash`** — เป็นโมเดลที่อ่อนที่สุดในชุด (เว้นวรรคทุกคำ)
   **คำถาม: นำเข้าตามนี้ก่อน หรือรอโควตา Gemini รีเซ็ต (~17 ชม.) แล้วรันใหม่ให้คุณภาพเท่ากันทั้งชุด?**

7. **`[ฟังไม่ชัด]`** — มี marker นี้ค้างอยู่ใน cue บางอัน
   **คำถาม: นำเข้าพร้อม marker (ให้คนมาแก้ทีหลัง) หรือกรองออกก่อน?**

**ข้อจำกัดที่ต้องยอมรับ**

8. **คุณภาพไม่เท่ากันทั้งชุด** — 49 ไฟล์มาจาก 7 โมเดลต่างกัน เพราะโควตาฟรีหมดระหว่างทาง
   ไม่สามารถทำให้เป็นโมเดลเดียวได้ในตอนนี้

9. **สคริปต์ preset เขียน SQLite** — ต้องปิดโปรเจกต์ก่อน ถ้าปิดไม่ได้ให้หยุด
   ห้ามฝืนเขียน (สคริปต์มี guard อยู่แล้ว)
