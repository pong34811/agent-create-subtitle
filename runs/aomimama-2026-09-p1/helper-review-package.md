# Task review package: Aomi phrase caption helper

Source baseline: git HEAD 2ebc3e5 in C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree. No tracked-file changes, commits, or pushes. All code is new untracked additions; review each complete file as an added-file diff.

Added source:
- scripts/aomimama_caption_core.py
- scripts/aomimama_asr.py
Added tests:
- tests/test_aomimama_captions.py
- tests/test_aomimama_asr.py

Read complete files from the absolute worktree root above. Report: C:/Users/warit/Desktop/agent-create-subtitle/runs/aomimama-2026-09-p1/implementation-report.md.

Binding spec: confirmed user policy in .hermes/plans/2026-10-06_100141-aomimama-all-timeline-subtitles.md (original repo); all short-cue draft code in that document superseded by user confirmation. Natural phrase captions; preserve all spoken words, meaningful repeats, negation and names; 4–5 word coherent phrases may stay >1.5s; split long phrases naturally, no mandatory 3-word or 1.5s cap; no unsafe hidden data loss/confidence stripping. 36 glyph/4 sec are soft draft heuristics requiring viewer QC, not approved styling measurements. Raw ASR must preserve confidence/words; reviewed files not overwritten; drafts unapproved; no Resolve mutation in helpers. Windows CUDA registration before inference if used. SRT timing positive, sorted non-overlap and within timeline duration.

Parent independently reran full suite: 17 tests OK in 1.289 sec; tests use a fake ASR model and are not actual transcription evidence. Do not repeat same tests unless investigating a concrete suspected bug. Real model inference pilot is parent-owned separately.

Return both spec compliance and code quality verdicts, graded concrete findings with file:line and minimal suggested remedy. Inspect actual preservation around whitespace, long token splitting, rounding/repair, raw metadata/resume and reviewed-artifact protection. Do not change source or access Resolve. Write review report to run-root/helper-review.md.
