"""Batch-transcribe rendered Aomi-mama timeline WAVs via Gemini through the local Hermes proxy.

Reads manifest.json, skips already-present transcripts (metadata-checked), posts base64 audio
to google/gemini-3.8-flash, asks for strict JSON {audio_available,duration_seconds,timing_measurement,
segments:[{start,end,text,uncertain}],uncertainties}, validates the response, and writes
transcripts/<id>.gemini.json. Raw/never-edited artifacts; no Resolve access, no approval logic.
"""
import base64
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

# Override with AOMIMAMA_RUN_ROOT; default resolves from this script, not a fixed drive path.
import os as _os
RUN_ROOT = Path(_os.environ.get('AOMIMAMA_RUN_ROOT') or Path(__file__).resolve().parents[1] / 'runs' / 'aomimama-2026-09-p1')
PROXY = 'http://127.0.0.1:8645/v1/chat/completions'
MODEL = 'google/gemini-3.8-flash'
AUTH = 'Bearer local-proxy'

PROMPT = ('ตรวจฟังไฟล์เสียงที่แนบจริง แล้วถอดบทพูดภาษาไทยครบทั้งไฟล์ อย่าเดาจากชื่อไฟล์ '
          'ไม่เติมคำ ไม่ย่อ ไม่เซ็นเซอร์ จัดเป็นวลีธรรมชาติตามความหมาย แบ่งวลียาวโดยไม่ตัดคำติดกัน '
          'ชื่อเฉพาะ หรือคำปฏิเสธ ไม่บังคับจำนวนคำ ไม่ใส่ข้อความระหว่างช่วงเงียบ '
          'รวมคำอุทานและภาษาอังกฤษที่ได้ยินจริง ถ้าฟังไม่ชัดให้ใช้ [ฟังไม่ชัด] พร้อมช่วงเวลา '
          'ถ้าไม่ได้รับเสียงจริงให้ตอบ {"audio_available": false} แล้วหยุด '
          'ห้ามแต่ง timestamp ถ้าวัดไม่ได้ ให้ระบุ timing_measurement เป็น measured_timestamps '
          'หรือ estimated_by_listening พร้อมความคลาดเคลื่อนโดยประมาณ ส่งเฉพาะ JSON '
          '{"audio_available":true,"duration_seconds":<ตัวเลข>,"timing_measurement":"<string>",'
          '"segments":[{"start":<ตัวเลข>,"end":<ตัวเลข>,"text":"<string>","uncertain":<bool>}],'
          '"uncertainties":[{"start":<ตัวเลข>,"end":<ตัวเลข>,"reason":"<string>"}]}')


def load_manifest():
    rows = json.loads((RUN_ROOT / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    assert len({r['id'] for r in rows}) == len(rows) == 49
    return rows


def transcribe_one(wav_path, expected_seconds):
    payload = base64.b64encode(wav_path.read_bytes()).decode()
    body = json.dumps({
        'model': MODEL,
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': PROMPT},
            {'type': 'file', 'file': {'filename': wav_path.name,
                                      'file_data': 'data:audio/wav;base64,' + payload}},
        ]}],
        'max_tokens': 16000,
    }).encode()
    req = urllib.request.Request(PROXY, data=body, headers={
        'Content-Type': 'application/json', 'Authorization': AUTH})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=560) as r:
                data = json.load(r)
            break
        except Exception as exc:
            detail = ''
            if hasattr(exc, 'read'):
                try:
                    detail = exc.read()[:400].decode('utf-8', 'replace')
                except Exception:
                    detail = ''
            print('  attempt', attempt + 1, 'failed:', type(exc).__name__, str(exc)[:120],
                  detail[:400], flush=True)
            if attempt == 2:
                raise
            time.sleep(8 * (attempt + 1))
    finish = data['choices'][0].get('finish_reason')
    content = data['choices'][0]['message'].get('content') or ''
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.S) or \
            re.search(r'(\{.*\})', content, re.S)
    if not match and finish == 'content_filter':
        print('  content_filter: model refused this file; recording refusal and continuing', flush=True)
        return {'audio_available': False, 'blocked_by_content_filter': True}
    assert match, f'no JSON in model reply (finish={finish}): ' + content[:400]
    raw = match.group(1) or match.group(0)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Gemini tends to break long strings across lines; join continuation lines
        # inside string literals by stripping raw newlines before punctuation/quote seams.
        raw = re.sub(r'"\s*\\n\s*"', ' ', raw)
        result = json.loads(raw)
    assert result.get('audio_available') is not None
    if not result.get('audio_available'):
        return result
    assert isinstance(result.get('segments'), list)
    segments = result['segments']
    assert all(isinstance(s.get('start'), (int, float)) and isinstance(s.get('end'), (int, float))
               and s['start'] >= 0 and s['end'] >= s['start'] and isinstance(s.get('text'), str)
               for s in segments)
    for s in segments:
        s.setdefault('uncertain', False)
    if segments and max(s['start'] for s in segments) > expected_seconds * 1.35:
        print('  timing drift: segments beyond file duration; marking all uncertain', flush=True)
        for s in segments:
            s['uncertain'] = True
        result['timing_drift'] = (f"max start {max(s['start'] for s in segments)}s exceeds "
                                  f"manifest duration {expected_seconds}s")
    if result.get('duration_seconds') and abs(result['duration_seconds'] - expected_seconds) > expected_seconds * 0.25:
        result['duration_drift_note'] = (f"model reported {result['duration_seconds']}s "
                                         f"vs manifest {expected_seconds}s; kept model segments")
    return result


def main():
    rows = load_manifest()
    only = [int(x) for x in sys.argv[1:]] or None
    for row in rows:
        if only and row['index'] not in only:
            continue
        uid = row['id']
        dest = RUN_ROOT / 'transcripts' / f'{uid}.gemini.json'
        if dest.exists():
            existing = json.loads(dest.read_text(encoding='utf-8'))
            if existing.get('metadata', {}).get('model') == MODEL:
                print(row['index'], uid, 'RESUME_SKIP', flush=True)
                continue
        expected = (row['end'] - row['start']) / row['fps']
        wav = RUN_ROOT / 'audio' / f'{uid}.wav'
        assert wav.is_file() and wav.stat().st_size > 0
        t0 = time.monotonic()
        result = transcribe_one(wav, expected)
        out = {'metadata': {'model': MODEL, 'timeline_index': row['index'], 'timeline_id': uid,
                            'timeline_name': row['name'], 'expected_duration_seconds': expected,
                            'wav_sha256_note': 'hash recorded by transcribe; see audio hash in reviewed artifacts'},
               'duration_seconds': expected, 'gemini': result}
        dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
        n = len(result.get('segments') or [])
        print(row['index'], uid, 'OK', n, 'segments', round(time.monotonic() - t0, 1), 's', flush=True)


if __name__ == '__main__':
    main()
