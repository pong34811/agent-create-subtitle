"""Batch-transcribe rendered Aomi-mama timeline WAVs via the Google Gemini API directly.

Uses GEMINI_API_KEY from the Hermes .env (AI Studio key). Posts inline base64 audio to
gemini-3-flash-preview, asks for strict JSON, validates, and writes
transcripts/<id>.gemini.json (archiving any previous proxy-route result first).

Raw artifacts only: no Resolve access, no cue approval, no subtitle import.
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RUN_ROOT = Path('C:/Users/warit/Desktop/agent-create-subtitle/runs/aomimama-2026-09-p1')
# Ordered by MEASURED Thai quality (scripts/compare_asr_v2.py, same audio), then
# newest-generation first. Newer Gemini releases transcribe Thai markedly better:
#   3.7/3.6/3.5-flash  newest — best names + fluency
#   3-flash-preview    proven best of the older set (quota spent until reset)
#   3.1-flash-lite     2nd tier, reliable, low spacing
#   2.5-flash          3rd — inserts a space between EVERY Thai word
#   *-lite-latest      last resort; may answer with all-[ฟังไม่ชัด] stubs
# Free-tier quota is per model per day; fall through on 429/5xx.
MODELS = ['gemini-3.7-flash', 'gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-3.5-flash-lite',
          'gemini-3-flash-preview', 'gemini-3.1-flash-lite', 'gemini-3.1-flash-lite-preview',
          'gemini-2.5-flash', 'gemini-flash-lite-latest', 'gemini-flash-latest']
API = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

PROMPT = ('ตรวจฟังไฟล์เสียงที่แนบจริง แล้วถอดบทพูดภาษาไทยครบทั้งไฟล์ อย่าเดาจากชื่อไฟล์ '
          'ไม่เติมคำ ไม่ย่อ ไม่เซ็นเซอร์ จัดเป็นวลีธรรมชาติตามความหมาย แบ่งวลียาวโดยไม่ตัดคำติดกัน '
          'ชื่อเฉพาะ หรือคำปฏิเสธ ไม่บังคับจำนวนคำ ไม่ใส่ข้อความระหว่างช่วงเงียบ '
          'รวมคำอุทานและภาษาอังกฤษที่ได้ยินจริง ถ้าฟังไม่ชัดให้ใช้ [ฟังไม่ชัด] พร้อมช่วงเวลา '
          'ถ้าไม่ได้รับเสียงจริงให้ตอบ {"audio_available": false} แล้วหยุด ห้ามแต่ง timestamp '
          'ส่งเฉพาะ JSON {"audio_available":true,"duration_seconds":<number>,'
          '"timing_measurement":"<string>","segments":[{"start":<number>,"end":<number>,'
          '"text":"<string>","uncertain":<bool>}],"uncertainties":[{"start":<number>,'
          '"end":<number>,"reason":"<string>"}]}')

# Forced structured output: Gemini must return this exact shape, which removes the
# malformed-JSON failures seen when it free-formatted long Thai strings.
RESPONSE_SCHEMA = {
    'type': 'object',
    'properties': {
        'audio_available': {'type': 'boolean'},
        'duration_seconds': {'type': 'number'},
        'timing_measurement': {'type': 'string'},
        'segments': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'start': {'type': 'number'},
                    'end': {'type': 'number'},
                    'text': {'type': 'string'},
                    'uncertain': {'type': 'boolean'},
                },
                'required': ['start', 'end', 'text', 'uncertain'],
            },
        },
        'uncertainties': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'start': {'type': 'number'},
                    'end': {'type': 'number'},
                    'reason': {'type': 'string'},
                },
                'required': ['start', 'end', 'reason'],
            },
        },
    },
    'required': ['audio_available', 'duration_seconds', 'segments'],
}


def api_key():
    env = Path(os.environ.get('HERMES_HOME') or r'C:\Users\warit\AppData\Local\hermes') / '.env'
    for line in env.read_text(encoding='utf-8').splitlines():
        if line.startswith('GEMINI_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise SystemExit('GEMINI_API_KEY not found in Hermes .env')


def load_manifest():
    rows = json.loads((RUN_ROOT / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    assert len({r['id'] for r in rows}) == len(rows) == 49
    return rows


def call(key, wav_path, model, duration=None):
    """One generateContent request.

    frequencyPenalty stops the character-repetition loops ("โอ้ยยยยย…") that eat
    the whole token budget on long Thai transcripts, but only some models accept
    it — a 400 "Penalty is not enabled" means retry the same model without it.

    `duration` is stated in the prompt because without it models drift: on an 84s
    clip they emitted the back half of the timeline at 104-124s. Naming the exact
    length pins every timestamp inside the file.
    """
    prompt = PROMPT
    if duration:
        prompt += (f' ไฟล์เสียงนี้ยาว {duration:.1f} วินาทีพอดี '
                   f'ทุก timestamp ต้องอยู่ระหว่าง 0 ถึง {duration:.1f} '
                   f'ห้ามเกิน {duration:.1f} เด็ดขาด')
    base_cfg = {'temperature': 0, 'maxOutputTokens': 65536,
                'responseMimeType': 'application/json',
                'responseSchema': RESPONSE_SCHEMA}
    penalised = dict(base_cfg, frequencyPenalty=0.7, presencePenalty=0.4)
    audio = {'inlineData': {'mimeType': 'audio/wav',
                            'data': base64.b64encode(wav_path.read_bytes()).decode()}}
    for attempt, cfg in enumerate((penalised, base_cfg)):
        body = json.dumps({'contents': [{'parts': [{'text': prompt}, audio]}],
                           'generationConfig': cfg}).encode()
        req = urllib.request.Request(API.format(model=model), data=body, headers={
            'Content-Type': 'application/json', 'x-goog-api-key': key})
        try:
            with urllib.request.urlopen(req, timeout=560) as r:
                data = json.load(r)
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:300].decode('utf-8', 'replace')
            if attempt == 0 and exc.code == 400 and 'Penalty is not enabled' in detail:
                continue
            raise
        candidates = data.get('candidates') or []
        if not candidates:
            # Safety block / empty response: no 'candidates' key at all. Raise a
            # per-model error so the chain tries the next model instead of
            # KeyError-ing the entire batch to a halt.
            reason = (data.get('promptFeedback') or {}).get('blockReason', 'no candidates')
            raise ReplyUnusable(f'{model}: empty response ({reason})')
        candidate = candidates[0]
        text = ''.join(p.get('text', '') for p in candidate['content']['parts'])
        return text, candidate.get('finishReason'), data.get('usageMetadata', {})
    raise AssertionError('unreachable: both penalty variants rejected')


class QuotaExhausted(Exception):
    """Raised when every model in MODELS is out of free-tier quota."""


class ReplyUnusable(Exception):
    """Model replied but the payload cannot be parsed into segments.

    Treated as a per-model failure so the next model in MODELS gets a chance:
    a 65536-token repetition loop on one model must not abort the whole batch.
    """


def call_with_fallback(key, wav_path, duration=None):
    """Try each model in turn. 429 = daily quota spent; unusable reply = retry next."""
    last_error = None
    for model in MODELS:
        try:
            text, finish, usage = call(key, wav_path, model, duration)
        except urllib.error.HTTPError as exc:
            payload = exc.read()[:400].decode('utf-8', 'replace')
            if exc.code in (429, 500, 502, 503, 504):
                print(f'  {exc.code} on {model}; trying next model', flush=True)
                last_error = f'{model}: {payload[:200]}'
                continue
            raise
        except ReplyUnusable as exc:
            print(f'  empty/blocked response from {model}; trying next model', flush=True)
            last_error = str(exc)
            continue
        try:
            result = parse(text, finish)
        except AssertionError as exc:
            print(f'  unusable reply from {model} ({finish}); trying next model',
                  flush=True)
            last_error = f'{model}: {exc}'
            continue
        if not has_real_speech(result):
            print(f'  {model} returned no real speech (all uncertain/empty); '
                  'trying next model', flush=True)
            last_error = f'{model}: no real speech'
            continue
        usage['model_used'] = model
        return result, usage
    raise QuotaExhausted(f'all models unavailable: {last_error}')


def has_real_speech(result):
    """Reject lazy replies that mark every segment [ฟังไม่ชัด] or empty.

    Such a reply parses fine but is useless, and would otherwise be saved as
    "transcribed" — silently poisoning the whole run.
    """
    if not result.get('audio_available'):
        return True  # genuine "no audio attached" is a valid, explicit answer
    segments = result.get('segments') or []
    if not segments:
        return False
    for s in segments:
        text = (s.get('text') or '').replace('[ฟังไม่ชัด]', '').strip()
        if text:
            return True
    return False


def parse(text, finish, expected_seconds=None):
    if not text.strip():
        return {'audio_available': False, 'empty_reply': True, 'finish_reason': finish}
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.S) or re.search(r'(\{.*\})', text, re.S)
    assert match, f'no JSON in reply (finish={finish}): {text[:300]}'
    raw = match.group(1) or match.group(0)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # A reply cut off mid-array still carries usable leading segments; keep
        # only the complete ones and record that the tail was dropped.
        repaired = repair_truncated(raw)
        assert repaired is not None, f'unrepairable JSON (finish={finish}): {raw[:300]}'
        result = repaired
        result['truncated_reply_repaired'] = True
    if not result.get('audio_available'):
        return result
    segments = result.get('segments') or []
    assert isinstance(segments, list)
    for s in segments:
        assert isinstance(s.get('start'), (int, float)) and isinstance(s.get('end'), (int, float))
        assert s['start'] >= 0 and s['end'] >= s['start'] and isinstance(s.get('text'), str)
        s.setdefault('uncertain', False)
    if expected_seconds and segments and max(s['start'] for s in segments) > expected_seconds * 1.35:
        for s in segments:
            s['uncertain'] = True
        result['timing_drift'] = (f"max start {max(s['start'] for s in segments)}s vs manifest "
                                  f"{expected_seconds}s; all cues marked uncertain")
    result['segment_count'] = len(segments)
    return result


def parse_result_timing(result, expected_seconds):
    """Apply the manifest-duration drift check to an already-parsed result."""
    segments = result.get('segments') or []
    if segments and max(s['start'] for s in segments) > expected_seconds * 1.35:
        for s in segments:
            s['uncertain'] = True
        result['timing_drift'] = (f"max start {max(s['start'] for s in segments)}s vs manifest "
                                  f"{expected_seconds}s; all cues marked uncertain")
    return result


def repair_truncated(raw):
    """Salvage a JSON object whose trailing segment objects are incomplete."""
    depth = 0
    in_string = False
    escaped = False
    last_complete = None
    for i, ch in enumerate(raw):
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in '{[':
            depth += 1
        elif ch in '}]':
            depth -= 1
            if depth == 1 and ch == '}':
                last_complete = i
    if last_complete is None:
        return None
    for suffix in (']}', ']}', '}]}', ']}}}'):
        candidate = raw[:last_complete + 1]
        if candidate.rstrip().endswith(','):
            candidate = candidate.rstrip()[:-1]
        candidate = candidate + suffix
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and isinstance(parsed.get('segments'), list):
            return parsed
    return None


def main():
    key = api_key()
    rows = load_manifest()
    only = [int(x) for x in sys.argv[1:]] or None
    archive = RUN_ROOT / 'transcripts' / 'archive-proxy'
    archive.mkdir(parents=True, exist_ok=True)
    for row in rows:
        if only and row['index'] not in only:
            continue
        uid = row['id']
        dest = RUN_ROOT / 'transcripts' / f'{uid}.gemini.json'
        if dest.exists():
            existing = json.loads(dest.read_text(encoding='utf-8'))
            if existing.get('metadata', {}).get('route') == 'google-generativeai-direct':
                print(row['index'], uid, 'RESUME_SKIP', flush=True)
                continue
            archive.mkdir(parents=True, exist_ok=True)
            (archive / f'{uid}.json').write_bytes(dest.read_bytes())
        expected = (row['end'] - row['start']) / row['fps']
        wav = RUN_ROOT / 'audio' / f'{uid}.wav'
        assert wav.is_file() and wav.stat().st_size > 0
        t0 = time.monotonic()
        try:
            result, usage = call_with_fallback(key, wav, expected)
        except QuotaExhausted as exc:
            print(f"STOPPING at timeline {row['index']}: {exc}", flush=True)
            print('Re-run this script later to resume; completed files are skipped.', flush=True)
            raise SystemExit(3)
        result = parse_result_timing(result, expected)
        dest.write_text(json.dumps({
            'metadata': {'model': usage.get('model_used'), 'route': 'google-generativeai-direct',
                         'timeline_index': row['index'], 'timeline_id': uid,
                         'timeline_name': row['name'], 'expected_duration_seconds': expected,
                         'prompt_token_count': usage.get('promptTokenCount')},
            'duration_seconds': expected, 'gemini': result,
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        print(row['index'], uid, 'OK', result.get('segment_count', 0), 'segments',
              f"[{usage.get('model_used')}]", round(time.monotonic() - t0, 1), 's', flush=True)
        time.sleep(4)


if __name__ == '__main__':
    main()
