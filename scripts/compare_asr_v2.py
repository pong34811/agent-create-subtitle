"""Focused ASR model shootout: same audio, same prompt, no responseSchema.

Answers: which model transcribes Thai best? Judged on real output against
external corroboration (timeline titles are known, but are NOT sent to the model).
Also tests whether responseSchema causes the spurious inter-word spacing artifact.
"""
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

# Override with AOMIMAMA_RUN_ROOT; default resolves from this script, not a fixed drive path.
import os as _os
RUN_ROOT = Path(_os.environ.get('AOMIMAMA_RUN_ROOT') or Path(__file__).resolve().parents[1] / 'runs' / 'aomimama-2026-09-p1')
OUT = RUN_ROOT / 'model-comparison-v2'
GOOGLE = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
GROQ = 'https://api.groq.com/openai/v1/audio/transcriptions'
SCRATCH = Path('C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-secrets')

PROMPT = ('ตรวจฟังไฟล์เสียงที่แนบจริง แล้วถอดบทพูดภาษาไทยครบทั้งไฟล์ อย่าเดาจากชื่อไฟล์ '
          'ไม่เติมคำ ไม่ย่อ ไม่เซ็นเซอร์ จัดเป็นวลีธรรมชาติตามความหมาย แบ่งวลียาวโดยไม่ตัดคำติดกัน '
          'ชื่อเฉพาะ หรือคำปฏิเสธ ไม่บังคับจำนวนคำ ไม่ใส่ข้อความระหว่างช่วงเงียบ '
          'รวมคำอุทานและภาษาอังกฤษที่ได้ยินจริง ถ้าฟังไม่ชัดให้ใช้ [ฟังไม่ชัด] พร้อมช่วงเวลา '
          'ห้ามแต่ง timestamp ห้ามใส่ช่องว่างระหว่างคำไทย ส่งเฉพาะ JSON '
          '{"audio_available":true,"duration_seconds":<number>,'
          '"timing_measurement":"<string>","segments":[{"start":<number>,"end":<number>,'
          '"text":"<string>","uncertain":<bool>}],"uncertainties":[{"start":<number>,'
          '"end":<number>,"reason":"<string>"}]}')

MODELS = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-3.1-flash-lite']
FILES = [1, 7, 19]


def env_key(name):
    env = Path(os.environ.get('HERMES_HOME') or r'C:\Users\warit\AppData\Local\hermes') / '.env'
    for line in env.read_text(encoding='utf-8').splitlines():
        if line.startswith(name + '='):
            return line.split('=', 1)[1].strip().strip('"').strip("'")
    return None


def scratch(name):
    p = SCRATCH / name
    return p.read_text(encoding='utf-8').strip() if p.exists() else None


def google(model, key, wav, schema):
    cfg = {'temperature': 0, 'maxOutputTokens': 65536}
    if schema:
        cfg['responseMimeType'] = 'application/json'
    body = json.dumps({
        'contents': [{'parts': [{'text': PROMPT},
                                {'inlineData': {'mimeType': 'audio/wav',
                                                'data': base64.b64encode(wav.read_bytes()).decode()}}]}],
        'generationConfig': cfg,
    }).encode()
    req = urllib.request.Request(GOOGLE.format(model=model), data=body, headers={
        'Content-Type': 'application/json', 'x-goog-api-key': key})
    with urllib.request.urlopen(req, timeout=560) as r:
        d = json.load(r)
    c = d['candidates'][0]
    return ''.join(p.get('text', '') for p in c['content']['parts']), c.get('finishReason')


def groq(model, key, wav):
    b = '----x' + uuid.uuid4().hex
    body = b''.join([
        f'--{b}\r\nContent-Disposition: form-data; name="model"\r\n\r\n{model}\r\n'.encode(),
        f'--{b}\r\nContent-Disposition: form-data; name="language"\r\n\r\nth\r\n'.encode(),
        f'--{b}\r\nContent-Disposition: form-data; name="response_format"\r\n\r\nverbose_json\r\n'.encode(),
        f'--{b}\r\nContent-Disposition: form-data; name="temperature"\r\n\r\n0\r\n'.encode(),
        f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\n'
        f'Content-Type: audio/wav\r\n\r\n'.encode(),
        wav.read_bytes(), f'\r\n--{b}--\r\n'.encode()])
    req = urllib.request.Request(GROQ, data=body, headers={
        'Authorization': 'Bearer ' + key, 'User-Agent': 'curl/8.0',
        'Content-Type': f'multipart/form-data; boundary={b}'})
    with urllib.request.urlopen(req, timeout=560) as r:
        return json.load(r)


def parse(text):
    m = re.search(r'\{.*\}', text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def score(d):
    """Objective quality proxies, no listening required."""
    segs = (d or {}).get('segments') or []
    joined = ' '.join(s.get('text', '') for s in segs)
    thai = [c for c in joined if '\u0e00' <= c <= '\u0e7f']
    # Spurious spacing: Thai chars separated by single spaces (broken typography)
    spaced = len(re.findall(r'[\u0e00-\u0e7f]\s+[\u0e00-\u0e7f]', joined))
    latin = re.findall(r'[A-Za-z][A-Za-z ]{2,}', joined)
    return {'segments': len(segs), 'thai_chars': len(thai),
            'spurious_thai_spaces': spaced, 'latin_terms': latin[:6],
            'unclear_marks': joined.count('[ฟังไม่ชัด]'),
            'preview': joined[:260]}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    gkey = env_key('GEMINI_API_KEY')
    gq = scratch('.groq_token')
    rows = {r['index']: r for r in json.loads(
        (RUN_ROOT / 'manifest.json').read_text(encoding='utf-8'))['timelines']}

    for idx in FILES:
        row = rows[idx]
        wav = RUN_ROOT / 'audio' / f"{row['id']}.wav"
        expected = (row['end'] - row['start']) / row['fps']
        print(f'\n{"#"*78}\n# index={idx}  {expected:.0f}s  timeline="{row["name"]}"')
        print(f'# (timeline title is NOT sent to the model — used only to check names)\n{"#"*78}')

        for model in MODELS + ['gemini-2.5-flash#schema']:
            schema = model.endswith('#schema')
            base = model.replace('#schema', '')
            dest = OUT / f'{base}{"-schema" if schema else ""}__{idx}.json'
            if dest.exists():
                saved = json.loads(dest.read_text(encoding='utf-8'))
                print(f'\n[{model}] cached {saved.get("seconds")}s')
                print(json.dumps(saved['score'], ensure_ascii=False, indent=1))
                continue
            t0 = time.monotonic()
            try:
                raw, finish = google(base, gkey, wav, schema)
                d = parse(raw)
                if d is None:
                    print(f'\n[{model}] unparsable finish={finish}: {raw[:160]}')
                    continue
                sc = score(d)
                dest.write_text(json.dumps({'model': model, 'index': idx,
                                            'seconds': round(time.monotonic() - t0, 1),
                                            'score': sc}, ensure_ascii=False, indent=2),
                                encoding='utf-8')
                print(f'\n[{model}] {round(time.monotonic()-t0,1)}s')
                print(json.dumps(sc, ensure_ascii=False, indent=1))
            except urllib.error.HTTPError as e:
                print(f'\n[{model}] HTTP {e.code} {e.read()[:120].decode("utf-8","replace")}')
            except Exception as e:
                print(f'\n[{model}] {type(e).__name__} {str(e)[:120]}')
            time.sleep(3)

        if gq:
            dest = OUT / f'whisper-large-v3__{idx}.json'
            if not dest.exists():
                try:
                    t0 = time.monotonic()
                    g = groq('whisper-large-v3', gq, wav)
                    sc = score({'segments': g.get('segments') or []})
                    sc['duration_reported'] = g.get('duration')
                    dest.write_text(json.dumps({'model': 'whisper-large-v3', 'index': idx,
                                                'seconds': round(time.monotonic() - t0, 1),
                                                'score': sc}, ensure_ascii=False, indent=2),
                                    encoding='utf-8')
                    print(f'\n[whisper-large-v3 via Groq] {round(time.monotonic()-t0,1)}s')
                    print(json.dumps(sc, ensure_ascii=False, indent=1))
                except urllib.error.HTTPError as e:
                    print(f'\n[whisper-large-v3] HTTP {e.code} {e.read()[:150].decode("utf-8","replace")}')
            else:
                saved = json.loads(dest.read_text(encoding='utf-8'))
                print(f'\n[whisper-large-v3] cached')
                print(json.dumps(saved['score'], ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
