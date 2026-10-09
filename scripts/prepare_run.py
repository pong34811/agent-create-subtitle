"""Prepare a run folder from the OPEN Resolve project: backup .drp, manifest.json, audio.

  py -3.12 scripts/prepare_run.py manifest   # backup .drp + write manifest.json (no timeline edits)
  py -3.12 scripts/prepare_run.py audio      # render per-timeline mix WAVs (Deliver queue) + mono 16 kHz

Run root comes from AOMIMAMA_RUN_ROOT (default: runs/<project name>). Source media is read-only.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTING = r'C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting'
os.environ.setdefault('RESOLVE_SCRIPT_API', SCRIPTING)
os.environ.setdefault('RESOLVE_SCRIPT_LIB', r'C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll')
sys.path.append(SCRIPTING + r'\Modules')
os.add_dll_directory(r'C:\Program Files\Blackmagic Design\DaVinci Resolve')
import DaVinciResolveScript as dvr  # noqa: E402


def connect():
    for _ in range(10):
        resolve = dvr.scriptapp('Resolve')
        if resolve:
            return resolve
        time.sleep(5)
    raise SystemExit('cannot connect to Resolve')


def clips(tl, kind):
    return [[{'id': c.GetUniqueId(), 'start': c.GetStart() - tl.GetStartFrame(),
              'end': c.GetEnd() - tl.GetStartFrame(), 'left': c.GetLeftOffset(), 'duration': c.GetDuration(),
              'speed': c.GetProperty('Speed')}
             for c in tl.GetItemListInTrack(kind, i) or []] for i in range(1, tl.GetTrackCount(kind) + 1)]


def manifest(project, run_root):
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / 'backups').mkdir(exist_ok=True)
    resolve_pm().SaveProject()
    drp = run_root / 'backups' / f'{project.GetName()}-before-subtitles.drp'
    if not drp.exists():
        assert resolve_pm().ExportProject(project.GetName(), str(drp)), 'ExportProject failed'
    rows = []
    for i in range(1, project.GetTimelineCount() + 1):
        tl = project.GetTimelineByIndex(i)
        rows.append({'index': i, 'id': tl.GetUniqueId(), 'name': tl.GetName(), 'start': 0,
                     'end': tl.GetEndFrame() - tl.GetStartFrame(), 'tl_start_frame': tl.GetStartFrame(),
                     'fps': float(tl.GetSetting('timelineFrameRate')),
                     'width': tl.GetSetting('timelineResolutionWidth'),
                     'height': tl.GetSetting('timelineResolutionHeight'),
                     'subtitle_tracks': tl.GetTrackCount('subtitle'),
                     'clips': {'video': clips(tl, 'video'), 'audio': clips(tl, 'audio')}})
    data = {'project': project.GetName(), 'timelines': rows}
    (run_root / 'manifest.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    retimed = [r['index'] for r in rows for k in ('video', 'audio') for t in r['clips'][k] for c in t
               if c['speed'] not in (None, 100, 100.0, '100', 1, 1.0)]
    print(f'{len(rows)} timelines, backup {drp.name}, retimed clips on: {sorted(set(retimed))}')


_PM = []


def resolve_pm():
    return _PM[0]


def audio(project, run_root):
    rows = json.loads((run_root / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    out = run_root / 'audio'
    out.mkdir(exist_ok=True)
    for r in rows:
        if (out / f"{r['id']}.wav").is_file():
            continue
        tl = project.GetTimelineByIndex(r['index'])
        assert tl.GetUniqueId() == r['id']
        project.SetCurrentTimeline(tl)
        project.DeleteAllRenderJobs()
        project.LoadRenderPreset('Audio Only')
        ok = project.SetRenderSettings({'SelectAllFrames': False, 'MarkIn': tl.GetStartFrame(),
                                        'MarkOut': tl.GetEndFrame() - 1, 'TargetDir': str(out),
                                        'CustomName': f"{r['id']}-mix"})
        job = project.AddRenderJob()
        assert ok and job, f"render setup failed for {r['index']}"
        project.StartRendering(job)
        while project.IsRenderingInProgress():
            time.sleep(1)
        status = project.GetRenderJobStatus(job)
        assert status.get('JobStatus') == 'Complete', (r['index'], status)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(out / f"{r['id']}-mix.wav"),
                        '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(out / f"{r['id']}.wav")], check=True)
        print(f"{r['index']:>3} audio ok")
    project.DeleteAllRenderJobs()


def main():
    resolve = connect()
    _PM.append(resolve.GetProjectManager())
    project = _PM[0].GetCurrentProject()
    run_root = Path(os.environ.get('AOMIMAMA_RUN_ROOT') or ROOT / 'runs' / project.GetName())
    print(f'project {project.GetName()} -> {run_root}')
    {'manifest': manifest, 'audio': audio}[sys.argv[1]](project, run_root)


if __name__ == '__main__':
    main()
