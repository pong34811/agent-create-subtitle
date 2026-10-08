# Changelog

## v0.4.0

Project audit: skills brought in line with the real (Gemini) pipeline, the
archived Whisper pipeline moved aside, clutter removed, weaknesses documented.

### Added
- `docs/REVIEW-th.md`: Thai review of the skills and of the project's weak points
  when instructing an agent to make Thai subtitles.
- `scripts/sync_skills.py` (`--check`): `.agents/skills` is the source of truth,
  `.claude/skills` is the mirror Claude Code actually loads.
- `GEMINI_API_KEY` from the environment is accepted by `gemini_direct_transcribe.py`.

### Changed
- `thai-subtitles-resolve`: the repo copy was stale. The Gemini-ASR version and
  `references/gemini-asr-pipeline.md`, which v0.3.0 claimed to ship but only
  existed in the Hermes skills folder, are now in the repository.
- `thai-proofread`: synced with the maintained copy.
- `create-subtitle`: rewritten. Gemini ASR is the default route, Whisper is
  documented as legacy, and the six pipeline steps are tied to their scripts and
  sibling skills.
- `AGENTS.md`: rewritten for the current layout and commands.
- Six scripts no longer hard-code `C:/Users/warit/...`; the run root comes from
  `AOMIMAMA_RUN_ROOT` or the script location.
- The K404 Whisper batch moved to `legacy/k404-whisper/` (scripts, transcripts,
  captions, job list, Mitr font), self-contained.

### Removed
- `work/2026-10-02_190418/` (41 scratch files incl. `speech.wav`), `transcript-work/`,
  root-level K404_29 sample captions and `caption-sample*.png`.
- `.hermes/skills/` (byte-identical duplicate of `.claude/skills`).
- Local-only renders: 2 root `.mov` and `caption_assets_final/rendered/` (~930 MB),
  all regenerable from the ASS files; plus pytest and `__pycache__` caches.

## v0.3.0

Full Gemini-ASR subtitle run for the `aomimama-2026-09-p1` project: 49 timelines
transcribed, imported into Resolve, and styled.

### Added
- `scripts/import_subtitles_resolve.py`: imports drafted SRTs into Resolve
  subtitle tracks and verifies by readback. Dry run by default; `--apply` writes.
  `--only N...` for a subset, `--replace` to delete an existing track first.
- `tests/test_import_subtitles.py`: 7 tests (SRT parsing, import planning, no cue
  exceeding its timeline).
- `scripts/aomimama_caption_core.py` and `scripts/aomimama_asr.py` with
  `tests/test_aomimama_asr.py` + `tests/test_aomimama_captions.py`: the phrase
  splitter and transcript quality gates built earlier in the scratch worktree.
  Project suite is now **32 tests**.
- `scripts/gemini_direct_transcribe.py`: Gemini ASR with per-model quota fallback,
  a stated file duration to stop timestamp drift, and recovery from repetition
  loops, truncated JSON, blocked responses and all-uncertain replies.
- `scripts/transcribe_chunked.py`: splits clips over ~100 s at their quietest
  seconds so long timelines keep correct timestamps.
- `TOOLING.md`: verified inventory of interpreters, packages, providers, scripts
  and the pitfalls that cost real debugging time.
- `.hermes/notes/grill-with-docs-troubleshooting.md`: why `/grill-with-docs` was
  not invocable (a stale in-process skill-command cache, not the skill).
- `.agents/skills/grilling`, `.agents/skills/domain-modeling`: `grill-with-docs`
  is a wrapper that delegates to these two; neither was present, so it could
  never load.

### Updated
- `thai-subtitles-resolve`: description corrected from Whisper to Gemini ASR, a
  new `references/gemini-asr-pipeline.md` (model ranking, prompt requirements,
  four failure modes, chunking, Thai spacing, provider comparison), and the
  `SetCurrentTimeline` trap folded into SKILL.md — the cause of a 0-of-3 first
  import attempt.
- `thai-proofread`: description shortened to fit the 60-character index limit.
- `.gitignore`: `*.wav`/`*.mp3`/`*.m4a`/`*.flac` plus `runs/*/audio/` and
  `runs/*/backups/`, after 101 rendered WAVs (964 MB) were committed by mistake
  in this branch's history and removed by rewriting the unpushed commit.

### Verified
- **49 of 49 timelines** in `aomimama-2026-09-p1` have a subtitle track whose cue
  count matches its SRT exactly — checked twice, once by the import script's
  readback and once by an independent Resolve query. **963 cues total.**
- Text retention from transcript to cue is **100.00 %**; no cue's timestamps
  exceed its file duration; zero Thai inter-word spacing violations; all 49 SRTs
  parse with monotonic timing.
- `Mitr Font` applied to all **49** subtitle tracks (`--apply` on a live project),
  verified by comparing the pre-write `Project.db` snapshot to the current blob
  (111 -> 288 bytes each). Re-running the dry run reports
  `0 of 49 subtitle track(s) would change.`
- Test suite: `./.venv-aomimama/Scripts/python.exe -m pytest tests/ -q` -> 32 passed.
- Backup for the style write:
  `~/Documents/resolve-subtitle-preset-backups/aomimama-2026-09-p1_20261006-150958/`
  (`.drp` + `Project.db` snapshot).

### Scope
- Cues are drafts: every `reviewed/*.gemini.json` is `approved: false`. No human
  listening pass has been done.
- The 49 transcripts came from 7 different Gemini models because the free-tier
  daily quota forced automatic fallback; 9 files used `gemini-2.5-flash`, the
  weakest of the set.
- 14 cues carry timing flags (`timestamp_beyond_duration`,
  `start_clipped_to_previous`, `overlap_merged`); text is intact, display timing
  was adjusted.
- Timeline 11 is game noise with no speech (spectral check: zcr 1595 Hz, 0 %
  quiet frames); its single recovered line is genuine.
- The `.drp` backup under `runs/*/backups/` is no longer ignored; the
  `runs/*/audio/` WAVs are ignored and must be re-rendered with the pipeline.

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
