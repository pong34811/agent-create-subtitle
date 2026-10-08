# Repository Guidelines

## Project Structure & Module Organization

This repository makes Thai gaming subtitles. The **current pipeline** is Gemini
ASR → SRT → DaVinci Resolve subtitle tracks (run `aomimama-2026-09-p1`). The
original Whisper pipeline is archived under `legacy/`.

- `scripts/`: current pipeline.
  - `gemini_direct_transcribe.py` and `transcribe_chunked.py` transcribe.
  - `build_gemini_cues.py` builds cues and SRT.
  - `import_subtitles_resolve.py` imports to Resolve (dry run by default).
  - `aomimama_asr.py` and `aomimama_caption_core.py` are the phrase splitter and quality gates.
  - `compare_asr*.py` are model comparisons.
  - `sync_skills.py` mirrors skills.
- `tests/`: pytest suite (32 tests).
- `runs/<run>/`: manifests, transcripts, reviewed JSON, SRT drafts and logs for one batch. Audio and `.drp` backups are git-ignored.
- `legacy/k404-whisper/`: K404 batch, the Whisper transcribers and builders, their transcripts, ASS/SRT and the Mitr font. Self-contained; run scripts from inside it.
- `.agents/skills/`: project skills, the source of truth (`create-subtitle`, `thai-subtitles-resolve`, `thai-proofread`, `resolve-mitr-subtitle-presets`, `grilling`, `domain-modeling`, `grill-with-docs`). `.claude/skills/` is a generated mirror: run `python scripts/sync_skills.py` after editing.
- `.hermes/`: plans, notes and SDD records (history, not code).
- `TOOLING.md`: verified interpreters, packages, providers and pitfalls. `CHANGELOG.md` and `VERSION` track releases. `docs/REVIEW-th.md` records the weaknesses review.

## Build, Test, and Development Commands

Run from the repository root with FFmpeg on PATH and `GEMINI_API_KEY` set (or in the Hermes `.env`).

```powershell
python -X utf8 scripts/gemini_direct_transcribe.py          # transcribe with model fallback
python -X utf8 scripts/build_gemini_cues.py                 # transcripts -> draft SRT
py -3.12 scripts/import_subtitles_resolve.py                # dry run
py -3.12 scripts/import_subtitles_resolve.py --apply --only 1 2
python -m pytest tests
python scripts/sync_skills.py --check
```

Resolve writes (`--apply`) must use `py -3.12`; the `.venv-aomimama` (3.11) holds `pythainlp` but cannot load `fusionscript.dll`. Set `AOMIMAMA_RUN_ROOT` to use another run folder. Legacy commands are in `.agents/skills/create-subtitle/SKILL.md`.

## Coding Style & Naming Conventions

Four-space Python indentation, `snake_case` functions and variables, uppercase constants. Keep JSON readable with two-space indentation and preserved Thai characters. Use UTF-8 JSON and UTF-8 BOM subtitle output where the legacy builders do. Transcripts are `<timeline-id>.gemini.json`; drafts are `<timeline-id>.draft.srt`. Do not hard-code absolute paths; resolve from `__file__` or an environment variable. No formatter or linter is configured.

## Testing Guidelines

Run `python -m pytest tests` before committing script changes. For behavior changes, validate on a few timelines first (`--only N`) and check: positive cue durations, no overlaps, last cue inside the clip, Thai text, no foreign-script junk, and readback counts after import. Say whether speech sync was actually listened to; drafts are `approved: false` until a person checks them. Report the checks you performed.

## Commit & Pull Request Guidelines

History uses `feat:`, `fix:`, `docs:`, `chore:` (with `chore(release): vX.Y.Z`). PRs describe affected timelines, behavior changes, validation and related issues. Include preview images for visual changes. Release notes are written in Thai in `.hermes/notes/release-vX.Y.Z-notes.md`.

## Configuration & Generated Outputs

Never commit audio, `.drp` backups or rendered video (see `.gitignore`). Never commit API keys. `import_subtitles_resolve.py` skips timelines that already have a subtitle track unless `--replace`. Source media is read-only. Subtitle times are relative to the extracted audio; timeline placement needs the clip's real timeline mapping. Verify drive paths such as `G:` before running anything that reads source media.
