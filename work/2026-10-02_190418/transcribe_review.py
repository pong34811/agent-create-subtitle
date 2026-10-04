import json
import os
import time
from pathlib import Path

import torch
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parent
dll_handle = os.add_dll_directory(str(Path(torch.__file__).parent / 'lib'))
started = time.time()
model = WhisperModel('large-v3-turbo', device='cuda', compute_type='float16')
segments, info = model.transcribe(
    str(ROOT / 'speech.wav'), language='th', task='transcribe',
    word_timestamps=True, vad_filter=True, beam_size=5, temperature=0,
    condition_on_previous_text=False,
    vad_parameters={'min_silence_duration_ms': 250, 'speech_pad_ms': 100},
)
rows = []
for seg in segments:
    row = {
        'start': seg.start, 'end': seg.end, 'text': seg.text,
        'avg_logprob': seg.avg_logprob, 'no_speech_prob': seg.no_speech_prob,
        'words': [{'start': w.start, 'end': w.end, 'text': w.word,
                   'probability': w.probability} for w in seg.words or []],
    }
    rows.append(row)
    print(json.dumps({'start': seg.start, 'end': seg.end, 'text': seg.text}, ensure_ascii=False), flush=True)
result = {'model': 'large-v3-turbo', 'language': info.language,
          'duration': info.duration, 'segments': rows}
(ROOT / 'transcript_initial.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'elapsed={time.time()-started:.1f}s segments={len(rows)}', flush=True)
