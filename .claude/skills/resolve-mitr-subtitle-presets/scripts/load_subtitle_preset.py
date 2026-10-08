"""Load a saved Subtitle *track* preset (Inspector > Load Preset) by script.

Resolve 21.1 has no scripting call for subtitle-track presets.  This tool
reproduces the GUI's "Load Preset" at the database level, verified on build
21.1.0.17:

* User presets live in ``<library>/Resolve Projects/Users/<user>/User.db``,
  table ``SM_User.FieldsBlob`` -> key ``SubtitlePresetsBA`` (QMap name->bytes).
* A styled subtitle track stores the *identical bytes* under key
  ``EffectFiltersBA`` in ``Sm2TiTrack.FieldsBlob`` (``Type = 2``) of the
  project's ``Project.db``.  Loading a preset = copying those bytes.

Default mode is a read-only dry run.  ``--apply`` writes, following the
project's database rules: save, export a ``.drp`` backup, close the project,
snapshot ``Project.db``, one transaction on the exact track rows, readback,
reopen, restore timeline/playhead/page, save, then verify blobs and cue
counts again.

Usage::

    python scripts/load_subtitle_preset.py --list
    python scripts/load_subtitle_preset.py --preset "Mitr-short-001"            # dry run, current timeline
    python scripts/load_subtitle_preset.py --preset "Mitr-short-001" --apply
    python scripts/load_subtitle_preset.py --preset mitr --timeline "TL A" --timeline "TL B" --apply
    python scripts/load_subtitle_preset.py --preset mitr --all-timelines --apply
    python scripts/load_subtitle_preset.py --preset "Mitr Font" --orientation horizontal --apply
    python scripts/load_subtitle_preset.py --preset "Mitr-short-001" --orientation vertical --apply
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import shutil
import sqlite3
import struct
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SCRIPT_API = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
SCRIPT_LIB = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
PREFS = Path(os.path.expandvars(r"%APPDATA%\Blackmagic Design\DaVinci Resolve\Preferences"))
STYLE_KEY = "EffectFiltersBA"
PRESETS_KEY = "SubtitlePresetsBA"
MUTATION_GAP_S = 1.2
SUBTITLE_TRACK_TYPE = 2


# --------------------------------------------------------------------------
# Qt QDataStream (big-endian, Qt5) helpers for the keyed blobs Resolve stores.
# --------------------------------------------------------------------------
class BlobFormatError(ValueError):
    pass


def _u32(buf: bytes, i: int) -> tuple[int, int]:
    if i + 4 > len(buf):
        raise BlobFormatError(f"truncated uint32 at {i}")
    return struct.unpack(">I", buf[i:i + 4])[0], i + 4


def _read_qstring(buf: bytes, i: int) -> tuple[str | None, int]:
    n, i = _u32(buf, i)
    if n == 0xFFFFFFFF:
        return None, i
    if i + n > len(buf):
        raise BlobFormatError(f"truncated QString at {i}")
    return buf[i:i + n].decode("utf-16-be"), i + n


def _read_qbytearray(buf: bytes, i: int) -> tuple[bytes | None, int]:
    n, i = _u32(buf, i)
    if n == 0xFFFFFFFF:
        return None, i
    if i + n > len(buf):
        raise BlobFormatError(f"truncated QByteArray at {i}")
    return buf[i:i + n], i + n


def _qstring(s: str) -> bytes:
    raw = s.encode("utf-16-be")
    return struct.pack(">I", len(raw)) + raw


def _qbytearray(b: bytes) -> bytes:
    return struct.pack(">I", len(b)) + b


# Fixed-width QVariant payloads seen in these blobs (type id -> byte width).
_FIXED = {1: 1, 2: 4, 3: 4, 4: 8, 5: 8, 6: 8}


def parse_fields_blob(blob: bytes) -> tuple[bytes, list[tuple[str, int, bytes]]]:
    """Parse ``<u32 version><u32 count>{QString key, QVariant value}*``.

    Returns (version_header, [(key, qvariant_type, raw_value_bytes)]) where the
    raw bytes include the null flag, so unknown-but-sized values round-trip.
    """
    if not blob or len(blob) < 8:
        raise BlobFormatError("blob too short")
    header = blob[:4]
    count, i = _u32(blob, 4)
    entries = []
    for _ in range(count):
        key, i = _read_qstring(blob, i)
        vtype, i = _u32(blob, i)
        start = i
        i += 1  # QVariant null flag
        if vtype in _FIXED:
            i += _FIXED[vtype]
        elif vtype in (10, 12):  # QString / QByteArray share the u32-length shape
            n, i = _u32(blob, i)
            if n != 0xFFFFFFFF:
                i += n
        else:
            raise BlobFormatError(f"unsupported QVariant type {vtype} for key {key!r}")
        if i > len(blob):
            raise BlobFormatError(f"value for {key!r} overruns blob")
        entries.append((key, vtype, blob[start:i]))
    if i != len(blob):
        raise BlobFormatError(f"{len(blob) - i} trailing bytes after {count} entries")
    return header, entries


def build_fields_blob(header: bytes, entries: list[tuple[str, int, bytes]]) -> bytes:
    out = [header, struct.pack(">I", len(entries))]
    for key, vtype, raw in entries:
        out += [_qstring(key), struct.pack(">I", vtype), raw]
    return b"".join(out)


def get_bytearray(blob: bytes, key: str) -> bytes | None:
    _, entries = parse_fields_blob(blob)
    for k, vtype, raw in entries:
        if k == key:
            if vtype != 12:
                raise BlobFormatError(f"{key} is QVariant type {vtype}, expected QByteArray")
            value, _ = _read_qbytearray(raw, 1)
            return value
    return None


def set_bytearray(blob: bytes, key: str, value: bytes) -> bytes:
    """Return blob with ``key`` replaced (or appended) as a QByteArray; others untouched."""
    header, entries = parse_fields_blob(blob)
    raw = b"\x00" + _qbytearray(value)
    for n, (k, _vtype, _raw) in enumerate(entries):
        if k == key:
            entries[n] = (k, 12, raw)
            break
    else:
        entries.append((key, 12, raw))
    return build_fields_blob(header, entries)


def parse_preset_map(data: bytes) -> dict[str, bytes]:
    """``SubtitlePresetsBA`` = ``<u32 version><u32 count>{QString name, QByteArray style}*``."""
    count, i = _u32(data, 4)
    presets: dict[str, bytes] = {}
    for _ in range(count):
        name, i = _read_qstring(data, i)
        value, i = _read_qbytearray(data, i)
        presets[name or ""] = value or b""
    if i != len(data):
        raise BlobFormatError("trailing bytes in SubtitlePresetsBA")
    return presets


def describe_style(style: bytes) -> str:
    """Best-effort human summary (font descriptor) of a style value; never required."""
    try:
        from compression import zstd  # Python 3.14+
    except ImportError:
        try:
            import zstandard

            def _dec(b):
                return zstandard.ZstdDecompressor().decompress(b, max_output_size=1 << 20)
        except ImportError:
            return f"{len(style)} bytes"
    else:
        _dec = zstd.decompress
    k = style.find(b"\x28\xb5\x2f\xfd")
    if k < 0:
        return f"{len(style)} bytes (uncompressed)"
    try:
        text = _dec(style[k:])
    except Exception:
        return f"{len(style)} bytes"
    import re
    fonts = re.findall(rb"([A-Za-z][\w .-]+),\d+(?:\.\d+)?,-?\d+,\d+,(\d+),[^J]*?([A-Za-z ]+)J", text)
    if fonts:
        family, weight, styl = fonts[0]
        return f"font={family.decode()} {styl.decode().strip()} (weight {weight.decode()}), {len(style)} bytes"
    return f"{len(style)} bytes"


# --------------------------------------------------------------------------
# Locating the active disk database, User.db and Project.db
# --------------------------------------------------------------------------
def library_roots(prefs: Path = PREFS) -> dict[str, Path]:
    """Map disk-database names in ``dblist.conf`` to library folders."""
    roots = {}
    text = (prefs / "dblist.conf").read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        parts = line.strip().split(":")
        if len(parts) < 2 or not parts[0] or not parts[-1].upper().startswith("DISK"):
            continue
        raw = parts[1]
        # Stored as "G\My Drive\..." (drive colon removed) on Windows.
        if len(raw) >= 2 and raw[1] == "\\" and raw[0].isalpha():
            raw = raw[0] + ":" + raw[1:]
        roots[parts[0]] = Path(raw)
    return roots


def find_user_db(root: Path, user: str) -> Path:
    path = root / "Resolve Projects" / "Users" / user / "User.db"
    if not path.is_file():
        raise SystemExit(f"User.db not found: {path}")
    return path


def find_project_db(root: Path, user: str, project: str, timeline_ids: list[str]) -> Path:
    base = root / "Resolve Projects" / "Users" / user / "Projects"
    pattern = str(base / "**" / glob.escape(project) / "Project.db")
    candidates = [Path(p) for p in glob.glob(pattern, recursive=True)]
    owning = [p for p in candidates if _db_has_timelines(p, timeline_ids)]
    if len(owning) != 1:
        raise SystemExit(
            f"Expected exactly one Project.db for {project!r} containing the target timelines; "
            f"found {[str(p) for p in owning] or [str(p) for p in candidates]}. Pass --project-db."
        )
    return owning[0]


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def _db_has_timelines(path: Path, ids: list[str]) -> bool:
    con = _ro(path)
    try:
        q = ",".join("?" for _ in ids)
        n = con.execute(f"SELECT COUNT(*) FROM Sm2Timeline WHERE Sm2Timeline_id IN ({q})", ids).fetchone()[0]
        return n == len(set(ids))
    finally:
        con.close()


def read_presets(user_db: Path) -> dict[str, bytes]:
    con = _ro(user_db)
    try:
        rows = con.execute("SELECT FieldsBlob FROM SM_User WHERE FieldsBlob IS NOT NULL").fetchall()
    finally:
        con.close()
    presets: dict[str, bytes] = {}
    for (blob,) in rows:
        data = get_bytearray(blob, PRESETS_KEY)
        if data:
            presets.update(parse_preset_map(data))
    return presets


TRACK_QUERY = """
SELECT tr.Sm2TiTrack_id, tl.Sm2Timeline_id, tl.Name, tr.FieldsBlob
FROM Sm2TiTrack tr
JOIN Sm2Sequence sq ON tr.Sequence = sq.Sm2Sequence_id
JOIN Sm2Timeline tl ON sq.Sm2Timeline_id = tl.Sm2Timeline_id
WHERE tr.Type = ? AND tl.Sm2Timeline_id IN ({q})
ORDER BY tl.Name, tr.rowid
"""


def subtitle_tracks(con: sqlite3.Connection, timeline_ids: list[str]) -> list[tuple]:
    q = ",".join("?" for _ in timeline_ids)
    return con.execute(TRACK_QUERY.format(q=q), [SUBTITLE_TRACK_TYPE, *timeline_ids]).fetchall()


def plan_updates(rows: list[tuple], style: bytes) -> list[dict]:
    plan = []
    for track_id, tl_id, tl_name, blob in rows:
        if not blob:
            raise SystemExit(f"Subtitle track {track_id} on {tl_name!r} has an empty FieldsBlob; refusing.")
        current = get_bytearray(blob, STYLE_KEY)
        new_blob = set_bytearray(blob, STYLE_KEY, style)
        # Everything except the style key must survive byte-for-byte.
        old_rest = [e for e in parse_fields_blob(blob)[1] if e[0] != STYLE_KEY]
        new_rest = [e for e in parse_fields_blob(new_blob)[1] if e[0] != STYLE_KEY]
        assert old_rest == new_rest and get_bytearray(new_blob, STYLE_KEY) == style
        plan.append({"track_id": track_id, "timeline_id": tl_id, "timeline": tl_name,
                     "already_matches": current == style, "new_blob": new_blob})
    return plan


def write_plan(project_db: Path, plan: list[dict], style: bytes) -> None:
    """Single transaction on the exact rows, readback before commit."""
    todo = [p for p in plan if not p["already_matches"]]
    con = sqlite3.connect(project_db, isolation_level=None)
    try:
        con.execute("BEGIN IMMEDIATE")
        for p in todo:
            cur = con.execute("UPDATE Sm2TiTrack SET FieldsBlob=? WHERE Sm2TiTrack_id=? AND Type=?",
                              (p["new_blob"], p["track_id"], SUBTITLE_TRACK_TYPE))
            if cur.rowcount != 1:
                raise RuntimeError(f"expected 1 row for track {p['track_id']}, updated {cur.rowcount}")
        for p in plan:
            (blob,) = con.execute("SELECT FieldsBlob FROM Sm2TiTrack WHERE Sm2TiTrack_id=?",
                                  (p["track_id"],)).fetchone()
            if get_bytearray(blob, STYLE_KEY) != style:
                raise RuntimeError(f"readback mismatch on track {p['track_id']}")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


def verify_db(project_db: Path, timeline_ids: list[str], style: bytes, expected_tracks: int) -> int:
    con = _ro(project_db)
    try:
        rows = subtitle_tracks(con, timeline_ids)
    finally:
        con.close()
    ok = sum(1 for r in rows if r[3] and get_bytearray(r[3], STYLE_KEY) == style)
    if len(rows) != expected_tracks or ok != expected_tracks:
        raise RuntimeError(f"post-verify: {ok}/{len(rows)} tracks match (expected {expected_tracks})")
    return ok


# --------------------------------------------------------------------------
# Resolve bridge
# --------------------------------------------------------------------------
def connect_resolve():
    os.environ.setdefault("RESOLVE_SCRIPT_API", SCRIPT_API)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", SCRIPT_LIB)
    mod = os.path.join(os.environ["RESOLVE_SCRIPT_API"], "Modules")
    if mod not in sys.path:
        sys.path.insert(0, mod)
    lib_dir = os.path.dirname(os.environ["RESOLVE_SCRIPT_LIB"])
    if hasattr(os, "add_dll_directory") and os.path.isdir(lib_dir):
        os.add_dll_directory(lib_dir)
    import DaVinciResolveScript as dvr  # noqa: E402

    resolve = dvr.scriptapp("Resolve")
    if not resolve:
        raise SystemExit("Cannot connect to DaVinci Resolve (is it running with scripting enabled?)")
    return resolve


def timelines_by_id(project) -> dict[str, object]:
    out = {}
    for i in range(1, project.GetTimelineCount() + 1):
        tl = project.GetTimelineByIndex(i)
        out[tl.GetUniqueId()] = tl
    return out


def timeline_orientation(tl) -> str:
    """'vertical' when the timeline raster is portrait (e.g. 1080x1920), else 'horizontal'."""
    w = int(float(tl.GetSetting("timelineResolutionWidth") or 0))
    h = int(float(tl.GetSetting("timelineResolutionHeight") or 0))
    if not w or not h:
        raise SystemExit(f"Cannot read resolution of timeline {tl.GetName()!r}")
    return "vertical" if h > w else "horizontal"


def cue_counts(project, ids: list[str]) -> dict[str, list[int]]:
    tls = timelines_by_id(project)
    return {i: [len(tls[i].GetItemListInTrack("subtitle", t) or [])
                for t in range(1, tls[i].GetTrackCount("subtitle") + 1)] for i in ids}


def wait_page(resolve, page: str, timeout: float = 10.0) -> bool:
    resolve.OpenPage(page)
    end = time.time() + timeout
    while time.time() < end:
        if resolve.GetCurrentPage() == page:
            return True
        time.sleep(0.25)
    return False


# --------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true", help="list subtitle presets and exit")
    ap.add_argument("--preset", help="preset name exactly as shown in Inspector > Load Preset")
    ap.add_argument("--timeline", action="append", default=[], help="timeline name (repeatable); default = current")
    ap.add_argument("--all-timelines", action="store_true")
    ap.add_argument("--orientation", choices=["horizontal", "vertical"],
                    help="only timelines whose resolution is landscape (W>=H) or portrait (H>W); "
                         "implies --all-timelines when no --timeline is given")
    ap.add_argument("--user", default="guest", help="Resolve database user folder (default guest)")
    ap.add_argument("--project-db", type=Path, help="override Project.db path")
    ap.add_argument("--user-db", type=Path, help="override User.db path")
    ap.add_argument("--backup-dir", type=Path, default=Path(os.environ.get("TMPDIR", ".")) / "subtitle_preset_backups")
    ap.add_argument("--apply", action="store_true", help="actually write (default: dry run)")
    args = ap.parse_args(argv)

    resolve = connect_resolve()
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    db = pm.GetCurrentDatabase() or {}
    if str(db.get("DbType", "")).lower() != "disk":
        raise SystemExit(f"Only disk databases are supported (current: {db})")
    root = library_roots().get(db.get("DbName"))
    if root is None and not (args.user_db and args.project_db):
        raise SystemExit(f"Database {db.get('DbName')!r} not found in dblist.conf; pass --user-db/--project-db")

    user_db = args.user_db or find_user_db(root, args.user)
    presets = read_presets(user_db)
    if args.list or not args.preset:
        print(f"User.db: {user_db}")
        for name, style in presets.items():
            print(f"  {name!r}: {describe_style(style)}")
        return 0
    if args.preset not in presets:
        raise SystemExit(f"Preset {args.preset!r} not found. Available: {list(presets)}")
    style = presets[args.preset]

    # Resolve targets by unique ID (== Sm2Timeline_id in Project.db).
    tls = timelines_by_id(project)
    current = project.GetCurrentTimeline()
    if args.all_timelines or (args.orientation and not args.timeline):
        target_ids = list(tls)
    elif args.timeline:
        by_name = {}
        for tid, tl in tls.items():
            by_name.setdefault(tl.GetName(), []).append(tid)
        target_ids = []
        for name in args.timeline:
            ids = by_name.get(name, [])
            if len(ids) != 1:
                raise SystemExit(f"Timeline {name!r}: expected 1 match, found {len(ids)}")
            target_ids += ids
    else:
        if not current:
            raise SystemExit("No current timeline; pass --timeline or --all-timelines")
        target_ids = [current.GetUniqueId()]
    if args.orientation:
        target_ids = [t for t in target_ids if timeline_orientation(tls[t]) == args.orientation]
    target_ids = [t for t in target_ids if tls[t].GetTrackCount("subtitle") > 0]
    if not target_ids:
        raise SystemExit("No target timeline has a subtitle track"
                         + (f" (orientation={args.orientation})" if args.orientation else ""))

    project_name = project.GetName()
    project_db = args.project_db or find_project_db(root, args.user, project_name, target_ids)
    con = _ro(project_db)
    try:
        rows = subtitle_tracks(con, target_ids)
    finally:
        con.close()
    plan = plan_updates(rows, style)
    api_tracks = sum(tls[t].GetTrackCount("subtitle") for t in target_ids)
    if len(plan) != api_tracks:
        raise SystemExit(f"DB has {len(plan)} subtitle tracks but Resolve reports {api_tracks}; "
                         "save the project in Resolve and retry.")

    report = {"project": project_name, "project_db": str(project_db), "user_db": str(user_db),
              "preset": args.preset, "style": describe_style(style),
              "tracks": [{k: v for k, v in p.items() if k != "new_blob"} for p in plan]}
    to_change = sum(not p["already_matches"] for p in plan)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"{to_change} of {len(plan)} subtitle track(s) would change.")
    if not args.apply:
        print("Dry run only. Re-run with --apply to write.")
        return 0
    if to_change == 0:
        print("Nothing to do; all target tracks already use this preset.")
        return 0

    # ---- capture state ---------------------------------------------------
    page = resolve.GetCurrentPage()
    active_id = current.GetUniqueId() if current else None
    playhead = current.GetCurrentTimecode() if current else None
    folder = pm.GetCurrentFolder()
    cues_before = cue_counts(project, target_ids)

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = args.backup_dir / f"{project_name}_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if not pm.SaveProject():
        raise SystemExit("SaveProject failed; nothing written")
    time.sleep(MUTATION_GAP_S)
    drp = backup_dir / f"{project_name}_before_preset.drp"
    if not pm.ExportProject(project_name, str(drp), False) or not drp.is_file() or drp.stat().st_size == 0:
        raise SystemExit(f"DRP backup failed ({drp}); nothing written")
    if not pm.CloseProject(project):
        raise SystemExit("CloseProject failed; nothing written")
    time.sleep(MUTATION_GAP_S)

    reopened = None
    try:
        snapshot = backup_dir / "Project.db.before_preset.sqlite"
        src = sqlite3.connect(project_db)
        dst = sqlite3.connect(snapshot)
        with dst:
            src.backup(dst)
        src.close(); dst.close()
        write_plan(project_db, plan, style)
    finally:
        if folder and pm.GetCurrentFolder() != folder:
            pm.OpenFolder(folder)
        reopened = pm.LoadProject(project_name)
    if not reopened:
        raise SystemExit(f"Wrote DB but could not reopen {project_name!r}. Backups in {backup_dir}")
    time.sleep(MUTATION_GAP_S)

    # ---- restore state, save, verify -------------------------------------
    tls = timelines_by_id(reopened)
    if active_id in tls:
        reopened.SetCurrentTimeline(tls[active_id])
        time.sleep(0.5)
        if playhead:
            reopened.GetCurrentTimeline().SetCurrentTimecode(playhead)
    if page:
        wait_page(resolve, page)
    pm.SaveProject()
    time.sleep(MUTATION_GAP_S)
    cues_after = cue_counts(reopened, target_ids)
    if cues_after != cues_before:
        raise SystemExit(f"Cue counts changed! before={cues_before} after={cues_after}. Backups: {backup_dir}")
    verified = verify_db(project_db, target_ids, style, len(plan))
    restored = reopened.GetCurrentTimeline()
    result = {"verified_tracks": verified, "changed_tracks": to_change, "backup_dir": str(backup_dir),
              "cue_counts": cues_after, "page": resolve.GetCurrentPage(),
              "active_timeline_restored": bool(restored and restored.GetUniqueId() == active_id),
              "playhead": restored.GetCurrentTimecode() if restored else None}
    (backup_dir / "result.json").write_text(json.dumps({**report, **result}, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print("Done. Check the viewer: Inspector should show the preset's font/position on each subtitle track.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
