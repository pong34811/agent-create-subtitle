# Aomimama subtitle helper implementation report

## Status

Implemented in isolated worktree `C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree`, branch `work/aomimama-subtitles`. Nothing committed or pushed. No Resolve calls, rendering, plugin installs, child dispatch, real model initialization, model downloads, or real ASR inference were performed.

Final full test run: **17 tests passed in 1.030 seconds**, exit 0. CLI help, compilation, and git whitespace check also exited 0. Full captured command output: `C:/Users/warit/Desktop/agent-create-subtitle/runs/aomimama-2026-09-p1/implementation-tests.log`.

## Created source files

- `C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree/scripts/aomimama_caption_core.py`
- `C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree/scripts/aomimama_asr.py`
- `C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree/tests/test_aomimama_captions.py`
- `C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree/tests/test_aomimama_asr.py`

No pre-existing repository files were modified. Git status enumerated exactly these four untracked source/test files. The original repository's plan and the worktree's `build_caption_assets.py` were read, never executed. The user's phrase policy supersedes the old scripts and the skill's historical word/duration/script-deletion rules.

## Caption core behavior

Public API: `build_cues(raw, duration, *, max_glyphs=36, target_seconds=4.0, pause_seconds=0.5, protected_terms=())`, `validate(cues, duration)`, `render_srt(cues)`.

- Joins faster-whisper fragments before `newmm` tokenization; interpolates a character-time index instead of treating recognizer fragments as dictionary words.
- Keeps all lexical characters, Thai combining marks, genuine repetition, Latin names/spaces, negations, and suspect foreign scripts. No confidence gate, repetition suppression, game-specific spelling substitutions, or foreign-glyph deletion.
- Splits draft phrases on segment boundaries, pauses of at least 0.5 seconds, sentence punctuation, clause conjunctions, and readable-size/time heuristics. No mandatory word count or 1.5-second cap.
- Counts Unicode combining marks as zero visible glyphs. The 36-glyph single-line and approximately 4-second targets are drafting heuristics, not font measurements or hard validation limits.
- Keeps known names supplied through `protected_terms` or `raw['protected_terms']` indivisible. Attaches common negation tokens to the following token. Unknown proper names still need human QC; no automatic name recognition is claimed.
- Normalizes whitespace and spaces before ordinary punctuation without rewriting spoken text or inserting spaces between Thai tokenizer words.
- Flags suspect foreign scripts, low confidence, missing word times, merged overlaps, and soft-limit exceptions on cues.
- Merges overlapping cues in source order without deduplicating or dropping text. Otherwise rejects impossible/out-of-range/zero-duration timings explicitly. Does not silently drop text to fit timestamps.
- Rounds draft timing to milliseconds before final validation; checks positive monotonic non-overlapping times both numerically and at SRT precision, within the supplied duration.
- Conflicting segment and fragment text raises an explicit reconciliation error rather than guessing which negation/name to lose. Segments without word times use flagged segment-level interpolation.

## Offline ASR helper contract

Required manifest: `<absolute run-root>/manifest.json`, with `{project, timelines:[{index,id,name,start,end,fps}]}`. `end` is exclusive. Expected WAV duration is `(end-start)/fps`; WAV time zero corresponds to timeline start, so nonzero frame starts do not offset SRTs. Duration tolerance is one frame or 10 ms, whichever is larger.

CLI accepts `--run-root` (absolute), `--indices` (one or more integers, default all), `--model` (default `large-v3`), `--device cpu|cuda`, and `--compute int8|float16`. One model is lazily loaded for all non-resumed jobs. Per-timeline progress prints with flushing.

Inputs: `audio/<id>.wav`. PCM WAV payload integrity, duration, selected indices, unique manifest identities, and positive FPS are checked before model loading. WAV SHA-256 is rechecked after decoding to detect concurrent modification.

Raw outputs: `transcripts/<id>.json`, retaining segment text/times, avg_logprob, no_speech_prob, compression ratio, temperature, and each fragment's text/times/probability. Metadata includes exact project/timeline, WAV hash/format/duration, model/device/compute, faster-whisper version and transcribe settings. Resume occurs only on exact metadata equality. Superseded raw bytes are archived in `transcripts/archive/<id>.<sha256>.json` before replacement.

Draft outputs: `reviewed/<id>.json` with `approved:false`, `qc_required:true`, `status:unreviewed_draft`, policy, metadata, duration and cues; and UTF-8 `srt/<id>.draft.srt`. Existing reviewed JSON is left intact if exactly identical, or execution stops if it differs, protecting human corrections and approved reviews. No approval or import functionality exists.

Windows CUDA package DLL directories are discovered from installed torch/nvidia packages and registered before importing faster-whisper; DLL directory handles are retained. No packages are installed by the helper.

## Test commands and real results

Working directory for all commands: the isolated worktree above.

```bash
'C:/Users/warit/Desktop/agent-create-subtitle/.venv-aomimama/Scripts/python.exe' -m unittest discover -s tests -v
# Ran 17 tests in 1.030s; OK; exit 0

'C:/Users/warit/Desktop/agent-create-subtitle/.venv-aomimama/Scripts/python.exe' scripts/aomimama_asr.py --help
# Correct requested CLI options printed; exit 0

'C:/Users/warit/Desktop/agent-create-subtitle/.venv-aomimama/Scripts/python.exe' -m py_compile scripts/aomimama_caption_core.py scripts/aomimama_asr.py tests/test_aomimama_captions.py tests/test_aomimama_asr.py
# No errors; exit 0

git diff --check
# No output; exit 0 (new source files remain untracked)
```

TDD was exercised in successive RED/GREEN slices, not by copying the superseded plan's short-cue implementation. Observed missing-behavior failures included: missing core; missing configurable phrase splitting; missing foreign-script flags; overlap validation before repair; missing SRT renderer; missing ASR helper; human review overwritten on rerun; missing archive of invalidated raw; duplicate identity not rejected before loading; truncated WAV accepted; missing Windows DLL discovery; missing soft-limit flags; invalid FPS division; conflicting fragment/segment text not rejected; punctuation spacing; and audio changed during decode not rejected. Each was followed by minimal implementation and a passing suite. Additional existing-behavior tests verified exact half-second pause splitting and segment fallback.

Coverage includes preserved low-confidence speech, five coherent Latin words lasting 3 seconds, long Thai phrase splitting, protected Thai names/negation/combining marks, genuine repetition, Latin and punctuation spacing, overlap/gap preservation, SRT parse consistency, impossible millisecond/out-of-duration times, heuristic exceptions, batch single model load, exact resume, hash invalidation, unapproved drafts, review protection, full WAV preflight, and mutation detection.

ASR tests deliberately inject a deterministic fake model because real ASR was expressly prohibited in this task. Generated PCM WAVs and recognizer-shaped test transcripts are fixtures, not production ASR evidence. The test log's model-loading messages describe calls to that injected factory, not a real loaded large-v3 model. Caption tokenization and all file/manifest/cache/SRT processing run the actual implementation. Test temporary directories are cleaned up; final runs use the explicit Hermes scratch directory (the inherited TMPDIR initially pointed to Windows Temp, so the tests were corrected to avoid relying on it).

## Remaining concerns / handoff

- **No real ASR/model smoke test or audio-language QC has run.** This is an implemented and fixture-tested helper, not verified production transcription. Start inference only after the controller confirms selected WAVs are complete.
- **Offline loading is deliberate:** `local_files_only=True`. A cached faster-whisper large-v3 model must already exist, or an authorized separate model download/preparation step is needed. This task neither checked cache readiness through model initialization nor downloaded a model. CUDA/native inference and CPU float16 compatibility are not claimed; CPU/int8 is the default.
- Phrase boundaries are conservative heuristics, not a semantic parser. Human listening must check unfamiliar names, conjunction boundaries, repetitions, foreign-language/game announcer speech, pauses, and soft-limit exceptions. Protected names can be configured through the core API, but are not inferred from timeline names.
- Out-of-range or millisecond-impossible captions stop with an error instead of deleting words. Raw transcripts are persisted before caption-building errors so reconciliation can continue without rerunning inference. Conflicting reviewed artifacts also stop for manual reconciliation.
- Output SRTs are explicitly `.draft.srt`, separate from any final `<id>.srt` chosen after approval. Do not import drafts merely because they exist.

The helpers are ready for the parent agent's review/integration from the isolated worktree; there is no commit to cherry-pick.
