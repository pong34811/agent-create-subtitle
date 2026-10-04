import json
import os
from pathlib import Path

import torch
from faster_whisper import WhisperModel
import numpy as np
import wave

ROOT = Path(__file__).resolve().parent
dll_handle = os.add_dll_directory(str(Path(torch.__file__).parent / 'lib'))
model = WhisperModel('large-v3-turbo', device='cuda', compute_type='float16')
with wave.open(str(ROOT / 'speech.wav')) as reader:
    audio = np.frombuffer(reader.readframes(reader.getnframes()),dtype=np.int16).astype(np.float32)/32768
intervals=[(0,7.9),(7.7,20.1),(20,30.4),(30.1,38.6),(38.4,51.1),(51,59.7),(59.5,72.6),(72.5,83.8),(83.6,98.4),(98.2,103.78)]
rows=[]
for a,b in intervals:
    segments,info=model.transcribe(
        audio[int(a*16000):int(b*16000)],language='th',word_timestamps=True,
        vad_filter=False,beam_size=5,temperature=0,condition_on_previous_text=False,
        initial_prompt='เคที่ Katy404 พี่โอมิ Minecraft ยอดผู้ติดตาม หนึ่งหมื่นซับ เดือนกันยา เดือนสิบ',
    )
    window=[]
    for s in segments:
        row={'start':a+s.start,'end':a+s.end,'text':s.text,
             'words':[{'start':a+w.start,'end':a+w.end,'text':w.word,'probability':w.probability} for w in s.words or []]}
        window.append(row)
        print(json.dumps({'start':row['start'],'end':row['end'],'text':row['text']},ensure_ascii=False),flush=True)
    rows.append({'window_start':a,'window_end':b,'segments':window})
(ROOT/'transcript_refined.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
