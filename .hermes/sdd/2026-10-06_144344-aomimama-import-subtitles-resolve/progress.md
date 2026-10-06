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

Task 7: BLOCKED pending user approval — dry run clean (49 of 49 tracks would
change). The preset script closes/reopens the project and writes SQLite, which the
plan marks as requiring explicit approval. Not executed.

Task 7: complete — Mitr Font applied to all 49 subtitle tracks.
  verified_tracks 49, changed_tracks 49 (blobs 111 -> 288 bytes each)
  backup: C:/Users/warit/Documents/resolve-subtitle-preset-backups/aomimama-2026-09-p1_20261006-150958
    (contains aomimama-2026-09-p1_before_preset.drp 1.6MB + Project.db.before_preset.sqlite)
  Idempotency re-check: "0 of 49 subtitle track(s) would change."
  Cues re-verified after the style write: 49/49 timelines, 963 cues, 0 mismatches.

Ruling: a plaintext `EffectFiltersBA` grep is NOT a valid style check — the style
lives inside a zstd-compressed payload. My first check wrongly reported 0/49 styled;
comparing the pre-write snapshot blob to the current blob is the correct check
(49/49 changed, 111->288 bytes). Cost if wrong: none now, but a future run must
compare blobs, not grep.
Ruling: the first --apply hit the 420s foreground cap while Resolve was closed for
the SQLite write, leaving the project closed. Re-running in background completed it.
The project was reopened manually and the abort was verified harmless (49/49 tracks
and 963 cues intact). Cost if wrong: none — verified before retrying.

Final: self-review (no subagent tool dispatched for this run)
Final: minor (deferred): import-results.json omits actual_cues for the 3 skipped
  timelines, so its cue total (918) understates the real 963. Cosmetic — the
  independent readback is the authority.
Final: minor (deferred): timeline 11 holds 1 cue (game noise only, no speech).
