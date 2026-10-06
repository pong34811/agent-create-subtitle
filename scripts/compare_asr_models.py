"""Controlled model comparison for Thai audio transcription.

Runs the SAME prompt over the SAME rendered WAVs with each candidate model and
prints a side-by-side table so quality can be judged from real output, not vibes.

Read-only: writes only runs/<run>/model-comparison/<model>__<index>.json
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

RUN_ROOT = Path('C:/Users/warit/Desktop/agent-create-subtitle/runs/aomimama-2026-09-p1')
OUT = RUN_ROOT / 'model-comparison'
GOOGLE = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
GROQ = 'https://api.groq.com/openai/v1/audio/transcriptions'
SCRATCH = Path('C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-secrets')

PROMPT = ('ตรวจฟังไฟล์เสียงที่แนบจริง แล้วถอดบทพูดภาษาไทยครบทั้งไฟล์ อย่าเดาจากชื่อไฟล์ '
          'ไม่เติมคำ ไม่ย่อ ไม่เซ็นเซอร์ จัดเป็นวลีธรรมชาติตามความหมาย แบ่งวลียาวโดยไม่ตัดคำติดกัน '
          'ชื่อเฉพาะ หรือคำปฏิเสธ ไม่บังคับจำนวนคำ ไม่ใส่ข้อความระหว่างช่วงเงียบ '
          'รวมคำอุทานและภาษาอังกฤษที่ได้ยินจริง ถ้าฟังไม่ชัดให้ใช้ [ฟังไม่ชัด] พร้อมช่วงเวลา '
          'ถ้าไม่ได้รับเสียงจริงให้ตอบ {"audio_available": false} แล้วหยุด ห้ามแต่ง timestamp '
          'ส่งเฉพาะ JSON {"audio_available":true,"duration_seconds":<number>,'
          '"timing_measurement":"<string>","segments":[{"start":<number>,"end":<number>,'
          '"text":"<string>","uncertain":<bool>}],"uncertainties":[{"start":<number>,'
          '"end":<number>,"reason":"<string>"}]}')

# index -> human label, tested against the same audio
CASES = {1: 'intro/hi (90.6s)', 23: 'few-segment suspect (110s)'}


def env_key(name):
    env = Path(os.environ.get('HERMES_HOME') or r'C:\Users\warit\AppData\Local\hermes') / '.env'
    for line in env.read_text(encoding='utf-8').splitlines():
        if line.startswith(name + '='):
            return line.split('=', 1)[1].strip().strip('"').strip("'")
    return None


def scratch(name):
    p = SCRATCH / name
    return p.read_text(encoding='utf-8').strip() if p.exists() else None


def google_call(model, key, wav, use_schema):
    cfg = {'temperature': 0, 'maxOutputTokens': 65536}
    if use_schema:
        cfg['responseMimeType'] = 'application/json'
    body = json.dumps({
        'contents': [{'parts': [{'text': PROMPT},
                                {'inlineData': {'mimeType': 'audio/wav',
                                                'data': base64.b64encode(wav.read_bytes()).decode()}}]}],
        'generationConfig': cfg,
    }).encode()
    req = urllib.request.Request(GOOGLE.format(model=model), data=body,
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
    with urllib.request.urlopen(req, timeout=560) as r:
        data = json.load(r)
    cand = data['candidates'][0]
    return ''.join(p.get('text', '') for p in cand['content']['parts']), cand.get('finishReason')


def groq_call(model, key, wav):
    import uuid
    b = '----cmp' + uuid.uuid4().hex
    parts = [
        f'--{b}\r\nContent-Disposition: form-data; name="model"\r\n\r\n{model}\r\n'.encode(),
        f'--{b}\r\nContent-Disposition: form-data; name="language"\r\n\r\nth\r\n'.encode(),
        f'--{b}\r\nContent-Disposition: form-data; name="response_format"\r\n\r\nverbose_json\r\n'.encode(),
        f'--{b}\r\nContent-Disposition: form-data; name="temperature"\r\n\r\n0\r\n'.encode(),
        f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\n'
        f'Content-Type: audio/wav\r\n\r\n'.encode(),
        wav.read_bytes(),
        f'\r\n--{b}--\r\n'.encode(),
    ]
    req = urllib.request.Request(GROQ, data=b''.join(parts),
                                 headers={'Authorization': 'Bearer ' + key,
                                          'Content-Type': f'multipart/form-data; boundary={b}'})
    with urllib.request.urlopen(req, timeout=560) as r:
        return json.load(r)


def summarize(text, kind):
    if kind == 'groq':
        segs = text.get('segments') or []
        joined = ' '.join(s['text'].strip() for s in segs)
        return {'duration': text.get('duration'), 'segments': len(segs),
                'text': joined[:900], 'chars': len(joined)}
    import re
    m = re.search(r'\{.*\}', text, re.S)
    if not m:
        return {'error': 'no json', 'raw': text[:300]}
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {'error': 'bad json', 'raw': text[:300]}
    segs = d.get('segments') or []
    joined = ' '.join(s.get('text', '') for s in segs)
    return {'duration': d.get('duration_seconds'), 'segments': len(segs),
            'timing': d.get('timing_measurement'), 'text': joined[:900], 'chars': len(joined),
            'uncertain': sum(1 for s in segs if s.get('uncertain'))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    gkey = env_key('GEMINI_API_KEY')
    groq = scratch('.groq_token')
    rows = {r['index']: r for r in json.loads((RUN_ROOT / 'manifest.json').read_text(encoding='utf-8'))['timelines']}

    plan = []
    for model in ['gemini-2.5-flash', 'gemini-3.1-flash-lite', 'gemini-flash-latest',
                  'gemini-3-flash-preview']:
        plan.append(('google', model, True))
    plan.append(('google', 'gemini-2.5-flash', False))  # schema vs free-form
    if groq:
        plan.append(('groq', 'whisper-large-v3', False))

    for index, label in CASES.items():
        row = rows[index]
        wav = RUN_ROOT / 'audio' / f"{row['id']}.wav"
        expected = (row['end'] - row['start']) / row['fps']
        print(f'\n{"="*78}\nFILE index={index}  {label}  expected={expected:.1f}s  {row["name"][:40]}\n{"="*78}')
        for kind, model, use_schema in plan:
            tag = f'{model}{"" if use_schema else " (no schema)"}'
            dest = OUT / f'{model}{"" if use_schema else "-noschema"}__{index}.json'
            if dest.exists():
                saved = json.loads(dest.read_text(encoding='utf-8'))
                print(f'\n--- {tag} [cached {saved.get("seconds")}s] ---')
                print(json.dumps(saved['summary'], ensure_ascii=False, indent=1)[:1200])
                continue
            t0 = time.monotonic()
            try:
                if kind == 'google':
                    raw, finish = google_call(model, gkey, wav, use_schema)
                    summary = summarize(raw, 'google')
                else:
                    raw = groq_call(model, groq, wav)
                    summary = summarize(raw, 'groq')
                elapsed = round(time.monotonic() - t0, 1)
                dest.write_text(json.dumps({'model': model, 'index': index, 'seconds': elapsed,
                                            'expected': expected, 'summary': summary},
                                           ensure_ascii=False, indent=2), encoding='utf-8')
                print(f'\n--- {tag} [{elapsed}s] ---')
                print(json.dumps(summary, ensure_ascii=False, indent=1)[:1200])
            except urllib.error.HTTPError as exc:
                body = exc.read()[:200].decode('utf-8', 'replace').replace('\n', ' ')
                print(f'\n--- {tag} [HTTP {exc.code}] {body}')
            except Exception as exc:
                print(f'\n--- {tag} [{type(exc).__name__}] {str(exc)[:160]}')
            time.sleep(3)


if __name__ == '__main__':
    main()
