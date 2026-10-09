# Repository Guidelines

## Project Structure & Module Organization

This repository makes Thai gaming subtitles. The **current pipeline** is Gemini
ASR → SRT → DaVinci Resolve subtitle tracks (runs `aomimama-2026-09-p1` and
`aomimama-2026-09-p2`, one run folder per Resolve project). The original Whisper
pipeline is archived under `legacy/`. Gemini replaces only Whisper; FFmpeg is
still used to turn the rendered mix into mono 16 kHz WAV.

- `scripts/`: current pipeline.
  - `prepare_run.py` reads the OPEN Resolve project: `manifest` (backup `.drp` + `manifest.json`) and `audio` (render each timeline's mix, then FFmpeg to 16 kHz mono).
  - `gemini_direct_transcribe.py` and `transcribe_chunked.py` transcribe.
  - `build_gemini_cues.py` builds cues and SRT.
  - `import_subtitles_resolve.py` imports to Resolve (dry run by default).
  - `aomimama_asr.py` and `aomimama_caption_core.py` are the phrase splitter and quality gates.
  - `compare_asr*.py` are model comparisons.
  - `run_pipeline.py` is the single entry point (`status|transcribe|cues|verify|import`).
  - `verify_cues_audio.py` checks cues against audio energy; `check_thai_text.py` applies Thai proofreading rules; `thai_text.py` is the deterministic clean-up.
  - `sync_skills.py` mirrors skills.
- `vocab/games.json`: game titles and preferred spellings for the transcription prompt and spell-check.
- `tests/`: pytest suite (46 tests).
- `runs/<run>/`: manifests, transcripts, reviewed JSON, SRT drafts, reports and logs for one batch (`audio/`, `backups/` hold WAVs and `.drp` files). `runs/` is now in `.gitignore`; files committed earlier (p1, p2) stay tracked until removed with `git rm --cached`.
- `legacy/k404-whisper/`: K404 batch, the Whisper transcribers and builders, their transcripts, ASS/SRT and the Mitr font. Self-contained; run scripts from inside it.
- `.agents/skills/`: project skills, the source of truth (`create-subtitle`, `thai-subtitles-resolve`, `thai-proofread`, `resolve-mitr-subtitle-presets`, `grilling`, `domain-modeling`, `grill-with-docs`). `.claude/skills/` is a generated mirror: run `python scripts/sync_skills.py` after editing.
- `.hermes/`: plans, notes and SDD records (history, not code).
- `GLOSSARY.md` (project vocabulary) and `docs/adr/` (decisions).
- `TOOLING.md`: verified interpreters, packages, providers and pitfalls. `CHANGELOG.md` and `VERSION` track releases. `docs/REVIEW-th.md` records the weaknesses review.

## Build, Test, and Development Commands

Run from the repository root with FFmpeg on PATH and `GEMINI_API_KEY` set (or in the Hermes `.env`).

```powershell
python scripts/run_pipeline.py status                       # what exists, per stage
python -X utf8 scripts/gemini_direct_transcribe.py          # transcribe with model fallback
python -X utf8 scripts/build_gemini_cues.py                 # transcripts -> draft SRT
py -3.12 scripts/import_subtitles_resolve.py                # dry run
py -3.12 scripts/import_subtitles_resolve.py --apply --only 1 2
python -m pytest tests
python scripts/sync_skills.py --check
```

Resolve writes (`--apply`) must use `py -3.12`; the `.venv-aomimama` (3.11) holds `pythainlp` but cannot load `fusionscript.dll`. Set `AOMIMAMA_RUN_ROOT` to use another run folder (default is `runs/aomimama-2026-09-p1`, so ALWAYS set it for p2 or a new project). Legacy commands are in `.agents/skills/create-subtitle/SKILL.md`.

### Workflow for a new Resolve project (what was done for p2)

1. Open the project in Resolve and check its name and timeline count. Ask before replacing existing subtitle tracks.
2. `py -3.12 scripts/prepare_run.py manifest`, then confirm the `.drp` backup exists and is not empty. Do not replace anything without it.
3. `py -3.12 scripts/prepare_run.py audio` (compare each WAV's length with the timeline).
4. `run_pipeline.py transcribe` (resumable; quota fallback mixes models, and a timeline answered "no audio" can be retried by moving its transcript aside and rerunning that index).
5. `run_pipeline.py cues`, `verify`, `check`.
6. `run_pipeline.py import` (dry run), then `--only N --apply --replace` on 2 timelines, then all.
7. Save the project in Resolve, then load the preset with `resolve-mitr-subtitle-presets` (`Mitr Font` for 1920x1080, `Mitr-short-001` for 1080x1920). Re-importing resets the track style, so the preset must be reapplied after every re-import. Re-run its dry run and expect `0 of N ... would change`.

### Cue length (short-form / vertical)

Defaults stay at 36 glyphs and no display cap. For Shorts set `AOMIMAMA_MAX_GLYPHS=12` and `AOMIMAMA_MAX_DISPLAY=2.0` before `run_pipeline.py cues`. Glyphs exclude tone and vowel marks, so Resolve's "characters" count is about 1.2x larger. 10 glyphs flickers (median 0.8 s); 12 gave a median of about 1 s. Keep the previous `srt/` before regenerating.

### Known pitfalls

- `--replace` must find the cached SRT pool item in every sub-bin; otherwise Resolve re-imports the old cues and the readback count equals the OLD count.
- `ExportProject` can fail silently (returns None) and writes nothing; verify the file.
- The preset step refuses with "DB has N subtitle tracks but Resolve reports M" until the project is saved.
- `AddTrack`/`AppendToTimeline` act on the active timeline; `GetProperty('Speed')` returns False here, so it is not evidence about retimed clips.
- The audio check measures energy only; it never proves the words match.

## Coding Style & Naming Conventions

Four-space Python indentation, `snake_case` functions and variables, uppercase constants. Keep JSON readable with two-space indentation and preserved Thai characters. Use UTF-8 JSON and UTF-8 BOM subtitle output where the legacy builders do. Transcripts are `<timeline-id>.gemini.json`; drafts are `<timeline-id>.draft.srt`. Do not hard-code absolute paths; resolve from `__file__` or an environment variable. No formatter or linter is configured.

## Testing Guidelines

Run `python -m pytest tests` before committing script changes. For behavior changes, validate on a few timelines first (`--only N`) and check: positive cue durations, no overlaps, last cue inside the clip, Thai text, no foreign-script junk, and readback counts after import. Say whether speech sync was actually listened to; drafts are `approved: false` until a person checks them. Report the checks you performed.

## Commit & Pull Request Guidelines

History uses `feat:`, `fix:`, `docs:`, `chore:` (with `chore(release): vX.Y.Z`). PRs describe affected timelines, behavior changes, validation and related issues. Include preview images for visual changes. Release notes are written in Thai in `.hermes/notes/release-vX.Y.Z-notes.md`.

## Configuration & Generated Outputs

Never commit audio, `.drp` backups or rendered video (see `.gitignore`). Keep a `.drp` backup before any `--replace`. Never commit API keys. `import_subtitles_resolve.py` skips timelines that already have a subtitle track unless `--replace`. Source media is read-only. Subtitle times are relative to the extracted audio; timeline placement needs the clip's real timeline mapping. Verify drive paths such as `G:` before running anything that reads source media.
