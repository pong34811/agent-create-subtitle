# aomimama-2026-09-p1 — subtitle generation status

49/49 timelines transcribed, 963 cues drafted, 49 SRT files written.
**Nothing has been imported into DaVinci Resolve. All cues are `approved: false`.**

## What was produced

| Artifact | Path |
|---|---|
| Raw ASR (per timeline) | `runs/aomimama-2026-09-p1/transcripts/<timeline-id>.gemini.json` |
| Cue drafts (reviewed) | `runs/aomimama-2026-09-p1/reviewed/<timeline-id>.gemini.json` |
| Subtitle files | `runs/aomimama-2026-09-p1/srt/<timeline-id>.draft.srt` (UTF-8 BOM) |
| Rendered audio | `runs/aomimama-2026-09-p1/audio/<timeline-id>.wav` (mono 16 kHz) |

## Verified quality gates

| Check | Result |
|---|---|
| Text retention (source segments → cues) | **100.00 %** — no word dropped |
| Timestamps beyond file end | **0 files** |
| Thai inter-word spacing violations | **0 cues** |
| SRT parse + monotonic timing | **49/49 pass** |
| Files with no real speech | **0** (timeline 11 has game noise only, not speech) |

## Models actually used

| Count | Model |
|---|---|
| 12 | gemini-3.5-flash |
| 10 | gemini-3.5-flash-lite |
| 9 | gemini-3-flash-preview |
| 9 | gemini-2.5-flash |
| 2 | gemini-3.1-flash-lite |
| 2 | gemini-3.6-flash |
| 2 | gemini-3.7-flash |
| 3 | chunked (see below) |

Measured ranking (same audio, `scripts/compare_asr_v2.py`): **3.7-flash > 3.6-flash >
3.5-flash > 3.5-flash-lite > 3-flash-preview > 3.1-flash-lite > 2.5-flash >>
whisper-large-v3 (Groq, unusable for Thai)**.

## Known limitations

1. **14 cues carry flags** (`timestamp_beyond_duration`, `start_clipped_to_previous`,
   `overlap_merged`) — the model's segment boundaries touched; text is intact but the
   display timing was adjusted. Review these before importing.
2. **Model mix**: the free-tier daily quota forced automatic fallback, so the 49 files
   were not all produced by one model. `gemini-2.5-flash` (9 files) inserts word spaces
   and was the weakest of the set — those files are worth re-running after quota reset.
3. **`[ฟังไม่ชัด]` markers** are kept inline where the model was unsure; they are
   deliberate and should be resolved by a human listening pass.
4. **Timeline 11** (`กวาดห้องจนจบภารกิจ-alien shooter-vdo`) is game noise with no
   speech: spectral check shows zcr 1595 Hz and 0 % quiet frames (speech shows ~220 Hz
   and ~88 % quiet). Its single recovered line is genuine.

## Providers tested and rejected

| Provider | Result |
|---|---|
| Groq `whisper-large-v3` | works, but Thai output is unreadable ("ฮัลโหล" → "เหลื่อการพังสะพาน") |
| OpenRouter free audio | 403 "agentic harnesses only"; nvidia omni needs $0.50 balance |
| opencode zen | 403 "free tier can only be used from within OpenCode" |
| Ollama Cloud | API has no audio input; every model replies "I cannot hear audio" |
| FreeLLMAPI (local) | 505 models listed but audio never reaches the model |
| Hermes/Nous proxy | removed at user request |

## How to regenerate

```bash
# transcribe every timeline missing a direct-route transcript (resumable)
python scripts/gemini_direct_transcribe.py

# re-run specific timelines
python scripts/gemini_direct_transcribe.py 5 12 13

# long timelines whose timestamps drift (>~100s) — splits at quiet points
python scripts/transcribe_chunked.py 13 41 46

# rebuild cues + SRT from transcripts (needs the pythainlp venv)
./.venv-aomimama/Scripts/python.exe scripts/build_gemini_cues.py
```

## Next step (not done)

Import the 49 `srt/*.draft.srt` into their Resolve subtitle tracks. That requires the
parent process to drive Resolve: `ImportMedia` → `AddTrack('subtitle')` →
`AppendToTimeline` with the bare `{'mediaPoolItem': item}` payload. Do **not** import
before a human review pass — the cues are drafts.
