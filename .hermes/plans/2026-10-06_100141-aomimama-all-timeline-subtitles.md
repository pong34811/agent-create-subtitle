# Plan: Thai subtitles for every timeline in aomimama-2026-09-p1

> Execution is NOT authorized in this planning turn. Approve this plan before modifying Resolve, installing dependencies, rendering audio, or implementing the helper files below.

## Confirmed caption policy — supersedes the short-cue draft below

ผู้ใช้ยืนยันให้ใช้ซับเป็นวลี แบ่งข้อความยาวตามความหมายและจังหวะพูด โดยเก็บคำพูดครบ ไม่ตัดคำติดกันหรือชื่อเฉพาะ และไม่แบ่งสั้นจนเสียความหมาย วลี 4–5 คำคงไว้ได้เมื่ออ่านทันและไม่แน่นภาพ; จำนวนคำเป็นสัญญาณให้ตรวจ ไม่ใช่เพดานบังคับ เวลาบนจอต้องสัมพันธ์กับเสียงและความยาววลี ไม่บังคับทุกซับให้ไม่เกิน 1.5 วินาที และไม่ค้างผ่านช่วงเงียบ

สถานะ: ยืนยันรูปแบบซับเท่านั้น ยังไม่ใช่อนุมัติให้เริ่มดำเนินงาน ข้อกำหนด 3 คำ/1.5 วินาทีและ code/tests ตัวอย่างด้านล่างเป็น draft ที่ถูกแทนที่แล้ว ห้ามคัดลอกไป implement โดยตรง ก่อนดำเนินงานต้องปรับ grouping/validation/tests ให้ตรวจการรักษาข้อความ จังหวะวลี และ readability จาก viewer จริง แทน hard cap เดิม พร้อมนำเสนอเกณฑ์ที่ยังขาดหากจำเป็น ไม่เดาขนาดฟอนต์หรือเพดานอักขระเอง

## Goal

สร้างซับบทพูดภาษาไทยบน native Subtitle track ให้ครบทุก Timeline ของ `aomimama-2026-09-p1` พร้อม SRT และหลักฐานตรวจข้อความ เวลา และการไม่เปลี่ยนงานตัดต่อเดิม

## Current context / evidence

Workspace: `C:/Users/warit/Desktop/agent-create-subtitle`; branch `main`; read-only `git status --short` was empty on 2026-10-06. Live Resolve bridge successfully reported the exact target project, 49 unique timeline IDs and 49 unique names. Every timeline has start frame 0, frame rate 60, raster 1920×1080, one audio track containing one item, zero subtitle tracks and zero subtitle cues. Source paths for all audio items exist. Total timeline duration reported by the tool is 4473.833333333334 seconds. Re-enumerate immediately before execution; this is a snapshot, not permission to ignore later edits.

The supplied screenshot shows the project and existing avatar/live-chat layout. Preserve it. The screenshot is not an authoritative complete timeline inventory.

Files inspected:
- `transcribe_caption_jobs.py`: loads `timeline_caption_jobs.json` at import, CPU large-v3, writes `transcripts_raw/K404_*`.
- `transcribe_thai_finetuned.py`: CUDA transformers ASR, same old jobs, writes `transcripts_thai/K404_*`.
- `build_caption_assets.py`: import-time processing; old word/confidence thresholds, four-word groups and ASS overlay output.
- `build_thai_caption_assets.py`: old project-specific substitutions and segment-weight timing, four-word groups and ASS overlays.
- `timeline_caption_jobs.json`: targets K404/Katy404, NOT Aomi-mama.

Do not run any of those four scripts unchanged. Do not overwrite that jobs file or existing K404 assets. No README.md or AGENTS.md was found in the workspace search. The live default Python is 3.14.7; faster_whisper, torch and pythainlp are absent in that interpreter. FFmpeg is available. Resolve bridge module exists at `C:/ProgramData/Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting/Modules/DaVinciResolveScript.py`.

`TimelineItem.GetProperty('Speed')` returned boolean False for every audio item. False means unavailable, NOT proven 100% speed. Source offsets were readable, but direct source trim extraction is deliberately not selected until retiming can be independently established.

### Skills and delegation

Loaded: `superpowers:brainstorming`, `superpowers:subagent-driven-development`, `superpowers:executing-plans`, `thai-subtitles-resolve`, `thai-proofread`, `resolve-mitr-subtitle-presets`.

`grill-with-docs` and `Subagent Delegation` were not found by their exact names; a skill listing and filename search did not find grill-with-docs. Do not claim they ran or install substitute plugins. Use native `delegate_task` for delegation. At execution, reload relevant skills; use subagent-driven-development for helper implementation/review, and executing-plans only if the user chooses inline execution. They are alternatives, not two simultaneous implementer controllers. No subagent was dispatched during this planning turn.

Classification: bounded operational batch using the existing subtitle workflow, not a new subtitle platform. The explicit /plan instructions override the skill's default no-plan-file rule for bounded work. This plan is the design-review artifact; no separate committed spec is required here.

## Architecture / proposed approach

Render each existing timeline's audible mix to a new 16 kHz mono WAV with time zero at timeline start; this preserves edits/retiming without interpreting the unavailable Speed property. Use a single local CPU faster-whisper worker, review Thai transcripts, build brief SRT cues from character-aligned word fragments, then have one controller import them serially onto native Subtitle tracks and read them back. Keep source media, existing timelines, video/audio clips, and old K404 assets unchanged; no Text+, ASS overlays, extra timelines, SQL writes, or style preset application.

### Alternatives considered

1. Selected: timeline-mix WAV → local ASR → reviewed SRT → native subtitle import. Slower audio-render setup, but correct for the actual audible timeline.
2. Direct ffmpeg trim of source media: faster, but needs proven speed/source mapping; current API evidence does not establish it.
3. Resolve automatic transcription: potentially simpler, but Thai availability and quality on this installation are not verified; do not assume support.

### Global constraints

- Exact target project name; identify timelines by UUID after discovery, never fuzzy names or index alone.
- Include all 49 timelines in the manifest and one execution checklist item per timeline. If inventory changes, stop and reconcile the scope before import.
- User requested subtitles, not style changes. Preserve existing style if new work is encountered; new track uses Resolve defaults and reports styling as not requested. Mitr presets are optional follow-up requiring approval, especially SQLite writes.
- Native Subtitle tracks only. No source-media modification, layout change, SFX/BGM/GIF addition or timeline creation.
- New-cue default: max 3 dictionary words per cue, max 1.5 s display, pause break at ≥0.7 s, at least one frame gap where feasible. ~14 Thai characters is a readability target, not a license to drop or corrupt a long word. Do not transfer Katy404-specific proper-name replacements to Aomi-mama.
- Thai words join without inter-word spaces; preserve legitimate spacing around Latin words and `ๆ`. Review informal speech, repeated reactions, game names and English announcer lines against audio. Do not censor or expand meaning.
- No content-confidence threshold that silently deletes speech. Flag weak ASR (`avg_logprob < -1.5`, `no_speech_prob > .8`, or suspect scripts) for listening. Unresolved speech is logged with time interval, never fabricated.
- Only one controller calls live Resolve. ASR and offline proofreading can be delegated; no concurrent Resolve mutations.
- A subtitle track found on rerun is NOT permission to append or delete it. Verify against this run's owned SRT; if identical, skip as verified; otherwise stop that timeline and report conflict. No implicit replace.
- Durable artifacts go under `runs/aomimama-2026-09-p1/`; do not put backup DRPs or final SRTs in system Temp or prunable scratch.

## Artifact paths

All paths are relative to the workspace unless absolute:

- New helper files: `scripts/aomimama_caption_core.py`, `scripts/aomimama_batch.py`, `tests/test_aomimama_caption_core.py`.
- Run root: `runs/aomimama-2026-09-p1/`.
- `manifest.json`: exact project + baseline timelines/clip signatures.
- `backups/aomimama-2026-09-p1-before-subtitles.drp`: verified backup before first track mutation.
- `audio/<timeline_uuid>.wav`: rendered timeline mix.
- `transcripts/<timeline_uuid>.json`: raw ASR, never edit in place.
- `reviewed/<timeline_uuid>.json`: reviewed cue list including `word_count`; the final import source.
- `srt/<timeline_uuid>.srt`: UTF-8 SRT.
- `review/<timeline_uuid>.md`: listened intervals, corrections, long-word exceptions, unresolved audio.
- `qc/<timeline_uuid>.png`: screenshot of the Resolve viewer, not ExportCurrentFrameAsStill.
- `progress.md`: stage, decisions and exact command results by UUID.
- `verification.json`: all-timeline readback result. Merge existing records when fixing one timeline.

Do not overwrite artifacts from an earlier run without checking manifest identity. An incomplete run resumes from its verified ledger, not from scratch. Keep audio and backups out of Git; stage only helper code/tests if commits are explicitly approved for execution.

## Step-by-step tasks

Times below are focused operator work, not promises about ASR or render wall-clock duration. Repeat timeline tasks per the inventory checklist. Long CPU inference is a foreground/bounded background job with progress; it is not a 2–5 minute computation guarantee.

### Task 1 — Reconfirm exact scope and prerequisite state (2–5 min)

Read this plan, reload subtitle/proofreading/process skills, inspect existing `runs/aomimama-2026-09-p1/progress.md` if present, then run:

```bash
git status --short
git branch --show-current
python --version
ffmpeg -version
uv --version
```

Expected: known working tree state, Python/FFmpeg/uv version output, not necessarily the same versions as planning. Preserve unrelated changes. No commit/push unless the execution authorization expressly includes it.

Create `runs/aomimama-2026-09-p1/progress.md` with this plan's exact path and one checklist row for every UUID/name. Use Task 4 inventory before populating it. If an exact requested skill is still unavailable, record that limitation; do not modify Hermes configuration.

### Task 2 — Isolated environment and backup preparation (2–5 min setup)

After execution approval, use an isolated Python 3.11 environment rather than the unprepared default 3.14 interpreter:

```bash
uv venv --python 3.11 .venv-aomimama
uv pip install --python .venv-aomimama/Scripts/python.exe faster-whisper pythainlp
.venv-aomimama/Scripts/python.exe -c "from faster_whisper import WhisperModel; from pythainlp.tokenize import word_tokenize; print(word_tokenize('ขอบคุณทุกคน',engine='newmm')); print('ASR_IMPORT_OK')"
```

Expected: environment creation/dependency install succeed, token list and `ASR_IMPORT_OK`. If network/install fails, report it; do not substitute invented transcripts. CPU int8 is the safe selected baseline; GPU is optional only after a real model-load/inference probe and appropriate CUDA-DLL registration.

In Resolve, Save Project, then File → Export Project to the exact backup path above. Verify the exported DRP exists and is non-empty using:

```bash
python -c "from pathlib import Path; p=Path('runs/aomimama-2026-09-p1/backups/aomimama-2026-09-p1-before-subtitles.drp'); assert p.is_file() and p.stat().st_size>0; print('BACKUP_PRESENT',p.stat().st_size)"
```

Expected: `BACKUP_PRESENT` with positive size. Capture original active timeline UUID/page/playhead for restoration during implementation. Backup export happens only in execution, not in plan mode.

### Task 3 — TDD for pure caption utilities (three 2–5 min slices)

3a. Create `tests/test_aomimama_caption_core.py` with the complete content below before implementation. Run:

```bash
.venv-aomimama/Scripts/python.exe -m unittest discover -s tests -p 'test_aomimama_caption_core.py' -v
```

Expected RED: import error because `scripts.aomimama_caption_core` does not exist yet (not a dependency error). These tests cover core formatting/import invariants, not speech accuracy.

```python
import unittest
from scripts.aomimama_caption_core import build_cues, render_srt, validate

class CaptionTests(unittest.TestCase):
    def raw(self, words):
        return {'segments': [{'words': words}]}

    def test_thai_fragments_and_short_duration(self):
        raw = self.raw([{'text':'ขอบ', 'start':0, 'end':.3},
                        {'text':'คุณทุกคน', 'start':.3, 'end':1.2}])
        cues = build_cues(raw, 2)
        self.assertEqual(''.join(c['text'] for c in cues), 'ขอบคุณทุกคน')
        validate(cues, 2)
        self.assertTrue(all(c['end']-c['start'] <= 1.5 for c in cues))

    def test_pauses_split_and_preserve_repeated_speech(self):
        raw = self.raw([{'text':'เฮ้ย', 'start':0, 'end':.3},
                        {'text':'เฮ้ย', 'start':1.2, 'end':1.5}])
        cues = build_cues(raw, 2)
        self.assertEqual(len(cues), 2)
        self.assertEqual([c['text'] for c in cues], ['เฮ้ย','เฮ้ย'])

    def test_script_removal_does_not_shift_later_onset(self):
        raw = self.raw([{'text':'를', 'start':0, 'end':.2},
                        {'text':'ดี', 'start':1, 'end':1.2}])
        cues = build_cues(raw, 2)
        self.assertEqual(cues[0]['text'], 'ดี')
        self.assertAlmostEqual(cues[0]['start'], 1)

    def test_latin_spacing(self):
        raw = self.raw([{'text':'เกม Minecraft ดี', 'start':0, 'end':1.2}])
        self.assertIn('Minecraft', ' '.join(c['text'] for c in build_cues(raw, 2)))
        cues = [{'start':0,'end':1,'text':'เกม Minecraft ดี','word_count':3}]
        self.assertIn('เกม Minecraft ดี', render_srt(cues))

    def test_clamp_and_no_overlap(self):
        raw = self.raw([{'text':'ดี', 'start':0, 'end':5},
                        {'text':'มาก', 'start':5, 'end':5.3}])
        cues = build_cues(raw, 5.2)
        validate(cues, 5.2)
        self.assertLessEqual(cues[-1]['end'], 5.2)

    def test_validation_rejects_bad_cues(self):
        for cue in [{'start':0,'end':2,'text':'ดี','word_count':1},
                    {'start':1,'end':.5,'text':'ดี','word_count':1},
                    {'start':0,'end':1,'text':'ดี\nมาก','word_count':2}]:
            with self.assertRaises(AssertionError):
                validate([cue], 3)

    def test_srt_rounding_carries(self):
        self.assertIn('00:01:00,000', render_srt([
            {'start':59.9996,'end':60.1,'text':'ดี','word_count':1}]))

if __name__ == '__main__':
    unittest.main()
```

3b. Create `scripts/aomimama_caption_core.py` with this complete content, then run the same test command. Expected GREEN: all seven tests pass. Namespace package `scripts` needs no added `__init__.py` on Python 3.11.

```python
import re
import unicodedata
from pythainlp.tokenize import word_tokenize

GAP = 1 / 60
BAD = re.compile(r'[\u0400-\u052f\u0600-\u06ff\u0900-\u097f'
                 r'\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]')


def joined(words):
    result = ''
    for word in words:
        if result and (re.search(r'[A-Za-z0-9]$', result) or
                       re.match(r'[A-Za-z0-9]', word)):
            result += ' '
        result += word
    return re.sub(r'\s+([,.!?])', r'\1', result).strip()


def build_cues(raw, duration):
    spans = []
    for segment in raw.get('segments', []):
        chars, times = [], []
        for word in segment.get('words', []):
            text = word['text']
            for i, ch in enumerate(text):
                if BAD.match(ch) or unicodedata.category(ch) == 'Cf':
                    continue
                a = word['start'] + (word['end']-word['start'])*i/max(1,len(text))
                b = word['start'] + (word['end']-word['start'])*(i+1)/max(1,len(text))
                chars.append(ch)
                times.append((a,b))
        text = ''.join(chars)
        cursor = 0
        local = []
        for token in word_tokenize(text, engine='newmm', keep_whitespace=True):
            ts = times[cursor:cursor+len(token)]
            cursor += len(token)
            if not token.strip() or not ts:
                continue
            token = token.strip()
            merge = (len(token)==1 and '\u0e00'<=token<='\u0e7f') or bool(
                re.match(r'^[\u0e31\u0e34-\u0e3a\u0e47-\u0e4e]', token)) or all(
                unicodedata.category(c).startswith('P') for c in token)
            if merge and local:
                local[-1]['text'] += token
                local[-1]['end'] = ts[-1][1]
            else:
                local.append({'text':token,'start':ts[0][0],'end':ts[-1][1]})
        spans.extend(local)
    spans.sort(key=lambda x: (x['start'],x['end']))
    groups, group = [], []
    for word in spans:
        if group and (len(group)>=3 or word['start']-group[-1]['end']>=.7 or
                      word['end']-group[0]['start']>1.5):
            groups.append(group)
            group = []
        group.append(word)
    if group:
        groups.append(group)
    cues = []
    for i, group in enumerate(groups):
        start = max(0, group[0]['start'])
        end = min(duration, group[-1]['end'], start+1.5)
        if i+1<len(groups):
            end = min(end, groups[i+1][0]['start']-GAP)
        if end<=start:
            raise ValueError('Conflicting ASR timestamps: review alignment; do not drop speech')
        cues.append({'start':start,'end':end,'text':joined([w['text'] for w in group]),
                     'word_count':len(group)})
    validate(cues,duration)
    return cues


def validate(cues, duration):
    previous = -1
    for cue in cues:
        a,b = cue['start'],cue['end']
        assert 0<=a<b<=duration+.000001
        assert b-a<=1.500001 and a>=previous
        assert cue['text'].strip() and '\n' not in cue['text']
        assert not BAD.search(cue['text'])
        assert 1<=cue['word_count']<=3
        previous=b


def render_srt(cues):
    def stamp(seconds):
        ms=round(seconds*1000)
        h,ms=divmod(ms,3600000)
        m,ms=divmod(ms,60000)
        s,ms=divmod(ms,1000)
        return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
    return '\n'.join(f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}\n"
                     for i,c in enumerate(cues,1))
```

3c. Review helper against skills. These automatic boundaries are proposals, not approved transcripts. Listen and manually split long tokens/repair overlapped ASR before import; log exceptions rather than truncating speech. Do not silently remove meaningful foreign speech: the script filter is appropriate only after review establishes such characters are ASR noise. A real foreign-script phrase requires an explicit policy decision before processing that timeline.

If execution includes permission to commit helper code, after GREEN:

```bash
git add scripts/aomimama_caption_core.py tests/test_aomimama_caption_core.py
git commit -m "feat: add tested Aomi subtitle cue utilities"
```

Expected: only the named files are staged/committed. Otherwise record GREEN in the ledger and leave changes uncommitted. Never push.

### Task 4 — Add the batch runbook helper and discover manifest (2–5 min slices)

Create `scripts/aomimama_batch.py` exactly as below. It is an operational helper, NOT an extension of old K404 scripts. `inventory` and `verify` are read-only to Resolve; `asr` only writes new local artifacts; `insert` mutates only the exact selected timeline after backup and review. Run as module from workspace root so imports resolve.

```python
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import wave
from scripts.aomimama_caption_core import build_cues, render_srt, validate

ROOT=Path('runs/aomimama-2026-09-p1')
PROJECT='aomimama-2026-09-p1'


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def connect():
    os.add_dll_directory('C:/Program Files/Blackmagic Design/DaVinci Resolve')
    sys.path.insert(0,'C:/ProgramData/Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting/Modules')
    import DaVinciResolveScript as d
    r=d.scriptapp('Resolve')
    assert r,'Resolve bridge unavailable'
    pm=r.GetProjectManager()
    p=pm.GetCurrentProject()
    assert p and p.GetName()==PROJECT,'Wrong project: stop'
    return r,pm,p


def clip_signature(t):
    return {kind:[[{'id':c.GetUniqueId(),'start':c.GetStart(),'end':c.GetEnd(),
                   'left':c.GetLeftOffset(),'duration':c.GetDuration()}
                  for c in (t.GetItemListInTrack(kind,j) or [])]
                 for j in range(1,t.GetTrackCount(kind)+1)]
            for kind in ('video','audio')}


def inventory():
    _,_,p=connect()
    rows=[]
    for i in range(1,p.GetTimelineCount()+1):
        t=p.GetTimelineByIndex(i)
        rows.append({'index':i,'id':t.GetUniqueId(),'name':t.GetName(),
                     'start':t.GetStartFrame(),'end':t.GetEndFrame(),
                     'fps':float(t.GetSetting('timelineFrameRate')),
                     'width':t.GetSetting('timelineResolutionWidth'),
                     'height':t.GetSetting('timelineResolutionHeight'),
                     'subtitle_tracks':t.GetTrackCount('subtitle'),
                     'clips':clip_signature(t)})
    assert len(rows)==49 and len({x['id'] for x in rows})==49,'Scope changed'
    assert all(x['start']==0 and x['fps']==60 for x in rows),'Timebase changed'
    path=ROOT/'manifest.json'
    assert not path.exists(),'Existing manifest: inspect/resume; do not overwrite'
    save(path,{'project':PROJECT,'timelines':rows})
    print('INVENTORY_OK',len(rows))


def load():
    data=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    assert data['project']==PROJECT
    return data['timelines']


def target(p,row):
    byid={p.GetTimelineByIndex(i).GetUniqueId():p.GetTimelineByIndex(i)
          for i in range(1,p.GetTimelineCount()+1)}
    assert set(byid)=={x['id'] for x in load()},'Timeline scope changed'
    t=byid[row['id']]
    assert t.GetName()==row['name'] and t.GetStartFrame()==row['start']
    assert t.GetEndFrame()==row['end'] and clip_signature(t)==row['clips'],'Edit changed'
    assert float(t.GetSetting('timelineFrameRate'))==row['fps'],'Frame rate changed'
    assert t.GetSetting('timelineResolutionWidth')==row['width'],'Raster width changed'
    assert t.GetSetting('timelineResolutionHeight')==row['height'],'Raster height changed'
    return t


def asr(row):
    path=ROOT/'audio'/f"{row['id']}.wav"
    duration=(row['end']-row['start'])/row['fps']
    with wave.open(str(path),'rb') as wav:
        assert wav.getnchannels()==1 and wav.getframerate()==16000
        assert abs(wav.getnframes()/16000-duration)<.1,'Wrong audio range'
    out=ROOT/'transcripts'/f"{row['id']}.json"
    assert not out.exists(),'Existing raw transcript: inspect/resume'
    from faster_whisper import WhisperModel
    model=WhisperModel('large-v3',device='cpu',compute_type='int8',cpu_threads=8)
    segments,_=model.transcribe(str(path),language='th',word_timestamps=True,
        beam_size=5,condition_on_previous_text=False,vad_filter=True,
        vad_parameters={'min_silence_duration_ms':400,'speech_pad_ms':200})
    data={'timeline_id':row['id'],'duration_seconds':duration,'segments':[]}
    for s in segments:
        data['segments'].append({'start':s.start,'end':s.end,'text':s.text,
            'avg_logprob':s.avg_logprob,'no_speech_prob':s.no_speech_prob,
            'words':[{'text':w.word,'start':w.start,'end':w.end,'probability':w.probability}
                     for w in (s.words or [])]})
    save(out,data)
    print('ASR_RAW_OK',row['id'],len(data['segments']))


def prepare(row):
    duration=(row['end']-row['start'])/row['fps']
    raw=json.loads((ROOT/'transcripts'/f"{row['id']}.json").read_text(encoding='utf-8'))
    assert raw['timeline_id']==row['id']
    out=ROOT/'reviewed'/f"{row['id']}.json"
    assert not out.exists(),'Preserve existing reviewed cues'
    save(out,{'timeline_id':row['id'],'approved':False,'cues':build_cues(raw,duration)})
    print('DRAFT_ONLY',row['id'])


def cues_for(row):
    path=ROOT/'reviewed'/f"{row['id']}.json"
    data=json.loads(path.read_text(encoding='utf-8'))
    assert data['timeline_id']==row['id'] and data['approved'] is True,'Review required'
    cues=data['cues']
    validate(cues,(row['end']-row['start'])/row['fps'])
    assert cues,'No speech? Record separate no-speech decision, do not insert empty SRT'
    return cues


def check(t,row,cues):
    assert t.GetTrackCount('subtitle')==1,'Unexpected subtitle tracks'
    items=t.GetItemListInTrack('subtitle',1) or []
    assert len(items)==len(cues),'Cue count mismatch'
    items=sorted(items,key=lambda c:c.GetStart())
    for item,cue in zip(items,cues):
        assert item.GetName().strip()==cue['text'].strip(),'Cue text mismatch'
        for actual,seconds in [(item.GetStart(),cue['start']),(item.GetEnd(),cue['end'])]:
            assert abs(actual-(row['start']+seconds*row['fps']))<=1.01,'Cue frame mismatch'
    assert t.GetEndFrame()==row['end'] and clip_signature(t)==row['clips']
    return {'id':row['id'],'name':row['name'],'cues':len(cues),'verified':True}


def insert(row):
    cues=cues_for(row)
    _,pm,p=connect()
    t=target(p,row)
    if t.GetTrackCount('subtitle'):
        check(t,row,cues)
        print('ALREADY_VERIFIED',row['id'])
        return
    backup=ROOT/'backups'/'aomimama-2026-09-p1-before-subtitles.drp'
    assert backup.is_file() and backup.stat().st_size>0,'Backup required'
    srt=ROOT/'srt'/f"{row['id']}.srt"
    srt.parent.mkdir(parents=True,exist_ok=True)
    content=render_srt(cues)
    if srt.exists():
        assert srt.read_text(encoding='utf-8')==content,'Changed SRT path: stop for cache-safe recovery'
    else:
        srt.write_text(content,encoding='utf-8')
    assert p.SetCurrentTimeline(t)
    time.sleep(1.2)
    mp=p.GetMediaPool()
    imported=mp.ImportMedia([str(srt.resolve())])
    assert imported and len(imported)==1
    time.sleep(1.2)
    assert t.AddTrack('subtitle')
    time.sleep(1.2)
    assert mp.AppendToTimeline([{'mediaPoolItem':imported[0]}])
    time.sleep(1.2)
    check(t,row,cues)
    assert pm.SaveProject()
    print('INSERT_VERIFIED',row['id'],len(cues))


def verify():
    _,_,p=connect()
    results=[]
    for row in load():
        t=target(p,row)
        results.append(check(t,row,cues_for(row)))
    save(ROOT/'verification.json',{'project':PROJECT,'results':results})
    print('ALL_VERIFIED',len(results))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('stage',choices=['inventory','asr','prepare','insert','verify'])
    ap.add_argument('--index',type=int)
    args=ap.parse_args()
    if args.stage=='inventory':
        inventory()
    elif args.stage=='verify':
        verify()
    else:
        assert args.index is not None,'--index required'
        row=next(x for x in load() if x['index']==args.index)
        {'asr':asr,'prepare':prepare,'insert':insert}[args.stage](row)

if __name__=='__main__':
    main()
```

Run syntax and pure tests before touching Resolve:

```bash
.venv-aomimama/Scripts/python.exe -c "import ast; from pathlib import Path; ast.parse(Path('scripts/aomimama_batch.py').read_text(encoding='utf-8')); print('SYNTAX_OK')"
.venv-aomimama/Scripts/python.exe -m unittest discover -s tests -p 'test_aomimama_caption_core.py' -v
.venv-aomimama/Scripts/python.exe -m scripts.aomimama_batch inventory
```

Expected: `SYNTAX_OK`, seven tests GREEN, `INVENTORY_OK 49`, manifest contains every exact UUID/name. Live API integration is proven by readback, not mocks. Review `GetName()` subtitle text behavior on the pilot; if different on this installation, stop and inspect the actual item properties before changing the comparison. Never waive text verification.

### Task 5 — Pilot timeline 1: render audible mix (2–5 min operator work)

In Resolve activate timeline `เปิดสตรีมทักทายก่อนเริ่มเกม-alien shooter last hope-vdo` by its manifest UUID. Deliver page → entire timeline, audio only, Wave/Linear PCM, export audible mix (not each source clip), new filename based on UUID, to `runs/aomimama-2026-09-p1/audio/`. Disable video export; ensure range begins at timeline start and ends at its original end; do not use stale in/out marks. Render only this audio job, not an existing unrelated queue job. Record resulting file and settings.

If Resolve only offers a different sample rate/channel count, render to `audio/<uuid>-mix.wav`, then convert the mix, NOT source media:

```bash
ffmpeg -hide_banner -loglevel error -i runs/aomimama-2026-09-p1/audio/4720b0bd-a3f4-4106-bdcb-18101a54c2f6-mix.wav -ac 1 -ar 16000 -c:a pcm_s16le runs/aomimama-2026-09-p1/audio/4720b0bd-a3f4-4106-bdcb-18101a54c2f6.wav
```

Expected: exit 0, new mono 16 kHz WAV; no `-y`, so existing files are not silently overwritten. The `asr` stage also asserts rendered duration within .1 s of the manifest. If the selected render does not contain the intended speech, fix the render selection; do not proceed with an empty/wrong mix.

### Task 6 — Pilot ASR/draft review (2–5 min start/check, inference may take longer)

```bash
.venv-aomimama/Scripts/python.exe -m scripts.aomimama_batch asr --index 1
.venv-aomimama/Scripts/python.exe -m scripts.aomimama_batch prepare --index 1
```

Expected: `ASR_RAW_OK` with positive segment count and `DRAFT_ONLY`; a real downloaded/loaded large-v3 model, not placeholder output. First model download is an explicit network cost of this selected approach.

Read raw JSON and listen to the rendered WAV. Use Thai-proofread but treat token dictionary misses as flags, not proof of error. Review every low-confidence/suspect segment and every suspicious silence/repeat; listen start/middle/end at minimum and all claimed omissions. Caption correct words and names; do not auto-import draft material. Review the whole pilot before selecting the batching policy. Preserve genuine reactions/English and correct against audio, not the timeline title.

Edit only `reviewed/4720b0bd-a3f4-4106-bdcb-18101a54c2f6.json`, preserving UUID and explicit `word_count`; mark `approved: true` only after listening/review. Write correction and unresolved-interval evidence to the matching review markdown. If any meaningful speech remains unresolved, the final report must say so; do not call coverage perfect.

Weak game-audio ASR remedy: produce a separate filtered WAV with ffmpeg `-af 'highpass=f=80,lowpass=f=7000,afftdn=nf=-25,dynaudnorm=f=150:g=15:p=0.7'`, retranscribe under a NEW artifact path and compare per affected interval. Do not globally substitute the filtered pass, overwrite the raw result, or rerun the existing `asr` stage over its raw path. Choose transcript phrases against audio evidence and record decisions. If this branch is needed, implement the small separate retry command with a failing regression test before reuse; it is not on the normal selected path.

### Task 7 — Pilot insert and independent readback (2–5 min)

```bash
.venv-aomimama/Scripts/python.exe -m scripts.aomimama_batch insert --index 1
.venv-aomimama/Scripts/python.exe -m scripts.aomimama_batch insert --index 1
```

Expected first run: `INSERT_VERIFIED <uuid> <cue_count>`. Expected second, separately connected run: `ALREADY_VERIFIED <uuid>`, no duplicate tracks/items. Check actual timeline subtitle track, first/middle/last text, timing, and a screenshot of the viewer. Save `qc/4720b0bd-a3f4-4106-bdcb-18101a54c2f6.png`. Do not use a clean-frame export that omits subtitles.

The importer uses bare `{mediaPoolItem: item}` with an empty subtitle track. Do not add recordFrame, mediaType or trackIndex. Wait between mutations. API success alone is not success: item count, text and frames must match in readback.

Partial failure after AddTrack may leave an empty track. The helper intentionally stops on rerun instead of deleting user data. Record track/index and owned pool-item identity; request authorization for targeted removal/recovery if necessary. Do not delete all tracks or cached clips. Corrected SRTs must get a fresh versioned file path or authorized deletion of the exact owned cached pool item; resolve path caching explicitly.

### Task 8 — Process remaining timelines, one checklist item each (repeated 2–5 min work slices)

For each manifest index below: (a) render its entire audible mix to `audio/<UUID>.wav`; (b) run ASR; (c) prepare reviewed draft; (d) listen/proofread and approve; (e) controller inserts serially; (f) reconnect/readback and capture viewer QC; (g) record complete only after verification. Copy these commands and change the numeric index to the current manifest row:

```bash
.venv-aomimama/Scripts/python.exe -m scripts.aomimama_batch asr --index 2
.venv-aomimama/Scripts/python.exe -m scripts.aomimama_batch prepare --index 2
# Listen/review the UUID-keyed files; explicitly set approved true only after QC.
.venv-aomimama/Scripts/python.exe -m scripts.aomimama_batch insert --index 2
.venv-aomimama/Scripts/python.exe -m scripts.aomimama_batch insert --index 2
```

Expected per row: ASR_RAW_OK → DRAFT_ONLY → INSERT_VERIFIED → ALREADY_VERIFIED. No blanket mutation loop before pilot acceptance. Offline workers receive exact UUID/file paths and cannot mutate Resolve or approve their own work without review. Use one ASR worker to avoid model RAM duplication; proofreading can be delegated in small batches with a second reviewer. Preserve complete review evidence, not just a subagent self-report.

#### Authoritative planning-time timeline checklist

Re-enumerated manifest UUIDs remain execution authority; these exact names prevent accidental omission. All are landscape at planning time.

- [ ] 1 เปิดสตรีมทักทายก่อนเริ่มเกม-alien shooter last hope-vdo
- [ ] 2 ตามหาห้องที่หายไป-alien shooter last hope-vdo
- [ ] 3 ฝูงเอเลี่ยนบุกจนร้องลั่น-alien shooter last hope-vdo
- [ ] 4 คุยเรื่องอายุและเด็กรุ่นหลาน-alien shooter last hope-vdo
- [ ] 5 ซื้อปืนไม่พอเงินขาดไปพันเดียว-alien shooter last hope-vdo
- [ ] 6 เตรียมป้อมสู้ศึกใหญ่-alien shooter last hope-vdo
- [ ] 7 ล่อบอสตัวเหนียวจนเหนื่อย-alien shooter last hope-vdo
- [ ] 8 จบเกมในครั้งเดียว-alien shooter last hope-vdo
- [ ] 9 คุยกับแชทช่วงต้นไลฟ์ เล่าว่าเล่นเกมนี้มาหล-alien shooter-vdo
- [ ] 10 ตั้งค่าหน้าจอไลฟ์ เจอวิธีใหม่-alien shooter-vdo
- [ ] 11 กวาดห้องจนจบภารกิจ-alien shooter-vdo
- [ ] 12 ตอบแชทว่าเกมยากไหมระหว่างเล่น-alien shooter-vdo
- [ ] 13 ด่านเขียวสุดท้ายก่อนจอดับ-alien shooter-vdo
- [ ] 14 คุยสรุปเกมหลังเล่นจบ ก่อนปิดไลฟ์-alien shooter-vdo
- [ ] 15 ลืมแชร์จอ จบของวีทูปเบอร์ที่ไม่เตรียมตัว-Minecraft-vdo
- [ ] 16 หนาวติดลบ 16 ต้องถือลาวา-Minecraft-vdo
- [ ] 17 ถือถังลาวาไว้กันหนาว-Minecraft-vdo
- [ ] 18 พี่น้องไม่เคยช่วยอะไรเลย-Minecraft-vdo
- [ ] 19 อย่าใส่ร้ายผม เกือบจมลาวา-Minecraft-vdo
- [ ] 20 เจอเพชรแล้ว! ยิส!-Minecraft-vdo
- [ ] 21 เจอทางกลับบ้านแต่เพื่อนไปห้องน้ำ-Minecraft-vdo
- [ ] 22 ลุยฐานใต้ดิน เข้าได้สองทาง-alien shooter 2-vdo
- [ ] 23 กวาดศัตรูในฐานมืด-alien shooter 2-vdo
- [ ] 24 เช็กของ เซฟยัง แล้วลุยต่อ-alien shooter 2-vdo
- [ ] 25 กดเล่นแล้วเกมเด้ง ลบโหลดใหม่เลย-alien shooter 2-vdo
- [ ] 26 Windows XP  Vista  8  ลองหมด-alien shooter 2-vdo
- [ ] 27 ในที่สุดแชร์จอเหมือนคนปกติได้แล้ว-alien shooter 2-vdo
- [ ] 28 ปรับความละเอียด 1024x768 ไอ้เฮีย-alien shooter 2-vdo
- [ ] 29 ไฟต์ใหญ่ในอารีนา-League of Legends-vdo
- [ ] 30 เสียงร้องโอ๊ยๆ-League of Legends-vdo
- [ ] 31 ดับเบิลคิลแล้วโดนฝัง-League of Legends-vdo
- [ ] 32 ไฟต์หน้าป้อม-League of Legends-vdo
- [ ] 33 เมาท์เรื่องสายเล่นเกม-League of Legends-vdo
- [ ] 34 เพนตาคิลแล้วพ่ายแพ้-League of Legends-vdo
- [ ] 35 ไฟต์ท้ายเกมสุดมัน-League of Legends-vdo
- [ ] 36 ลืมเปิดเสียงเพื่อน คุยกับผีมาตั้งนาน-Minecraft-vdo
- [ ] 37 ลืมเอาอาหาร ต้องกินเนื้อซอมบี้-Minecraft-vdo
- [ ] 38 ซอมบี้มาได้ไงวะ!-Minecraft-vdo
- [ ] 39 อยากเปลี่ยนร่าง เอาคนไม่มีเสียงในหัวมาเล่นแทน-Minecraft-vdo
- [ ] 40 พี่จ๋าช่วยด้วย เรือไปไหนวะ-Minecraft-vdo
- [ ] 41 วิ่งหนีมอนตอนมืดจนเห็นบ้าน-Minecraft-vdo
- [ ] 42 ออกไม่ได้เลยวะ ฮ่าๆๆ-Minecraft-vdo
- [ ] 43 ไฟต์ในเลนกับเสียงร้องเฮ้ย-League of Legends-vdo
- [ ] 44 ทีมไฟต์ถูกชัตดาวน์-League of Legends-vdo
- [ ] 45 เริ่มเกมแล้วเจอไฟต์-League of Legends-vdo
- [ ] 46 หัวยังไม่ฟู ตายก่อนเลย-League of Legends-vdo
- [ ] 47 ออกเมื่อไหร่มีตายเมื่อนั้น-League of Legends-vdo
- [ ] 48 ด่าทีมรัวๆ ไอ้เชี่ยทีมตาก-League of Legends-vdo
- [ ] 49 ลาสตรีม ขอบคุณทุกคน-League of Legends-vdo

### Task 9 — Final independent verification and handoff (2–5 min automated check + review)

```bash
.venv-aomimama/Scripts/python.exe -m unittest discover -s tests -p 'test_aomimama_caption_core.py' -v
.venv-aomimama/Scripts/python.exe -m scripts.aomimama_batch verify
python -c "import json; from pathlib import Path; d=json.loads(Path('runs/aomimama-2026-09-p1/verification.json').read_text(encoding='utf-8')); r=d['results']; assert len(r)==49 and len({x['id'] for x in r})==49 and all(x['verified'] and x['cues']>0 for x in r); print('REPORT_OK',len(r),'cues',sum(x['cues'] for x in r))"
git diff --stat
git status --short
```

Expected: seven tests GREEN; `ALL_VERIFIED 49`; `REPORT_OK 49 cues <actual total>`. Never invent the total. A no-speech timeline must be explicitly resolved with listening evidence and an agreed no-cue exception before updating the verifier/report contract; no empty all() success.

A separate reviewer checks manifest-vs-results UUID sets, sample SRT-vs-readback text, all unresolved intervals, start/middle/end screenshots and whether layout/clip signatures remain unchanged. Automated timing tolerance ≤1.01 frames covers SRT millisecond rounding plus Resolve frame quantization; it does not excuse perceptual speech misalignment. Spot-listen each timeline at start/middle/end and all flagged intervals.

Restore original active timeline/playhead/page captured at execution start, wait for page changes and read back the actual state. Save project, verify current project name and retained subtitles in a separate connection. Record all exceptions. If helper code commits were approved, stage/commit only `scripts/aomimama_batch.py` after successful pilot/final evidence; do not stage DRP/WAV/media or push.

Final report in Thai: verified timelines/expected 49, actual total cues, SRT directory, DRP path, omitted/uncertain speech and whether styling was deferred. Keep plan, run ledger and backup for recovery.

## Tests / validation contract

- TDD applies to new pure caption code; seven provided tests must be observed RED then GREEN, not merely predicted. Operational backup/render/import steps use real output/readback and do not require inventing failing tests that mutate production timelines.
- Before draft approval: ASR text reviewed against real audible mix; bad script removal/name changes/repeats are explained in the per-timeline review log.
- SRT: UTF-8, consecutive indices, one non-empty line per cue, positive durations ≤1.5 s, ≤3 logical words, no unintended foreign glyphs, monotonic non-overlapping timings, all cues end inside original timeline.
- Import: one subtitle track per newly processed timeline, actual cue texts/counts match reviewed cue list, frame placement within rounding tolerance, no append stacking.
- Non-regression: original timeline UUID/name/start/end/raster/fps and video/audio clip signatures remain unchanged; no source-media writes, extra timelines or overlays.
- Resumability: raw/reviewed files not overwritten; a second insert reads back and skips identical cues; conflicts stop without destructive fallback.
- No completion claim while any timeline is unverified, any unread review issue remains, or all-timeline inventory count differs.

## Risks, tradeoffs and open questions

1. Audio-only render UI options depend on installed Resolve version. Use verified current Deliver controls; if mix WAV cannot be rendered without changing project content, stop and choose a documented alternative. Do not invent API settings.
2. 49 render jobs and CPU large-v3 inference can be slow; work-slice times are not runtime estimates. GPU is optional optimization, not required for correctness.
3. Whisper Thai words are fragments; character interpolation provides a starting alignment, not human-quality proof. Overlaps/long fragments stop or require listening rather than silent content loss.
4. Short-cue default is a stated assumption for Aomi-mama, not a new user instruction imported from Katy404. The user may prefer longer natural-sentence captions; approve/change this in plan review. No styling/preset/SQL work is included.
5. Existing scripts are unsafe to reuse wholesale because of import-time effects and K404-specific paths/replacements. New scoped helpers avoid accidental old-project processing; a generic framework is intentionally out of scope.
6. The batch script is fully specified but has not been created or run in plan mode. Live subtitle GetName/end-frame conventions are validated on the pilot before batch import. A discrepancy is an integration blocker, not permission to weaken assertions.
7. Exported backup presence is checked; a full recovery/import of DRP is not attempted on the live project. Restore into a separately named project only with explicit permission if recovery becomes necessary.
8. Native Resolve mutation and cached SRT behavior are not transactionally reversible. Do not delete tracks on a failed rerun. Pause for authorization for destructive repair.
9. Actual non-Thai dialogue, genuine no-speech timelines, new existing subtitle tracks or changed scope require explicit exception decisions. Unclear audio never becomes invented words.
10. Code commit permission is separate from subtitle insertion; no commit or push has been performed in planning. Frequent local commits are optional only if included in execution approval.

## Execution handoff

Preferred: subagent-driven-development for the tested helper and offline transcript review, with a single parent-owned Resolve mutation lane. Read this plan as the binding scope; preflight shared interfaces `manifest → audio → raw transcript → reviewed cues → SRT → readback`. Do not dispatch a worker that both edits Resolve and races another worker; never treat a child's success report as external-state evidence. The parent runs the exact final readback before reporting completion.
