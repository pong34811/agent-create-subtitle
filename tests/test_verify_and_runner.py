"""Tests for verify_cues_audio and run_pipeline helpers (synthetic audio, no network)."""
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_pipeline as rp  # noqa: E402
import verify_cues_audio as vca  # noqa: E402


def _tone_mask(segments, total=6.0):
    """Frame mask for a signal that is loud only inside the given (start, end) spans."""
    n = int(total / vca.FRAME_S)
    db = np.full(n, -70.0)
    for a, b in segments:
        db[int(a / vca.FRAME_S):int(b / vca.FRAME_S)] = -20.0
    return vca.active_mask(db)


def test_cue_over_speech_passes_and_cue_over_silence_is_flagged():
    mask = _tone_mask([(1.0, 2.5)])
    good = {'start': 1.0, 'end': 2.5, 'text': 'พูดจริง'}
    silent = {'start': 4.0, 'end': 5.0, 'text': 'ไม่มีเสียง'}
    flags = vca.check_cues([good, silent], mask, 6.0)
    assert [f['cue'] for f in flags] == [2]
    assert 'little_audio_under_cue' in flags[0]['problems']


def test_cue_past_end_of_audio_and_bad_duration_are_flagged():
    mask = _tone_mask([(1.0, 5.9)])
    flags = vca.check_cues([{'start': 5.0, 'end': 6.5, 'text': 'x'},
                            {'start': 3.0, 'end': 3.0, 'text': 'y'}], mask, 6.0)
    assert 'past_end_of_audio' in flags[0]['problems']
    assert 'non_positive_duration' in flags[1]['problems']


def test_verify_pair_end_to_end_with_real_ffmpeg(tmp_path):
    pytest.importorskip('numpy')
    wav = tmp_path / 'a.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-t', '1', '-i', 'anullsrc=r=16000:cl=mono',
                    '-f', 'lavfi', '-i', 'sine=frequency=500:duration=1.5:sample_rate=16000',
                    '-filter_complex', '[0][1]concat=n=2:v=0:a=1', '-y', str(wav)], check=True)
    srt = tmp_path / 'a.srt'
    srt.write_text('1\n00:00:01,000 --> 00:00:02,400\nเสียง\n\n2\n00:00:00,000 --> 00:00:00,900\nเงียบ\n',
                   encoding='utf-8-sig')
    result = vca.verify_pair(srt, wav)
    assert result['cues'] == 2
    assert [f['text'] for f in result['flags']] == ['เงียบ']


def test_runner_picks_the_right_interpreter_per_stage():
    assert rp.build_command('import', [1, 2])[:2] == ['py', '-3.12']
    assert '--apply' not in rp.build_command('import', [])
    assert '--apply' in rp.build_command('import', [3], apply=True)
    assert rp.build_command('transcribe', [36])[-1] == '36'
    assert rp.build_command('cues', [])[0].endswith('python.exe') or rp.build_command('cues', [])[0] == sys.executable
    assert rp.build_command('verify', [8])[-2:] == ['--only', '8'] or '8' in rp.build_command('verify', [8])


def test_apply_is_rejected_outside_import():
    with pytest.raises(SystemExit):
        rp.main(['verify', '--apply'])
