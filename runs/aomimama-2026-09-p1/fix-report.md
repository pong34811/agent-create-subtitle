# Caption helper fixes — RED → GREEN evidence

## Outcome / scope

Fixed all four independently reproduced review findings and the actual timeline-4 timestamp failure in the scratch worktree `C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree`.

No Resolve calls, ASR inference, model loading, child delegation, commits or pushes. Tests use FakeModel only. The actual transcript was read and replayed through caption drafting in memory; no production audio, raw transcript, reviewed JSON, or SRT was modified. Existing implementation and helper-review reports were not overwritten. Parent owns draft regeneration and audio QC.

## Changed files

Relative to the worktree:

- `scripts/aomimama_caption_core.py`
- `scripts/aomimama_asr.py`
- `tests/test_aomimama_captions.py`
- `tests/test_aomimama_asr.py`

Created outside the worktree: this `runs/aomimama-2026-09-p1/fix-report.md`.

The helper files remain untracked (`git status --short`: `?? scripts/`, `?? tests/`), as they were at review baseline. No commit made.

## Root causes / fixes

1. **Timed whitespace / silence:** all characters, including leading spaces, previously consumed interpolated word time; whitespace tokenizer units then set cue endpoints. Whitespace now has no occupied span and is excluded from interpolation denominators (including segment fallback). Text boundaries remain preserved, but cue endpoints derive only from speech spans. Separately timed whitespace does not extend a cue across silence. Text-only whitespace attachment retains Latin boundaries, negation attachment, and multiword protected names without extending timing.
2. **Nested internal intervals:** unit merging and group flush previously used the final fragment end, silently discarding the outer fragment extent. Token, merged-unit and complete-cue bounds now use occupied min/max; internal overlap emits `fragment_overlap_review`. Completed-cue overlap repair remains text-preserving and flagged.
3. **Malformed cache:** metadata equality alone accepted missing transcript content. Added `validate_transcript`, applied to existing raw caches before metadata comparison and new serialization before persistence. Requires schema version 1, metadata identity fields and nested audio/timeline structure, explicit segments list, segment confidence/timing fields, word text/times/probability, and info/duration fields with numeric types (rejects bools and stringified numbers). Invalid JSON/schema fails closed with a reconciliation message, preserving the existing raw bytes and avoiding model calls/draft writes. Explicit `segments: []` remains valid no-speech data. Exact-metadata cached duration must also match the current timeline.
4. **SRT block injection:** public `validate` now requires string cue text without CR/LF. `render_srt` inherits the same rejection. Valid one-line text still round-trips as exactly one SRT block.

### Actual timeline 4: not a timeline-edge rounding failure

Read-only artifact: `transcripts/28e23409-55dc-4284-8a0f-4b0985620b4e.json`.

Baseline replay reproduced `ValueError: invalid or overlapping cue timing`. The offending completed cue was index 9, start=end=24.22, text `ขAc folKate`. Segment 6 spans 18.63–24.22. Its initial fragment occupies 18.63–18.83, while the combining mark and remaining tail fragments are point-aligned at 24.22. A combining-mark-preserving token occupied a positive span through 24.22, but the soft duration split separated its zero-duration tail into an impossible SRT cue.

Added a minimal anonymized regression preserving that timing shape, shifted to zero: initial Thai base at 0–0.2, combining mark and lexical tail at 5.59–5.59. Point-aligned units already contained within the current phrase's occupied interval no longer trigger a heuristic split into an impossible cue. No timestamps are fabricated and no text is deleted. Zero-duration fragments produce a warning log plus `zero_duration_fragment_reconciliation`; the long merged phrase also retains the duration-heuristic flag. Entirely point-aligned speech without an occupied positive interval still fails validation rather than inventing timing.

Final read-only replay: **26 valid cues, all 417 non-whitespace source characters preserved in exact order**, rendered block count equals cue count. Segment 6 remains the full text `เท่าขAc folKate` at 18.63–24.22 with reconciliation/low-confidence/duration flags. Raw bytes compared unchanged before/after; SHA-256 `6acd048e71a42f7a5dffd9b2fe0291315a7a07d3f7bba85d2f8128ecf433690c`.

### Separate millisecond-edge regression

Duration 6508/60 = 108.46666666666667 is not itself representable on the SRT millisecond lattice. Rounding a legitimate endpoint produces 108.467, previously rejected as outside the exact float duration. Build now clamps only the rounded edge to exact duration after checking unrounded lexical intervals. Source endpoints more than half a millisecond beyond duration are rejected/logged for reconciliation. Public validation still rejects float endpoints beyond duration; its SRT lattice limit is the rounded duration (at most half-ms serialization error), not floor(duration*1000). Negative starts, reversed intervals, zero-length cues and precision-collapsed cues remain errors.

## Executed RED → GREEN commands

All commands used this interpreter and cwd:

```text
C:/Users/warit/Desktop/agent-create-subtitle/.venv-aomimama/Scripts/python.exe
C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree
```

Prefix below means `"C:/Users/warit/Desktop/agent-create-subtitle/.venv-aomimama/Scripts/python.exe" -B -m unittest discover -s tests`.

| Command suffix | Actual RED | Actual GREEN |
|---|---|---|
| `-p test_aomimama_captions.py -k whitespace -v` | 1 failed: `(0,3.167),(3.167,4)` instead of `(0,1),(3,4)` | 1 passed |
| `-k nested -v` | 1 failed: nested cue ended at 2 instead of 3 | 1 passed |
| `-k multiline -v` | 1 failed: expected ValueError not raised | 1 passed |
| `-k malformed -v` | 1 failed: missing segments resumed as zero cues; second schema-extension RED also showed malformed nested audio metadata caused automatic re-decode | 1 passed after each fix; 13 malformed mutations plus explicit-empty valid resume exercised |
| `-k timeline4 -v` | 1 error: exact invalid/overlapping timing exception reproduced by derived fixture | 1 passed |
| `-k timeline_edge -v` | 1 error: legitimate rounded endpoint failed timeline bound | 1 passed |
| `-k segment_fallback_excludes -v` | 1 failed: fallback whitespace shifted endpoints to 1.222–1.778 instead of 1–2 | 1 passed |
| `-k whitespace_keeps -v` | 1 failed during whitespace fix hardening: `not gone` split into separate cues | 1 passed; multiword protected name also retained |

Final full suite:

```bash
"C:/Users/warit/Desktop/agent-create-subtitle/.venv-aomimama/Scripts/python.exe" -B -m unittest discover -s tests -v
```

Actual result: **Ran 25 tests in 0.596s — OK**, exit code 0. Expected warning logs from deliberately invalid/zero-duration test inputs are visible; these are reconciliation diagnostics, not test failures. Final actual-transcript in-memory replay also exited 0 after schema, timing, exact lexical-order, SRT-count and unchanged-raw-byte assertions.

## Remaining concerns / parent follow-up

- Zero-duration and distant combining-mark alignment is genuinely uncertain. The flagged 18.63–24.22 phrase spans a suspicious gap inherited from raw occupied alignment; this is not proof of continuous speech or permission to leave it displayed through genuine silence. Audio QC must reconcile its timing. We preserve content/occupied extent rather than silently shortening or inventing word timing.
- Raw ASR Thai text accuracy, names, semantic coherence and viewer readability are not established. No listening performed.
- 36 glyphs / ~4 seconds remain soft heuristics, not hard limits; no three-word/1.5-second cap, repetition deletion, confidence deletion, negation loss or proper-name rewrite was introduced.
- Invalid raw cache requires manual reconciliation; intentionally valid changed-input cache still follows the prior archival/redecode behavior. Existing differing reviewed JSON remains protected and will block regeneration; parent must preserve/reconcile it deliberately rather than overwrite.
- Real draft regeneration was intentionally left to parent. No tooling blocker encountered.
