---
name: resolve-mitr-subtitle-presets
description: "Apply Mitr subtitle presets to 16:9 and 9:16 Resolve tracks."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [DaVinci-Resolve, Subtitles, Fonts, Thai, Presets]
---

# Mitr Subtitle Presets for Horizontal and Vertical Timelines

Loads the user's saved Subtitle *track* presets (Inspector > Load Preset) onto
DaVinci Resolve subtitle tracks by script, picking the Mitr preset by timeline
orientation: landscape 16:9 vs portrait 9:16 Shorts. It does NOT create cues,
retime captions, or invent styles. It only copies an existing preset. Uses the
stdlib plus Resolve's own scripting bridge. Resolve has no preset API, so the
write goes into the disk-database `Project.db` while the project is closed.

## When to Use

- "load preset Mitr Font ให้ทุก timeline", "ใส่ฟอนต์ Mitr ให้ซับ"
- "จัดการ font mitr แนวนอน / แนวตั้ง", "ซับ shorts ใช้ Mitr-short-001"
- Batch-applying one subtitle style across many timelines without clicking
  Inspector > Load Preset per track.

## Prerequisites

- Windows, Resolve Studio running (verified on 21.1.0.17), project open, on a
  **Disk** database (`pm.GetCurrentDatabase()['DbType'] == 'Disk'`).
- Python 3.10+ (`python`). Python 3.14 `compression.zstd` (or `pip install
  zstandard`) is optional and only used for the `--list` font summary.
- The preset must already be saved in Resolve (Inspector > Save Track as Preset).
- Scripting paths used: `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting`
  and `C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll`.
- Explicit user approval for `--apply` (it closes/reopens the project and
  writes SQLite). A request like "load preset X" for named timelines counts.

## How to Run

Invoke `scripts/load_subtitle_preset.py` (in this skill's dir; repo copy at
`scripts/load_subtitle_preset.py` of agent-edite-davinci_resolve) through the
`terminal` tool. Always dry-run first, read the plan, then re-run with `--apply`.

## Quick Reference

Preset mapping in the user's library (verified on project KT404_2026-09-29:
30 tracks of 1920x1080 used Mitr Font, 30 tracks of 1080x1920 `_9x16` used
Mitr-short-001):

| Orientation | Raster | Preset | Font in preset |
|---|---|---|---|
| horizontal (แนวนอน) | 1920x1080 | `Mitr Font` | Mitr SemiBold, default position |
| vertical (แนวตั้ง) | 1080x1920 | `Mitr-short-001` | Mitr Bold + custom position |
| (unused/basic) | any | `mitr`, `mitr-short` | Mitr Regular, identical bytes |

```
python load_subtitle_preset.py --list
python load_subtitle_preset.py --preset "Mitr Font" --orientation horizontal
python load_subtitle_preset.py --preset "Mitr-short-001" --orientation vertical
python load_subtitle_preset.py --preset "Mitr Font" --all-timelines
python load_subtitle_preset.py --preset "Mitr Font" --timeline "TL name" --timeline "TL 2"
... add --apply --backup-dir "C:/Users/<you>/Documents/davinci-resolve-mcp-analysis/subtitle-preset-backups"
```

Other flags: `--user` (default guest), `--project-db`, `--user-db` overrides.
No target flag = current timeline only.

## Procedure

1. `--list` and confirm the exact preset name. The menu shows `Mitr Font` with a
   space; users often type `Mitr-Font`. Map to the real name, don't guess others.
2. Dry run per orientation. Output lists every subtitle track and
   `already_matches`, then `N of M subtitle track(s) would change.`
   A mixed project (16:9 + `_9x16` copies) needs **two** runs: horizontal with
   `Mitr Font`, vertical with `Mitr-short-001`. Never `--all-timelines` one
   preset over a mixed project.
3. Re-run with `--apply` and a durable `--backup-dir` (the default under
   `TMPDIR` is pruned after 24h). The script: SaveProject -> ExportProject `.drp`
   -> CloseProject -> sqlite snapshot of `Project.db` -> one transaction on the
   exact `Sm2TiTrack` rows (Type=2), readback -> LoadProject -> restore active
   timeline, playhead, page -> SaveProject -> verify blobs + cue counts.
4. Report `verified_tracks`, `changed_tracks`, cue counts, backup dir; ask the
   user to eyeball one horizontal and one vertical timeline in the viewer.

How it works (for debugging): presets live in
`<library>\Resolve Projects\Users\guest\User.db`, `SM_User.FieldsBlob`, key
`SubtitlePresetsBA`. A styled track stores the identical bytes under
`EffectFiltersBA` in `Sm2TiTrack.FieldsBlob`. Library path comes from
`%APPDATA%\Blackmagic Design\DaVinci Resolve\Preferences\dblist.conf` (drive
colon stripped, e.g. `G\My Drive\...`). Orientation comes from
`Timeline.GetSetting("timelineResolutionWidth"/"timelineResolutionHeight")`.

## Pitfalls

- `No target timeline has a subtitle track (orientation=vertical)` is normal
  for a project with only 16:9 timelines. It's not a bug.
- `DB has N subtitle tracks but Resolve reports M`: unsaved new tracks. Save in
  Resolve and rerun.
- A track added by SRT import has no `EffectFiltersBA` (unstyled stub). The
  script appends the key, which reproduces Resolve's own bytes exactly.
- Re-importing an SRT (DeleteTrack/AddTrack) resets the track style. Reapply
  the preset afterwards.
- Projects sit in nested folders (`Projects\Tygarina\2026-09-30\<name>`). The
  script globs recursively and requires the DB to contain the target timeline IDs
  (`GetUniqueId()` == `Sm2Timeline_id`).
- Never write while the project is open; the script refuses if Save/Export/Close
  fails. Don't hand-edit `pointSize` to change Inspector Size (8.14286 is the
  descriptor, not the UI size). Save a new preset in the UI instead.
- Running with a preset that already matches is a no-op (`Nothing to do`).

## Verification

Re-run the same dry run after `--apply`. It must print
`0 of N subtitle track(s) would change.` (every track `already_matches: true`).
