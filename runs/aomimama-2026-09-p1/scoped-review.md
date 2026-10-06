# Scoped re-review — subtitle helper fixes

## Verdicts

- **Spec compliance: PASS for this fix scope.** All four required findings are addressed; zero-duration-tail and fractional-frame regressions retain lexical content or fail explicitly rather than silently deleting it.
- **Task / code quality: PASS for this fix scope.** Focused regression coverage exercises the reported failure shapes and preservation boundaries. No new Critical/Important breakage identified in the fixes.
- **Production / speech accuracy: NOT VERIFIED.** These verdicts do not approve ASR text, inferred word alignment, natural Thai phrasing, silence handling against actual audio, or viewer readability. Audio-capable analysis remains unavailable; listening/QC is still required.

## Four dispositions

References are relative to `C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree/`.

| Prior finding | Disposition | Verified evidence |
|---|---|---|
| Timed whitespace crossing silence | **ADDRESSED** | `scripts/aomimama_caption_core.py:30–47,55–63,82–86,93–100,161–164`: spaces retain textual boundaries but have no occupied span and do not consume interpolation time. Leading-space words, separately timed whitespace, and Thai/Latin boundaries now produce `(0,1)` and `(3,4)` rather than displaying the first cue across the pause. Fallback and negation/protected multiword-name regressions also pass. |
| Nested internal occupied intervals | **ADDRESSED** | Core `:37–39,93–100,161–164,196–203`: fragment overlap is flagged; token, merged-unit and cue timing use occupied min/max. Nested `hello world` and merged `Alice!` retain end 3, original text, and `fragment_overlap_review`. Completed overlap repair continues to preserve text with an explicit flag. |
| Damaged raw cache resume | **ADDRESSED** | `scripts/aomimama_asr.py:78–130,170–180,212–220`: required raw/nested metadata, confidence and word fields are validated before resume or replacement; malformed JSON/schema raises reconciliation instead of interpreting absent transcript content as no speech. Targeted test verifies 13 malformed mutations leave raw bytes intact, make no further fake transcribe call, and write no review/SRT. Explicit `segments: []` remains valid no-speech input. Exact-metadata duration mismatch also fails explicitly. |
| CR/LF SRT injection | **ADDRESSED** | Core `:116–119,215–226`: public validation rejects nonstring and CR/LF-bearing cue text; renderer uses that validation. Injection, CR and LF cases fail; one-line names/negation/repetition round-trip as one block with unchanged text. |

## Zero-tail / rounding consistency

- Core `:178–185` keeps a point-aligned tail contained inside an already occupied phrase from being split into an impossible zero-length cue. It neither drops text nor fabricates a separate speech interval; `zero_duration_fragment_reconciliation` and heuristic flags retain the uncertainty. Entirely point-aligned speech still raises rather than disappearing into an empty draft.
- Core `:141–144,191–195` rejects lexical spans outside the stated half-millisecond edge tolerance, then clamps a rounded edge to exact timeline duration. Public validation still rejects an actual cue endpoint beyond the float duration and checks positive, sorted, non-overlapping SRT-lattice timing. The fractional-frame regression verifies exact-duration and +0.0004-second inputs, rejection of +0.0006-second/negative/reversed inputs, and the expected `00:01:48,467` serialized edge. This is an explicit precision policy, not evidence of submillisecond speech accuracy.
- Independently replayed the actual timeline-4 raw sidecar **in memory only**: schema valid; **26 valid cues; all 417 non-whitespace source characters preserved in exact order; 26 rendered SRT blocks**. Raw bytes remained unchanged, SHA-256 `6acd048e71a42f7a5dffd9b2fe0291315a7a07d3f7bba85d2f8128ecf433690c`.
- The formerly failing segment remains `เท่าขAc folKate`, 18.63–24.22, with zero-duration reconciliation, low-confidence and duration-heuristic flags. Occupied-span preservation is not confirmation of continuous speech through that interval. Suspicious long occupied alignments remain parent-owned audio-QC work, not a newly discovered regression or permission to hold captions over verified silence.

## Verification and scope limits

Read the scope package first, prior review, fix report, and all four complete current added files. No commits exist for these additions, so reviewed the complete files as the supplied new-file change set. Applied independent review discipline; no implementation, child delegation, commits, model loading or Resolve actions.

Executed only eight targeted existing tests: seven caption regressions covering the required timing/SRT/zero-tail/edge cases plus the malformed-cache regression. Command used `.venv-aomimama/Scripts/python.exe -B` with an explicit `unittest.TestSuite`; **8 tests in 0.457s, OK, exit 0**. The cache test uses `FakeModel` exclusively; its `loading large-v3` console text is the helper's generic log, not a real model load. Scratch-only fake artifacts were cleaned by the test. Expected invalid/zero-duration warnings are reconciliation evidence, not failures. Did not repeat the parent's already-green 25-test suite.

No source/test edits and no production audio, transcript, reviewed JSON or SRT writes. Only durable artifact created: this report. No tooling blocker encountered. Transcript accuracy and final caption approval remain blocked pending actual listening/audio QC.
