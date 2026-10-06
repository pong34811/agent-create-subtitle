# Independent review: Aomimama caption core and ASR helper

## Verdicts

- **Spec compliance: FAIL pending timing and resume fixes.** The approved natural-phrase policy is substantially respected, but whitespace can park a caption across a real silence, internal overlapping word times can silently truncate its display interval, and malformed cached raw data can silently become an empty transcription.
- **Code quality: CHANGES REQUIRED.** Four reproducible findings below; no source changes proposed or applied in this review.
- **Production readiness: not established.** The supplied 17-test green results are fake-ASR evidence, not real transcription, CUDA inference, or listening/viewer QC. Parent owns those checks.

Scope: read the review package first, all four complete added files, implementation report, and the original plan including its superseding confirmed caption policy. Reviewed baseline HEAD `2ebc3e5544829cae6702b4260ca2c2141ed98107`. File references below are relative to `C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree/`.

Severity: P1 = high-priority policy/timing defect; P2 = correctness or fail-closed validation defect.

## Findings

### 1. P1 — Timed whitespace extends the preceding caption across a pause

**Location:** `scripts/aomimama_caption_core.py:126-138`, especially unconditional `group.append(unit)` at line 138 and flush boundaries at lines 119-123.

A whitespace-only tokenizer unit is appended to the current group before the following spoken unit triggers a pause break. Rendering strips that whitespace, but the preceding cue still takes its end time. Faster-whisper's common leading-space word shape therefore extends the old caption through silence and delays the next visible word by the interpolated space duration.

**Executed reproduction:** one segment with text `hello world`; words `hello` at `[0, 1]` and ` world` at `[3, 4]`; timeline duration 5. Actual output:

```text
[0.000, 3.167] hello   flags=[]
[3.167, 4.000] world   flags=[]
```

The input has a two-second speech gap `[1, 3]`; the caption persists throughout it. This directly conflicts with the confirmed requirement not to hold captions through silence. A soft four-second target does not make this silence acceptable.

**Minimal remedy:** preserve spacing in text without making whitespace extend a spoken cue's timing. Base pause decisions and display boundaries on non-whitespace speech character spans; deliberately handle leading spaces in the next word. Add regressions for leading-space recognizer words and separately timed spaces around Thai/Latin boundaries, asserting the prior cue ends with prior speech and the next cue starts with next speech.

### 2. P2 — Internal overlapping word times lose the true end without a review flag

**Location:** `scripts/aomimama_caption_core.py:64-67` and `scripts/aomimama_caption_core.py:122-123`.

Individual fragments are checked for finite, nonnegative-length intervals, but their temporal relationship is not checked. Unit merging and cue flush use the last unit's end rather than the maximum occupied end. Nested or decreasing word end times can silently shorten a caption; the later cue-level overlap repair never sees the lost interval.

**Executed reproduction:** text `hello world`; words `hello` at `[0, 3]` and ` world` at `[1, 2]`; duration 5. Actual output is one cue `[0, 2] hello world`, `flags=[]`. The source's first word extends to 3, but the final second is discarded from caption timing.

**Minimal remedy:** explicitly reject inconsistent internal fragment ordering for reconciliation, or preserve the full occupied interval with min/max bounds and an explicit overlap/alignment review flag. Apply this to both merged units and complete groups, not just overlap between completed cues. Add a regression with nested fragment intervals and decreasing ends.

### 3. P2 — Matching metadata alone permits a damaged cache to resume as zero speech

**Location:** `scripts/aomimama_asr.py:115-119`, combined with `scripts/aomimama_caption_core.py:104`.

Resume accepts any parsed JSON object whose metadata matches, without validating the raw transcript schema or completeness. `build_cues` treats an absent `segments` field as an empty segment list. A damaged or incorrectly edited cache retaining metadata is therefore reported as a successful exact resume, with no inference and no reconciliation error. The same design also lacks required-field validation for retained raw confidence/word data. Legitimate no-speech output must remain distinguishable from missing transcript data.

**Executed reproduction using scratch-only fake-ASR fixtures:** generated a valid transcript, removed its `segments` key while preserving all metadata, and removed the unreviewed JSON to simulate resuming before draft creation. The second run printed `resuming exact metadata`, returned `cue_count: 0`, and wrote an empty draft SRT. Total fake-model transcribe calls remained 1. This is not actual audio/transcription evidence. With a differing existing reviewed JSON the later review conflict prevents draft replacement, but it does not make the raw-cache acceptance correct.

**Minimal remedy:** validate required raw fields/types/schema and retained segment/word metadata before accepting a resume. Require an explicit `segments` list (including an intentional empty list for actual no-speech ASR), and fail with a reconciliation message when required data is absent. Do not silently reinterpret malformed raw data as no speech or overwrite it automatically. Add a malformed-cache regression alongside exact-metadata resume tests.

### 4. P2 — Public SRT validation accepts text that injects additional SRT blocks

**Location:** `scripts/aomimama_caption_core.py:83-84` and `scripts/aomimama_caption_core.py:163-175`.

`validate` checks only that cue text is nonblank. `render_srt`, advertised as rendering validated cues, interpolates text verbatim. Embedded blank lines and timestamp/index lines create additional parsed cues which were never checked for sorting, overlap, duration, or count. This is an exported utility issue: the current `build_cues` path normalizes whitespace, so normal helper-generated drafts do not exercise it, but manually reviewed or direct API cue input does.

**Executed reproduction:** supplied one cue `[0, 1]` with text `hello\n\n2\n00:00:02,000 --> 00:00:03,000\nother`. Validation returned `True`; rendering produced two syntactically separate SRT blocks despite receiving only one cue.

**Minimal remedy:** enforce the one-nonempty-line cue-text contract in validation (reject CR/LF and embedded block separators), or explicitly define and safely serialize a multiline contract. For this run, rejecting multiline text is the smaller fix. Add a renderer regression checking parsed cue count and text, not merely timestamp arithmetic.

## Verified strengths / policy compliance

- No three-word or 1.5-second hard cap; 36 glyphs / four seconds are documented draft heuristics, and indivisible long tokens/protected phrases can exceed them with flags. A targeted long Latin-token probe preserved the entire five-second token and emitted heuristic-exceeded flags rather than cutting it.
- No lexical confidence deletion, repeat deduplication, foreign-script stripping, proper-name substitution, or truncation to fit a hard duration cap. Low confidence and suspect scripts are flagged.
- Fragment/segment lexical disagreement fails explicitly instead of choosing a source and losing negation/name text. Whitespace normalization is intentional, but its timing consequences are not safe in finding 1.
- Known protected names are kept indivisible; unknown names and semantic phrase coherence still require listening/QC. The helper CLI does not provide a protected-name option; do not interpret automatic drafts as name-verified captions.
- Raw serialization retains segment confidence and fragment probability/timing. Metadata includes WAV hash, timeline identity, inference settings and faster-whisper version. Superseded raw bytes are archived before replacement.
- Existing differing reviewed JSON is not overwritten; all generated review artifacts are explicitly unapproved and SRT paths are `.draft.srt`, not final paths. A conflicting reviewed file is checked after possible raw re-decode/replacement, so an error can leave a newly archived/replaced raw file; it is not a wholly side-effect-free preflight.
- Helpers contain no Resolve mutation, approval/import logic, shell execution, hardcoded credentials, unsafe deserialization or model-download fallback.
- Windows CUDA DLL registration is before the real faster-whisper import/inference and retains handles; real native/model readiness remains outside this review.
- Completed-cue millisecond timing is checked for positive duration, sorted non-overlap and timeline bounds. Those checks do not catch the internal timing losses above.

## Verification and limitations

Did not rerun the already-green 17-test suite. Ran only targeted executable probes for the concrete timing, malformed-resume and SRT-text issues, using the existing `.venv-aomimama` interpreter and actual caption tokenizer/core. Probes used `-B` and temporary scratch-only fixture files cleaned on exit; no source/tests, production audio/transcripts/reviews/SRTs, Resolve state, commits, or children were changed. Read-only git status showed untracked `scripts/` and `tests/` at the stated baseline.

Only durable artifact created by this review: `C:/Users/warit/Desktop/agent-create-subtitle/runs/aomimama-2026-09-p1/helper-review.md`.

No tooling blocker was encountered. The report deliberately does not claim ASR accuracy, semantic Thai phrase quality, readability against the viewer, or real CUDA inference. Those require parent-owned real evidence after the findings are addressed or explicitly reconciled.
