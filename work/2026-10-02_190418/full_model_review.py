import json
from pathlib import Path
import whisper

ROOT=Path(__file__).resolve().parent
model=whisper.load_model('large-v3',device='cuda')
result=model.transcribe(
    str(ROOT/'speech.wav'),language='th',word_timestamps=True,fp16=True,
    initial_prompt='ชื่อช่อง เคที่ Katy404 พี่โอมิ Minecraft',
    condition_on_previous_text=False,temperature=0,beam_size=5,verbose=False,
)
(ROOT/'transcript_full_model.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
for s in result['segments']:
    print(json.dumps({'start':s['start'],'end':s['end'],'text':s['text']},ensure_ascii=False),flush=True)
