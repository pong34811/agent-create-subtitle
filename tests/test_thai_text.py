"""Tests for deterministic Thai text clean-up and the rule-based checker."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import thai_text as tt  # noqa: E402
import check_thai_text as ck  # noqa: E402


def test_decomposed_sara_am_is_composed():
    assert tt.fix_sara_am('ทํา') == 'ทำ'
    assert tt.fix_sara_am('น้ํา') == 'น้ำ'      # tone mark stays before the vowel
    assert tt.fix_sara_am('คว่ํา ถ้ํา') == 'คว่ำ ถ้ำ'
    assert tt.fix_sara_am('ทำ') == 'ทำ'          # already composed


def test_uncertain_marker_never_survives():
    assert tt.strip_uncertain('[ฟังไม่ชัด]') == ''
    assert tt.strip_uncertain('ไม่ได้ลาภอยู่นะ [ฟังไม่ชัด]') == 'ไม่ได้ลาภอยู่นะ'
    assert tt.clean_cue_text('เหี้ยทีมกาก [ฟังไม่ชัด] ทีมโคตรกาก') == 'เหี้ยทีมกาก ทีมโคตรกาก'


def test_stutter_is_collapsed_but_normal_repeats_are_kept():
    assert tt.collapse_stutter('ฮึมฮึมฮึมฮึมฮึม') == 'ฮึมฮึม'
    assert tt.collapse_stutter('อื้ออื้ออื้ออื้ออื้อ') == 'อื้ออื้อ'
    assert tt.collapse_stutter('เฮ้ยเดี๋ยวนะ') == 'เฮ้ยเดี๋ยวนะ'
    assert tt.collapse_stutter('ไปไปไป') == 'ไปไปไป'   # three is natural speech
    assert tt.collapse_stutter('ฮ่าๆๆๆๆ') == 'ฮ่าๆๆๆๆ'


def test_checker_flags_errors_and_passes_clean_text():
    codes = lambda text, d=1.5: {c for _, c, _ in ck.check_text(text, d)}  # noqa: E731
    assert codes('เฮ้ยเจอแล้ว') == set()
    assert 'foreign_script' in codes('มันมี를')
    assert 'doubled_tone_mark' in codes('ไม่่ได้')
    assert 'starts_with_combining_mark' in codes('็นไร')
    assert 'stretched_character' in codes('ย้าาาาา')
    assert 'reading_speed' in codes('ก' * 60, 1.0)
    assert 'empty_text' in codes('  ')
    assert 'uncertain_marker' in codes('[ฟังไม่ชัด]')


def test_overlapping_segments_never_become_a_wall_of_text():
    """Regression: 10 overlapping segments were merged into one 290-glyph cue."""
    pytest = __import__('pytest')
    pytest.importorskip('pythainlp')
    import build_gemini_cues as b
    segments = [{'start': 1.0 + i * 0.01, 'end': 1.6 + i * 0.01, 'uncertain': False,
                 'text': 'ไม่ได้ใช้เลยนะพี่ไปกดเล่นเลย'} for i in range(10)]
    transcript = {'gemini': {'segments': segments}}
    cues, _ = b.build(transcript, 30.0)
    assert max(b.glyphs(c['text']) for c in cues) <= b.MAX_GLYPHS * 1.5
    assert all(a['end'] <= c['start'] + 1e-6 for a, c in zip(cues, cues[1:]))
    assert all(c['end'] > c['start'] and c['end'] <= 30.0 for c in cues)


def test_marker_only_segment_makes_no_cue():
    pytest = __import__('pytest')
    pytest.importorskip('pythainlp')
    import build_gemini_cues as b
    cues, _ = b.build({'gemini': {'segments': [
        {'start': 1.0, 'end': 2.0, 'text': '[ฟังไม่ชัด]', 'uncertain': True},
        {'start': 3.0, 'end': 4.0, 'text': 'ทํา', 'uncertain': False}]}}, 10.0)
    assert [c['text'] for c in cues] == ['ทำ']
