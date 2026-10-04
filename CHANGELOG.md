# Changelog

## v0.2.0

Add project skill, AGENTS.md, and local transcript work.

### Added
- `.agents/skills/create-subtitle/`: project-specific subtitle workflow skill with agents config
- `AGENTS.md`: repository guidelines at root
- `work/2026-10-02_190418/`: local transcript work folder (Soul Walker 005) with aligned captions, review assets, DRIs, and UI state snapshots

## v0.1.0

First versioned release of the Thai subtitle creation pipeline.

### Added
- Agent skills under `.agents/skills/`, synced from the live Hermes copies:
  - `thai-subtitles-resolve`: Whisper ASR to Thai SRT, scripted SRT import into native Resolve Subtitle tracks, and readback verification. Now also documents how subtitle track presets are stored (`User.db` `SubtitlePresetsBA` = track `EffectFiltersBA`).
  - `resolve-mitr-subtitle-presets` (new): applies saved Subtitle track presets by orientation. `Mitr Font` goes on 16:9 (1920x1080) and `Mitr-short-001` on 9:16 (1080x1920). Bundles `scripts/load_subtitle_preset.py`, which is a dry run by default; `--apply` makes a `.drp` and `Project.db` backup, writes one transaction, reopens the project and verifies.
  - `thai-proofread`: Thai spelling, tone mark and caption house-style checks.
- `transcript-work/`: Soul Walker 005 (HellCityClear) transcription work: Thai SRT, prompted ASR JSON, and original, dynamic and reviewed `.drt` timelines.

### Existing (initial commit)
- Transcription (`transcribe_caption_jobs.py`, `transcribe_thai_finetuned.py`) and caption asset builders (`build_caption_assets.py`, `build_thai_caption_assets.py`), along with transcripts, caption assets and fonts.

### Scope
- The preset loader has been verified live with `--apply` on one 16:9 project (10/10 tracks). The 9:16 path is dry-run tested only.
