import importlib
import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


def raw(text: str, start: float = 0, end: float = 3) -> dict:
    """Recognizer-shaped fixture; deliberately low confidence but real text."""
    return {'segments': [{'start': start, 'end': end, 'text': text,
                          'words': [{'word': text, 'start': start, 'end': end,
                                     'probability': 0.001}],
                          'avg_logprob': -9, 'no_speech_prob': 0.99}]}


class CaptionTests(unittest.TestCase):
    def test_timeline_edge_rounding_clamps_only_half_millisecond(self):
        core = importlib.import_module('aomimama_caption_core')
        duration = 6508 / 60
        for end in [duration, duration + .0004]:
            cues = core.build_cues(raw('Alice not not gone', 108, end), duration)
            self.assertEqual(cues[0]['end'], duration)
            core.validate(cues, duration)
            self.assertIn('00:01:48,467', core.render_srt(cues))
        for start, end in [(108, duration + .0006), (-.001, 1), (2, 1)]:
            with self.assertRaises(ValueError):
                core.build_cues(raw('Alice not not gone', start, end), duration)
        with self.assertRaises(ValueError):
            core.validate([dict(start=108, end=duration+.0004, text='Alice')], duration)

    def test_timeline4_derived_zero_duration_tail_reconciles_without_text_loss(self):
        # Anonymized segment-6 timing shape, shifted to segment zero.
        # Positive Thai base, distant combining mark, then zero-duration tail.
        core = importlib.import_module('aomimama_caption_core')
        words = [('ก', 0, .2), ('่', 5.59, 5.59), ('า', 5.59, 5.59),
                 ('ข', 5.59, 5.59), ('Ab', 5.59, 5.59), (' xyz', 5.59, 5.59)]
        text = ''.join(w for w, _, _ in words)
        data = raw(text, end=5.59)
        data['segments'][0]['words'] = [dict(word=w, start=s, end=e) for w,s,e in words]
        with self.assertLogs('aomimama_caption_core', level='WARNING') as logs:
            cues = core.build_cues(data, 6)
        self.assertEqual(''.join(c['text'] for c in cues), text)
        self.assertEqual([(c['start'], c['end']) for c in cues], [(0, 5.59)])
        self.assertIn('zero_duration_fragment_reconciliation', cues[0]['flags'])
        self.assertIn('reconciliation', ' '.join(logs.output))
        core.validate(cues, 6)
        with self.assertRaises(ValueError):
            core.build_cues(raw('not Alice', 1, 1), 6)

    def test_multiline_srt_text_rejected_by_public_apis(self):
        core = importlib.import_module('aomimama_caption_core')
        for text in ['hello\n\n2\n00:00:02,000 --> 00:00:03,000\nother', 'Alice\rnot', 'Alice\nnot']:
            cues = [dict(start=0, end=1, text=text)]
            for action in [lambda: core.validate(cues, 3), lambda: core.render_srt(cues)]:
                with self.assertRaisesRegex(ValueError, 'single.line'):
                    action()
        srt = core.render_srt([dict(start=0, end=1, text='Alice not not gone')])
        self.assertEqual(len(srt.strip().split('\n\n')), 1)
        self.assertEqual(srt.splitlines()[2], 'Alice not not gone')

    def test_nested_fragment_extents_are_preserved_and_flagged(self):
        core = importlib.import_module('aomimama_caption_core')
        for text, words in [('hello world', [('hello', 0, 3), (' world', 1, 2)]),
                            ('Alice!', [('Alice', 0, 3), ('!', 1, 2)])]:
            data = raw(text)
            data['segments'][0]['words'] = [dict(word=w, start=s, end=e) for w,s,e in words]
            cues = core.build_cues(data, 5)
            self.assertEqual(cues[0]['end'], 3)
            self.assertEqual(cues[0]['text'], text)
            self.assertIn('fragment_overlap_review', cues[0]['flags'])

    def test_whitespace_keeps_negation_and_multiword_protected_name_indivisible(self):
        core = importlib.import_module('aomimama_caption_core')
        for text, names in [('not gone', []), ('Copper Golem', ['Copper Golem'])]:
            cues = core.build_cues(raw(text), 4, max_glyphs=3, protected_terms=names)
            self.assertEqual([c['text'] for c in cues], [text])

    def test_segment_fallback_excludes_whitespace_from_interpolation(self):
        core = importlib.import_module('aomimama_caption_core')
        data = raw('  Alice  ', 1, 2)
        data['segments'][0]['words'] = []
        cues = core.build_cues(data, 3)
        self.assertEqual(cues[0]['text'], 'Alice')
        self.assertEqual((cues[0]['start'], cues[0]['end']), (1, 2))

    def test_whitespace_does_not_occupy_speech_timing(self):
        core = importlib.import_module('aomimama_caption_core')
        for words in [ [('hello', 0, 1), (' world', 3, 4)],
                       [('hello', 0, 1), (' ', 1, 3), ('world', 3, 4)],
                       [('ไทย', 0, 1), (' Alice', 3, 4)]]:
            text = ''.join(w[0] for w in words)
            data = raw(text, end=4)
            data['segments'][0]['words'] = [dict(word=w, start=s, end=e) for w,s,e in words]
            cues = core.build_cues(data, 5)
            self.assertEqual([(c['start'], c['end']) for c in cues], [(0, 1), (3, 4)])
            self.assertEqual(' '.join(c['text'] for c in cues), text)

    def test_coherent_five_words_longer_than_one_point_five_seconds(self):
        self.assertIsNotNone(importlib.util.find_spec('aomimama_caption_core'),
                             'phrase core is missing')
        core = importlib.import_module('aomimama_caption_core')
        cues = core.build_cues(raw('we must not lose Alice', end=3), 5)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0]['text'], 'we must not lose Alice')
        self.assertGreater(cues[0]['end'] - cues[0]['start'], 1.5)
        core.validate(cues, 5)

    def test_long_thai_splits_without_severing_combining_marks_negation_or_name(self):
        core = importlib.import_module('aomimama_caption_core')
        text = 'วันนี้พวกเราจะเดินทางไปด้วยกันแต่ไม่ทิ้งออมิมามะเพราะทุกคนต้องกลับบ้านอย่างปลอดภัย'
        data = raw(text, end=8)
        data['protected_terms'] = ['ออมิมามะ']
        import inspect
        self.assertIn('max_glyphs', inspect.signature(core.build_cues).parameters,
                      'configurable phrase splitting is missing')
        cues = core.build_cues(data, 10, max_glyphs=22)
        self.assertGreater(len(cues), 1)
        self.assertEqual(''.join(c['text'] for c in cues), text)
        self.assertTrue(any('ออมิมามะ' in c['text'] for c in cues))
        self.assertFalse(any(c['text'].endswith('ไม่') for c in cues))
        import unicodedata
        self.assertFalse(any(unicodedata.category(c['text'][0]).startswith('M') for c in cues))
        core.validate(cues, 10)

    def test_fragment_preservation_repetition_latin_punctuation_and_foreign_flags(self):
        core = importlib.import_module('aomimama_caption_core')
        text = 'เลือดน้อย ๆ ระวังระวัง Alice, go! มันมี를'
        data = raw(text, end=3)
        data['segments'][0]['words'] = [
            {'word': ch, 'start': i * 0.05, 'end': (i+1)*0.05, 'probability': 0.001}
            for i, ch in enumerate(text)]
        cues = core.build_cues(data, 5, max_glyphs=100)
        self.assertEqual(''.join(c['text'] for c in cues).replace(' ', ''), text.replace(' ', ''))
        self.assertTrue(any('Alice, go!' in c['text'] for c in cues))
        self.assertTrue(any('suspect_foreign_script' in c['flags'] for c in cues))
        self.assertEqual(core.visible_glyphs('กิ่'), 1)

    def test_overlap_repair_preserves_all_text_and_pause_gap(self):
        core = importlib.import_module('aomimama_caption_core')
        data = {'segments': raw('Alice', 0, 2)['segments'] + raw('not gone', 1, 3)['segments']
                + raw('กลับมา', 4, 5)['segments']}
        cues = core.build_cues(data, 5)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0]['text'], 'Alice not gone')
        self.assertIn('overlap_merged', cues[0]['flags'])
        self.assertEqual(cues[1]['start'] - cues[0]['end'], 1)
        core.validate(cues, 5)

    def test_srt_roundtrip_milliseconds_and_invalid_timing(self):
        core = importlib.import_module('aomimama_caption_core')
        self.assertTrue(hasattr(core, 'render_srt'), 'SRT renderer is missing')
        cues = core.build_cues(raw('ไม่ทิ้ง Alice', 0.0006, 2.9996), 3)
        srt = core.render_srt(cues)
        import re
        blocks = srt.strip().split('\n\n')
        parsed = []
        for index, block in enumerate(blocks, 1):
            lines = block.splitlines()
            self.assertEqual(int(lines[0]), index)
            numbers = [int(x) for x in re.findall(r'\d+', lines[1])]
            def seconds(parts):
                h, m, s, ms = parts
                return h*3600 + m*60 + s + ms/1000
            parsed.append({'start': seconds(numbers[:4]), 'end': seconds(numbers[4:]),
                           'text': lines[2]})
        self.assertEqual([(c['start'], c['end'], c['text']) for c in parsed],
                         [(c['start'], c['end'], c['text']) for c in cues])
        core.validate(parsed, 3)
        for invalid in [raw('ห้ามทิ้ง', 0, 0.0001), raw('ห้ามทิ้ง', 4, 5)]:
            with self.assertRaises(ValueError):
                core.build_cues(invalid, 3)
        with self.assertRaises(ValueError):
            core.validate([{'start': 0.0001, 'end': 0.0002, 'text': 'ไม่'}], 1)

    def test_unbreakable_phrase_exceeds_soft_limits_and_is_flagged_not_deleted(self):
        core = importlib.import_module('aomimama_caption_core')
        name = 'ออมิมามะชื่อยาวที่ต้องรักษาทั้งหมด'
        data = raw(name, end=5)
        cues = core.build_cues(data, 6, max_glyphs=8, protected_terms=[name])
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0]['text'], name)
        self.assertEqual(cues[0]['end'], 5)
        self.assertIn('glyph_heuristic_exceeded', cues[0]['flags'])
        self.assertIn('duration_heuristic_exceeded', cues[0]['flags'])
        self.assertIn('low_confidence_review', cues[0]['flags'])

    def test_disagreeing_segment_fragments_require_explicit_reconciliation(self):
        core = importlib.import_module('aomimama_caption_core')
        data = raw('ไม่ทิ้ง Alice')
        data['segments'][0]['words'][0]['word'] = 'ทิ้ง Alice'
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            core.build_cues(data, 5)

    def test_half_second_pause_and_segment_fallback_preserve_text(self):
        core = importlib.import_module('aomimama_caption_core')
        data = raw('วันนี้กลับบ้าน', end=2.5)
        data['segments'][0]['words'] = [
            {'word': 'วันนี้', 'start': 0, 'end': 1},
            {'word': 'กลับบ้าน', 'start': 1.5, 'end': 2.5}]
        cues = core.build_cues(data, 3, max_glyphs=100)
        self.assertEqual([c['text'] for c in cues], ['วันนี้', 'กลับบ้าน'])
        self.assertEqual(cues[1]['start'] - cues[0]['end'], 0.5)
        data['segments'][0]['words'] = []
        cues = core.build_cues(data, 3, max_glyphs=100)
        self.assertEqual(cues[0]['text'], 'วันนี้กลับบ้าน')
        self.assertIn('missing_word_times_segment_fallback', cues[0]['flags'])

    def test_punctuation_spacing_preserves_latin_names_and_thai_repetition_mark(self):
        core = importlib.import_module('aomimama_caption_core')
        cues = core.build_cues(raw('Copper Golem , ไปด้วยกัน ๆ !', end=2), 3, max_glyphs=100)
        self.assertEqual(cues[0]['text'], 'Copper Golem, ไปด้วยกัน ๆ!')


if __name__ == '__main__':
    unittest.main()
