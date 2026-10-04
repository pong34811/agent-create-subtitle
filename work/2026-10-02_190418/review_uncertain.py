import json
from pathlib import Path
import wave
import numpy as np
import torch
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq, pipeline

ROOT=Path(__file__).resolve().parent
repo='bjak/distill-whisper-th-large-v3'
p=AutoProcessor.from_pretrained(repo)
m=AutoModelForSpeechSeq2Seq.from_pretrained(repo,dtype=torch.float16).to('cuda')
asr=pipeline('automatic-speech-recognition',model=m,tokenizer=p.tokenizer,
             feature_extractor=p.feature_extractor,device='cuda',dtype=torch.float16)
with wave.open(str(ROOT/'speech.wav')) as f:
    a=np.frombuffer(f.readframes(f.getnframes()),dtype=np.int16).astype(np.float32)/32768
rows=[]
for st,en in [(20,24),(29.6,31),(36.7,38.8),(51,55.9),(55.6,59.6),(66.1,72.7),(73,79.1),(83.7,87.7),(90.8,95),(97.9,103.7)]:
    r=asr({'raw':a[int(st*16000):int(en*16000)],'sampling_rate':16000},generate_kwargs={'language':'thai','task':'transcribe','max_new_tokens':160})
    row={'start':st,'end':en,'text':r['text']}
    rows.append(row)
    print(json.dumps(row,ensure_ascii=False),flush=True)
(ROOT/'review_uncertain.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
