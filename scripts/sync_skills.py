"""Mirror project skills from .agents/skills (source of truth) to .claude/skills.

Claude Code only loads skills from .claude/skills; Codex-style agents read
.agents/skills. Keep one source and copy, so the two never drift.

  python scripts/sync_skills.py          # copy
  python scripts/sync_skills.py --check  # exit 1 if they differ (for CI/pre-commit)
"""
import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / '.agents' / 'skills'
DST = ROOT / '.claude' / 'skills'


def files(base):
    return sorted(p.relative_to(base) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    drift = []
    for skill in sorted(p for p in SRC.iterdir() if p.is_dir()):
        for rel in files(skill):
            s, d = skill / rel, DST / skill.name / rel
            if not d.exists() or not filecmp.cmp(s, d, shallow=False):
                drift.append(d)
                if not args.check:
                    d.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(s, d)
    for d in drift:
        print(('DIFF  ' if args.check else 'synced ') + str(d.relative_to(ROOT)))
    if args.check and drift:
        sys.exit(1)
    print('skills in sync' if not drift or not args.check else '')


if __name__ == '__main__':
    main()
