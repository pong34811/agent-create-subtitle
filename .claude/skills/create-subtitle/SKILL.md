---
name: create-subtitle
description: Create Thai SRT subtitles for gaming clips/timelines (Gemini ASR).
---

# Create Subtitle

Entry point for making Thai subtitles in this repository. It routes to the right
pipeline and sibling skill; the detail lives there, not here. Resolve the
repository root from this skill's location (three directories up), never from
the shell's current directory.

## Decide first (ask only what is missing)

1. **Source**: a Resolve project's timelines, or loose audio/video files?
2. **Deliverable**: SRT sidecars only, SRT imported into Resolve subtitle
   tracks, or styled ASS / rendered overlay? "Make subtitles" alone means SRT
   sidecars. It is not permission to touch a Resolve project or render video.
3. **Style**: natural phrases (current default) or the legacy 1-4 token
   "gaming cards"? Do not mix them in one batch.
4. **Language**: Thai. Anything else needs a changed prompt and tokenizer.

## Pipeline A — Gemini ASR (default, current)

One entry point picks the right interpreter per stage:
`python scripts/run_pipeline.py status|transcribe|cues|verify|import [N ...]`.
`import` is a dry run unless `--apply` is given. Vocabulary is in `GLOSSARY.md`;
why Gemini and not Whisper is in `docs/adr/0001-gemini-asr-over-whisper.md`.

Proven on 49 Resolve timelines (`runs/aomimama-2026-09-p1`). Whisper is **not**
the default: it produced garbled or hallucinated Thai on game audio. Do not
re-litigate without new evidence; the measurements are in
`.agents/skills/thai-subtitles-resolve/references/gemini-asr-pipeline.md`.

| Step | Script / skill | Output |
| --- | --- | --- |
| 1. Render audio per timeline (16 kHz WAV) | ffmpeg | `runs/<run>/audio/*.wav` (git-ignored) |
| 2. Transcribe, model fallback chain | `scripts/gemini_direct_transcribe.py` | `transcripts/<id>.gemini.json` |
| 2b. Clips over ~100 s | `scripts/transcribe_chunked.py` | split at quietest seconds |
| 3. Review `uncertain` segments, then build cues | `scripts/build_gemini_cues.py` | `srt/<id>.draft.srt` |
| 3b. Plausibility check against audio | `scripts/verify_cues_audio.py` | `audio-verification.json`: cues to listen to first |
| 4. Proofread Thai text | skill `thai-proofread` | corrected cues |
| 5. Import to subtitle tracks (dry run first) | `scripts/import_subtitles_resolve.py` | readback-verified |
| 6. Apply Mitr preset by orientation | skill `resolve-mitr-subtitle-presets` | styled tracks |

Requirements: `GEMINI_API_KEY` in the environment (or the Hermes `.env`),
FFmpeg on PATH. Set `AOMIMAMA_RUN_ROOT` to point scripts at another run folder;
the default is `runs/aomimama-2026-09-p1` next to the scripts.

**Two interpreters, on purpose.** Tokenizing (`pythainlp`) runs in
`.venv-aomimama` (3.11). Anything that writes to Resolve (`--apply`) must run
under `py -3.12`, because the 3.11 venv cannot load `fusionscript.dll`. A dry
run passes in either, which is why this fails late. See `TOOLING.md`.

Read `thai-subtitles-resolve` before any Resolve write. It records the traps
that cost real debugging time: make the target timeline current before
`AddTrack`/`AppendToTimeline`, `ImportMedia` caches by path, native Subtitle
tracks only (never Text+), source media is read-only.

## Pipeline B — Whisper (legacy, archived)

`legacy/k404-whisper/` holds the original K404 batch: CPU `faster-whisper`
(`large-v3`) and CUDA `bjak/distill-whisper-th-large-v3`, with builders that
write short 1-4 token cards and styled ASS. Use it only to reproduce or tweak
those 28 K404 clips, or for clean studio speech. Scripts resolve paths relative
to themselves, so run them from inside that folder. Its job list points at
media on `G:`; confirm the drive is mounted. The builders contain corrections
specific to that batch; inspect them before reuse.

## Timing rules

- Cue times are relative to the extracted audio. Timeline time is
  `wav_time + clip_timeline_start`. Multi-cut, retimed (`Speed != 1`) or
  reordered timelines break the linear mapping; obtain the real mapping first.
- New cues: no overlap, positive duration, final cue ends inside the timeline,
  display cap about 2.2 s, minimum gap about 2 frames. Never drop words to fit;
  flag them.
- Gemini timestamps drift unless the prompt states the exact file duration and
  forbids timestamps beyond it. The shipped prompt does; keep that line.

## Check before saying "done"

Reparse the written SRTs as UTF-8 and assert: consecutive indices, `end > start`,
no overlaps, last cue within the clip, no foreign-script junk, no leftover
`[ฟังไม่ชัด]` unless intended. Run `python -m pytest tests` (39 tests). State
plainly whether the audio was actually listened to: drafts are `approved: false`
until a person has checked them against speech. Never claim sync you did not
verify. `verify_cues_audio.py` only shows that audio exists under a cue; it does not
prove the words. Re-running Gemini on the same audio gives different words and
timestamps up to ~2 s apart, so do not regenerate an approved Draft casually.

## Hygiene

- Do not commit audio (`*.wav` etc.), `.drp` backups or rendered video.
  `.gitignore` already blocks them; check `git status` before committing.
- Keep job/run folders for one-off experiments under `runs/` or a scratch
  folder, not the repository root.
- After editing any skill under `.agents/skills`, run
  `python scripts/sync_skills.py` so `.claude/skills` (the copy Claude Code
  loads) matches.
