"""One entry point for the Gemini subtitle pipeline; picks the right Python per stage.

  python scripts/run_pipeline.py status
  python scripts/run_pipeline.py transcribe [N ...]     # Gemini, resumes, needs GEMINI_API_KEY
  python scripts/run_pipeline.py cues [N ...]           # transcripts -> draft SRT (pythainlp venv)
  python scripts/run_pipeline.py verify [N ...]         # audio plausibility check
  python scripts/run_pipeline.py import [N ...]         # Resolve dry run (py -3.12)
  python scripts/run_pipeline.py import [N ...] --apply [--replace]

Why this exists: tokenizing needs the 3.11 venv (pythainlp) while Resolve needs
3.12 (fusionscript.dll); using the wrong one passes a dry run and fails on --apply.
Stages never write to Resolve unless --apply is given explicitly.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = Path(os.environ.get('AOMIMAMA_RUN_ROOT') or ROOT / 'runs' / 'aomimama-2026-09-p1')
SCRIPTS = ROOT / 'scripts'
VENV_PY = ROOT / '.venv-aomimama' / 'Scripts' / 'python.exe'


def interpreter(stage):
    """Command prefix for the interpreter a stage needs."""
    if stage == 'cues':
        return [str(VENV_PY)] if VENV_PY.is_file() else [sys.executable]
    if stage == 'import':
        return ['py', '-3.12']
    return [sys.executable]


def build_command(stage, indices, apply=False, replace=False):
    script = {'transcribe': 'gemini_direct_transcribe.py', 'cues': 'build_gemini_cues.py',
              'verify': 'verify_cues_audio.py', 'import': 'import_subtitles_resolve.py'}[stage]
    cmd = interpreter(stage) + ['-X', 'utf8', str(SCRIPTS / script)]
    if stage == 'verify' and indices:
        cmd += ['--only'] + [str(i) for i in indices]
    elif stage == 'import':
        if indices:
            cmd += ['--only'] + [str(i) for i in indices]
        if apply:
            cmd.append('--apply')
        if replace:
            cmd.append('--replace')
    elif stage in ('transcribe', 'cues'):
        cmd += [str(i) for i in indices]
    return cmd


def status():
    rows = json.loads((RUN_ROOT / 'manifest.json').read_text(encoding='utf-8'))['timelines']

    def count(folder, suffix):
        return sum((RUN_ROOT / folder / f"{r['id']}{suffix}").is_file() for r in rows)

    print(f'run root : {RUN_ROOT}')
    print(f'timelines: {len(rows)}')
    for label, folder, suffix in (('audio', 'audio', '.wav'), ('transcripts', 'transcripts', '.gemini.json'),
                                  ('draft srt', 'srt', '.draft.srt')):
        print(f'{label:<11}: {count(folder, suffix)}/{len(rows)}')
    results = RUN_ROOT / 'import-results.json'
    if results.is_file():
        data = json.loads(results.read_text(encoding='utf-8'))
        items = data.get('results', data) if isinstance(data, dict) else data
        print(f'import     : {len(items)} recorded in import-results.json')
    report = RUN_ROOT / 'audio-verification.json'
    if report.is_file():
        data = json.loads(report.read_text(encoding='utf-8'))
        print(f"verified   : {len(data)} timelines, {sum(v['flagged'] for v in data.values())} cues flagged")
    print(f"GEMINI_API_KEY: {'set' if os.environ.get('GEMINI_API_KEY') else 'not in environment (Hermes .env is used)'}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('stage', choices=['status', 'transcribe', 'cues', 'verify', 'import'])
    parser.add_argument('indices', type=int, nargs='*', help='manifest indices; default all')
    parser.add_argument('--apply', action='store_true', help='import only: actually write to Resolve')
    parser.add_argument('--replace', action='store_true', help='import only: replace an existing subtitle track')
    args = parser.parse_args(argv)
    if args.stage == 'status':
        return status()
    if (args.apply or args.replace) and args.stage != 'import':
        parser.error('--apply/--replace only apply to the import stage')
    cmd = build_command(args.stage, args.indices, args.apply, args.replace)
    print('>', ' '.join(cmd), flush=True)
    env = dict(os.environ, AOMIMAMA_RUN_ROOT=str(RUN_ROOT), PYTHONUTF8='1')
    return subprocess.call(cmd, env=env)


if __name__ == '__main__':
    sys.exit(main())
