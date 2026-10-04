import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent
raw = json.loads((ROOT / 'cues_aligned.json').read_text(encoding='utf-8'))
raw[0].update(start=2.112, end=3.136)
raw[1].update(start=3.552, end=4.416)
raw[2].update(start=4.896, end=5.472)
raw[3]['start'] = 5.824
raw[29]['text'] = 'เดี๋ยว ก่อนอื่นผม'
raw[54]['text'] = 'พี่ พี่โอมิเนี่ย'
raw[56]['text'] = 'เขาติด เขาติดน้ำท่วมอะ'
raw[70].update(start=85.87, text='ก่อน แล้วก็กดแชร์')
raw[79].update(start=97.21, end=98.17)

merge = {16: 17, 41: 42, 44: 45, 46: 47, 61: 62, 63: 64,
         66: 67, 73: 74, 77: 78}
cues = []
i = 0
while i < len(raw):
    cue = dict(raw[i])
    if i == 35:
        cues.append({'start':44.03, 'end':44.95, 'text':'ช่วงเดือน'})
        cue.update(start=44.95, text='กัน...กันยา')
    if i == 37:
        cue.update(end=48.67, text='ผมไปลอง')
    if i == 38:
        cue.update(start=50.016, text='หัดทำอะไรมาใหม่')
    if i in merge:
        other = raw[merge[i]]
        cue['end'] = other['end']
        cue['text'] += (' ' if i in (63, 77) else '') + other['text']
        i = merge[i]
    # Match Resolve's 60 fps frame grid without showing before the measured onset.
    cue['start_frame'] = math.ceil(cue['start'] * 60 - 1e-7)
    cue['end_frame'] = math.floor(cue['end'] * 60 + 1e-7)
    cue['start'] = cue['start_frame'] / 60
    cue['end'] = cue['end_frame'] / 60
    cues.append(cue)
    i += 1

for i, cue in enumerate(cues):
    cue['start_frame'] = math.ceil(cue['start'] * 60 - 1e-7)
    cue['end_frame'] = math.floor(cue['end'] * 60 + 1e-7)
    cue['start'] = cue['start_frame'] / 60
    cue['end'] = cue['end_frame'] / 60
    assert 0 <= cue['start_frame'] < cue['end_frame'] <= 6227
    if i:
        assert cues[i-1]['end_frame'] <= cue['start_frame']
    assert '\n' not in cue['text']

def stamp(seconds, ass=False):
    units = round(seconds * (100 if ass else 1000))
    unit = 100 if ass else 1000
    hh, units = divmod(units, 3600 * unit)
    mm, units = divmod(units, 60 * unit)
    ss, frac = divmod(units, unit)
    return f'{hh:d}:{mm:02d}:{ss:02d}.{frac:02d}' if ass else f'{hh:02d}:{mm:02d}:{ss:02d},{frac:03d}'

srt = '\n\n'.join(f'{i}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}'
                  for i, c in enumerate(cues, 1)) + '\n'
(ROOT / 'captions_review.srt').write_text(srt, encoding='utf-8-sig')
header = '''[Script Info]
Title: Katy404 Day 20 - Horizontal dynamic captions
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Mitr,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,5,180,180,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
ass = header + ''.join(f'Dialogue: 0,{stamp(c["start"],True)},{stamp(c["end"],True)},Default,,0,0,0,,{{\\pos(960,730)}}{c["text"]}\n' for c in cues)
(ROOT / 'captions_review.ass').write_text(ass, encoding='utf-8-sig')
(ROOT / 'cues_review.json').write_text(json.dumps(cues, ensure_ascii=False, indent=2), encoding='utf-8')
(ROOT / 'transcript_review.txt').write_text('\n'.join(c['text'] for c in cues)+'\n', encoding='utf-8-sig')
durations = [c['end'] - c['start'] for c in cues]
summary = {'count':len(cues), 'average_duration':statistics.mean(durations),
           'minimum_duration':min(durations), 'maximum_duration':max(durations),
           'overlaps':0, 'timeline_fps':60, 'timeline_end_frame':6227,
           'pending_review': ['56-59 seconds: conjunction before follow request',
                              '85-87 seconds: brief word after follow request'],
           'method':'Independent ASR comparison, user name/sentence corrections, audio forced alignment and VAD repairs; not a completed human listening review.'}
(ROOT / 'qc_review.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
