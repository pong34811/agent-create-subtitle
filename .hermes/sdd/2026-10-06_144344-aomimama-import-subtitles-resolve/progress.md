# SDD ledger — plan: .hermes/plans/2026-10-06_144344-aomimama-import-subtitles-resolve.md

Executor: inline (superpowers:executing-plans)
Spec: none reachable — rulings are provisional. Binding authority = plan file.
Mode: Rulings for the 3 open questions taken as the recommended defaults:
  - Q1 (14 flagged cues): import all, record flags in results
  - Q2 (9 gemini-2.5-flash files): use current files, re-run later when quota resets
  - Q3 ([ฟังไม่ชัด] markers): keep inline as the user originally specified
  These match the plan's recommended option; no deviation.

Pre-flight: Tasks 1-2 (helper + tests) produce parse_srt/plan_import; Tasks 3-6 consume
them via CLI only. No shared mutable state. Task 7 (preset) touches the same subtitle
tracks Task 5 creates — runs strictly after, and re-applies style the import resets.
No conflicts found.

Task 1+2: complete (7 passed — tests/test_import_subtitles.py, RED ModuleNotFoundError -> GREEN)

Task 3: complete (dry run 49 timelines, 0 OVERRUN, 0 missing SRT)
Task 4+5: complete (49/49 verified, 0 FAIL; 918 cues placed in Resolve)
Task 6: complete (independent readback from Resolve: 49/49 exact cue match)

Ruling: the target timeline must be made CURRENT (SetCurrentTimeline) before
AddTrack/AppendToTimeline — both act on the active timeline, not the object they
were called through. First --apply attempt failed 0/3 ("ImportMedia returned
nothing" / "AppendToTimeline placed nothing") because the active timeline was a
different one. Cost if wrong: none — readback now proves 49/49.
Ruling: connect() must run under `py -3.12`, not the pythainlp venv (3.11 cannot
load fusionscript.dll). Dry run works in either. Cost if wrong: --apply fails loudly.
Ruling: connect() now refuses to write when the open project is not the target
(guards against the Untitled Project state seen during probing). Cost if wrong: none.
Ruling: scriptapp() intermittently returns None; retry up to 10x with 5s sleep.
Cost if wrong: none — it succeeded on retry every time.

Incident (contained): an early probe called AddTrack on the WRONG timeline and left
one unstyled subtitle track + one stale pool clip. Both were on the unsaved
"Untitled Project"; the probe clip was deleted from the pool and a fresh readback
confirms all 49 target timelines had 0 subtitle tracks before the real run.
