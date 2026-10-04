import json
import os
from pathlib import Path
import re

import torch
import stable_whisper

ROOT=Path(__file__).resolve().parent
dll_handle=os.add_dll_directory(str(Path(torch.__file__).parent/'lib'))
plan=json.loads((ROOT/'caption_plan.json').read_text(encoding='utf-8'))
segments=[{'start':s['start'],'end':s['end'],'text':' '.join(s['phrases'])} for s in plan]
for previous,current in zip(segments,segments[1:]):
    if previous['end']>current['start']:
        boundary=(previous['end']+current['start'])/2
        previous['end']=boundary
        current['start']=boundary
model=stable_whisper.load_faster_whisper('large-v3-turbo',device='cuda',compute_type='float16')
result=model.align_words(str(ROOT/'speech.wav'),segments,language='th',regroup=False,
                         normalize_text=False,suppress_silence=True,
                         min_word_dur=0.04,verbose=False)
result.save_as_json(str(ROOT/'aligned_transcript.json'))

def norm(t):
    return re.sub(r'\s+','',t)

cues=[]
assert len(result.segments)==len(plan),(len(result.segments),len(plan))
for spec,segment in zip(plan,result.segments):
    char_times=[]
    aligned_text=''
    for word in segment.words:
        text=norm(word.word)
        aligned_text+=text
        char_times.extend([(word.start,word.end)]*len(text))
    expected=''.join(norm(p) for p in spec['phrases'])
    assert aligned_text==expected,(aligned_text,expected)
    offset=0
    for phrase in spec['phrases']:
        n=len(norm(phrase))
        times=char_times[offset:offset+n]
        start=times[0][0]
        end=times[-1][1]
        offset+=n
        cues.append({'start':start,'end':end,'text':phrase})

for a,b in zip(cues,cues[1:]):
    a['end']=min(a['end'],b['start'])
(ROOT/'cues_aligned.json').write_text(json.dumps(cues,ensure_ascii=False,indent=2),encoding='utf-8')
for c in cues:
    print(f"{c['start']:6.2f} {c['end']:6.2f} {c['end']-c['start']:4.2f} {c['text']}",flush=True)
