"""Tests for the Resolve subtitle import helper. No Resolve connection needed."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import import_subtitles_resolve as imp  # noqa: E402

MAIN_RUN = Path('C:/Users/warit/Desktop/agent-create-subtitle/runs/aomimama-2026-09-p1')


def test_parse_srt_reads_every_cue():
    rows = json.loads((MAIN_RUN / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    checked = 0
    for row in rows:
        srt = MAIN_RUN / 'srt' / f"{row['id']}.draft.srt"
        cues = imp.parse_srt(srt)
        reviewed = json.loads(
            (MAIN_RUN / 'reviewed' / f"{row['id']}.gemini.json").read_text(encoding='utf-8'))
        assert len(cues) == len(reviewed['cues']), f"{row['id']} cue count differs"
        checked += 1
    assert checked == 49


def test_parse_srt_times_match_reviewed_cues():
    rows = json.loads((MAIN_RUN / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    row = rows[0]
    cues = imp.parse_srt(MAIN_RUN / 'srt' / f"{row['id']}.draft.srt")
    reviewed = json.loads(
        (MAIN_RUN / 'reviewed' / f"{row['id']}.gemini.json").read_text(encoding='utf-8'))
    for got, want in zip(cues, reviewed['cues']):
        assert abs(got['start'] - want['start']) < 0.002, (got, want)
        assert got['text'] == want['text']


def test_parse_srt_rejects_a_file_that_does_not_exist(tmp_path):
    with pytest.raises(FileNotFoundError):
        imp.parse_srt(tmp_path / 'nope.srt')


def test_plan_import_flags_timelines_that_already_have_a_track():
    rows = json.loads((MAIN_RUN / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    live = {r['id']: 0 for r in rows}
    live[rows[0]['id']] = 1                      # pretend one already imported
    plan = imp.plan_import(rows, live, replace=False)
    assert plan[0]['action'] == 'skip'
    assert all(p['action'] == 'import' for p in plan[1:])
    assert len(plan) == 49


def test_plan_import_with_replace_imports_everything():
    rows = json.loads((MAIN_RUN / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    live = {r['id']: 2 for r in rows}
    plan = imp.plan_import(rows, live, replace=True)
    assert all(p['action'] == 'replace' for p in plan)


def test_srt_cues_never_exceed_timeline_duration():
    rows = json.loads((MAIN_RUN / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    for row in rows:
        cues = imp.parse_srt(MAIN_RUN / 'srt' / f"{row['id']}.draft.srt")
        duration = (row['end'] - row['start']) / row['fps']
        assert cues[-1]['end'] <= duration + 0.05, row['id']


def test_srt_time_parses_milliseconds():
    assert imp.srt_time('00:00:10,500') == 10.5
    assert imp.srt_time('01:02:03,250') == 3723.25
