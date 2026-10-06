import importlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class FakeModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, path, **options):
        self.calls.append((path, options))
        words = [SimpleNamespace(word='ไม่ทิ้ง Alice', start=0, end=2, probability=0.01)]
        segment = SimpleNamespace(id=0, seek=0, start=0, end=2, text='ไม่ทิ้ง Alice',
                                  avg_logprob=-3, no_speech_prob=0.9,
                                  compression_ratio=1.0, temperature=0.0, words=words)
        return iter([segment]), SimpleNamespace(language='th', language_probability=0.8,
                                               duration=2, duration_after_vad=2)


class ASRTests(unittest.TestCase):
    def fixture(self, root):
        timelines = [{'index': i, 'id': f'uuid-{i}', 'name': f'clip {i}',
                      'start': 120, 'end': 240, 'fps': 60} for i in (1, 2)]
        (root / 'manifest.json').write_text(json.dumps({'project': 'test-project',
                                                      'timelines': timelines}))
        (root / 'audio').mkdir()
        for timeline in timelines:
            with wave.open(str(root / 'audio' / f"{timeline['id']}.wav"), 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b'\0\0' * 32000)
        return timelines

    def test_malformed_cache_fails_closed_preserving_raw(self):
        import copy
        helper = importlib.import_module('aomimama_asr')
        with tempfile.TemporaryDirectory(dir='C:/Users/warit/AppData/Local/hermes/cache/scratch') as temporary:
            root = Path(temporary)
            self.fixture(root)
            args = helper.parse_args(['--run-root', str(root), '--indices', '1'])
            model = FakeModel()
            helper.run(args, model_factory=lambda *a, **k: model)
            path = root / 'transcripts' / 'uuid-1.json'
            valid = json.loads(path.read_text(encoding='utf-8'))
            (root / 'reviewed' / 'uuid-1.json').unlink()
            (root / 'srt' / 'uuid-1.draft.srt').unlink()
            mutations = [lambda r: r.pop('segments'),
                         lambda r: r.update(segments=None),
                         lambda r: r.pop('info'),
                         lambda r: r.update(duration_seconds='2'),
                         lambda r: r['metadata'].update(schema_version=99),
                         lambda r: r['metadata']['audio'].pop('frames'),
                         lambda r: r['metadata']['timeline'].update(fps='60'),
                         lambda r: r['metadata'].pop('transcribe_options'),
                         lambda r: r['segments'][0].pop('avg_logprob'),
                         lambda r: r['segments'][0].update(words={}),
                         lambda r: r['segments'][0]['words'][0].pop('probability'),
                         lambda r: r['segments'][0]['words'][0].update(start='0'),
                         lambda r: r['segments'][0]['words'][0].update(probability=True)]
            for mutate in mutations:
                broken = copy.deepcopy(valid)
                mutate(broken)
                path.write_text(json.dumps(broken, ensure_ascii=False), encoding='utf-8')
                before = path.read_bytes()
                with self.assertRaisesRegex(ValueError, 'reconciliation'):
                    helper.run(args, model_factory=lambda *a, **k: model)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(len(model.calls), 1)
                self.assertFalse((root / 'reviewed' / 'uuid-1.json').exists())
                self.assertFalse((root / 'srt' / 'uuid-1.draft.srt').exists())
            valid['segments'] = []  # Explicit no-speech remains a valid cache.
            path.write_text(json.dumps(valid), encoding='utf-8')
            result = helper.run(args, model_factory=lambda *a, **k: model)
            self.assertEqual(result[0]['cue_count'], 0)
            self.assertEqual(len(model.calls), 1)

    def test_batch_one_model_retains_confidence_and_unapproved_drafts(self):
        self.assertIsNotNone(importlib.util.find_spec('aomimama_asr'), 'offline ASR helper is missing')
        helper = importlib.import_module('aomimama_asr')
        with tempfile.TemporaryDirectory(dir='C:/Users/warit/AppData/Local/hermes/cache/scratch') as temporary:
            root = Path(temporary)
            self.fixture(root)
            model = FakeModel()
            loads = []
            def factory(*args, **kwargs):
                loads.append((args, kwargs))
                return model
            args = helper.parse_args(['--run-root', str(root), '--device', 'cpu', '--compute', 'int8'])
            result = helper.run(args, model_factory=factory)
            self.assertEqual(len(loads), 1)
            self.assertEqual(len(model.calls), 2)
            self.assertEqual(len(result), 2)
            for i in (1, 2):
                transcript = json.loads((root / 'transcripts' / f'uuid-{i}.json').read_text(encoding='utf-8'))
                self.assertEqual(transcript['segments'][0]['avg_logprob'], -3)
                self.assertEqual(transcript['segments'][0]['no_speech_prob'], 0.9)
                self.assertEqual(transcript['segments'][0]['words'][0]['probability'], 0.01)
                self.assertEqual(transcript['segments'][0]['text'], 'ไม่ทิ้ง Alice')
                reviewed = json.loads((root / 'reviewed' / f'uuid-{i}.json').read_text(encoding='utf-8'))
                self.assertIs(reviewed['approved'], False)
                self.assertTrue((root / 'srt' / f'uuid-{i}.draft.srt').exists())
            helper.run(args, model_factory=factory)
            self.assertEqual(len(loads), 1, 'exact metadata resume must not load a model')

    def test_rerun_never_overwrites_human_review(self):
        helper = importlib.import_module('aomimama_asr')
        with tempfile.TemporaryDirectory(dir='C:/Users/warit/AppData/Local/hermes/cache/scratch') as temporary:
            root = Path(temporary)
            self.fixture(root)
            args = helper.parse_args(['--run-root', str(root), '--indices', '1'])
            factory = lambda *a, **k: FakeModel()
            helper.run(args, model_factory=factory)
            path = root / 'reviewed' / 'uuid-1.json'
            draft = json.loads(path.read_text(encoding='utf-8'))
            draft['approved'] = True
            draft['cues'][0]['text'] = 'human correction'
            path.write_text(json.dumps(draft, ensure_ascii=False), encoding='utf-8')
            previous = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'review'):
                helper.run(args, model_factory=factory)
            self.assertEqual(path.read_bytes(), previous)

    def test_changed_audio_invalidates_resume_and_archives_previous_raw(self):
        helper = importlib.import_module('aomimama_asr')
        with tempfile.TemporaryDirectory(dir='C:/Users/warit/AppData/Local/hermes/cache/scratch') as temporary:
            root = Path(temporary)
            self.fixture(root)
            args = helper.parse_args(['--run-root', str(root), '--indices', '2'])
            model = FakeModel()
            factory = lambda *a, **k: model
            helper.run(args, model_factory=factory)
            raw_path = root / 'transcripts' / 'uuid-2.json'
            old_raw = raw_path.read_bytes()
            (root / 'reviewed' / 'uuid-2.json').unlink()
            wav_path = root / 'audio' / 'uuid-2.wav'
            with wav_path.open('r+b') as source:
                source.seek(44)
                source.write(b'\x01\x00')
            helper.run(args, model_factory=factory)
            self.assertEqual(len(model.calls), 2)
            archives = list((root / 'transcripts' / 'archive').glob('uuid-2.*.json'))
            self.assertEqual(len(archives), 1, 'superseded raw must be archived')
            self.assertEqual(archives[0].read_bytes(), old_raw)
            self.assertNotEqual(raw_path.read_bytes(), old_raw)

    def test_duplicate_manifest_identity_rejected_before_model_load(self):
        helper = importlib.import_module('aomimama_asr')
        with tempfile.TemporaryDirectory(dir='C:/Users/warit/AppData/Local/hermes/cache/scratch') as temporary:
            root = Path(temporary)
            timelines = self.fixture(root)
            timelines[1]['id'] = timelines[0]['id']
            (root / 'manifest.json').write_text(json.dumps({'project': 'test-project', 'timelines': timelines}))
            args = helper.parse_args(['--run-root', str(root)])
            loads = []
            def factory(*a, **k):
                loads.append(1)
                return FakeModel()
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                helper.run(args, model_factory=factory)
            self.assertFalse(loads)

    def test_truncated_wav_rejected_before_model_load(self):
        helper = importlib.import_module('aomimama_asr')
        with tempfile.TemporaryDirectory(dir='C:/Users/warit/AppData/Local/hermes/cache/scratch') as temporary:
            root = Path(temporary)
            self.fixture(root)
            wav_path = root / 'audio' / 'uuid-2.wav'
            with wav_path.open('r+b') as source:
                source.truncate(100)
            args = helper.parse_args(['--run-root', str(root)])
            loads = []
            def factory(*a, **k):
                loads.append(1)
                return FakeModel()
            with self.assertRaisesRegex(ValueError, 'truncated'):
                helper.run(args, model_factory=factory)
            self.assertFalse(loads)

    def test_windows_cuda_dll_discovery_only_uses_existing_package_dirs(self):
        helper = importlib.import_module('aomimama_asr')
        self.assertTrue(hasattr(helper, 'cuda_dll_directories'), 'Windows CUDA DLL discovery is missing')
        with tempfile.TemporaryDirectory(dir='C:/Users/warit/AppData/Local/hermes/cache/scratch') as temporary:
            root = Path(temporary)
            torch_lib = root / 'torch' / 'lib'
            nvidia_bin = root / 'nvidia' / 'cublas' / 'bin'
            torch_lib.mkdir(parents=True)
            nvidia_bin.mkdir(parents=True)
            self.assertEqual(set(helper.cuda_dll_directories([str(root)])), {torch_lib, nvidia_bin})

    def test_preflight_duration_root_index_and_fps_checks(self):
        helper = importlib.import_module('aomimama_asr')
        with tempfile.TemporaryDirectory(dir='C:/Users/warit/AppData/Local/hermes/cache/scratch') as temporary:
            root = Path(temporary)
            timelines = self.fixture(root)
            loads = []
            def factory(*a, **k):
                loads.append(1)
                return FakeModel()
            for argv in [['--run-root', '.'], ['--run-root', str(root), '--indices', '99']]:
                with self.assertRaises(ValueError):
                    helper.run(helper.parse_args(argv), model_factory=factory)
            timelines[1]['end'] = 300
            manifest_path = root / 'manifest.json'
            manifest_path.write_text(json.dumps({'project': 'test-project', 'timelines': timelines}))
            with self.assertRaisesRegex(ValueError, 'duration mismatch'):
                helper.run(helper.parse_args(['--run-root', str(root)]), model_factory=factory)
            timelines[1]['end'] = 240
            timelines[1]['fps'] = 0
            manifest_path.write_text(json.dumps({'project': 'test-project', 'timelines': timelines}))
            with self.assertRaisesRegex(ValueError, 'fps'):
                helper.run(helper.parse_args(['--run-root', str(root)]), model_factory=factory)
            self.assertFalse(loads)

    def test_audio_mutation_during_decode_stops_before_persisting_raw(self):
        helper = importlib.import_module('aomimama_asr')
        with tempfile.TemporaryDirectory(dir='C:/Users/warit/AppData/Local/hermes/cache/scratch') as temporary:
            root = Path(temporary)
            self.fixture(root)
            class MutatingModel(FakeModel):
                def transcribe(self, path, **options):
                    with Path(path).open('r+b') as source:
                        source.seek(44)
                        source.write(b'\x02\x00')
                    return super().transcribe(path, **options)
            args = helper.parse_args(['--run-root', str(root), '--indices', '1'])
            with self.assertRaisesRegex(ValueError, 'changed'):
                helper.run(args, model_factory=lambda *a, **k: MutatingModel())
            self.assertFalse((root / 'transcripts' / 'uuid-1.json').exists())


if __name__ == '__main__':
    unittest.main()
