"""Debug: dump the raw Gemini reply for timeline 2 without touching artifacts."""
import base64, json, urllib.request
from pathlib import Path

# Override with AOMIMAMA_RUN_ROOT; default resolves from this script, not a fixed drive path.
import os as _os
RUN_ROOT = Path(_os.environ.get('AOMIMAMA_RUN_ROOT') or Path(__file__).resolve().parents[1] / 'runs' / 'aomimama-2026-09-p1')
row = json.loads((RUN_ROOT / 'manifest.json').read_text(encoding='utf-8'))['timelines'][1]
wav = RUN_ROOT / 'audio' / f"{row['id']}.wav"
payload = base64.b64encode(wav.read_bytes()).decode()
prompt = Path('C:/Users/warit/Desktop/agent-create-subtitle/scripts/gemini_batch_transcribe.py').read_text(encoding='utf-8')
p_start = prompt.find("PROMPT = ('") + len("PROMPT = ('")
p_end = prompt.find("')", p_start)
PROMPT = prompt[p_start:p_end].replace('\\n', '\n').replace("', '\n", '\n').replace("' '", '')
body = json.dumps({
    'model': 'google/gemini-3.8-flash',
    'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': PROMPT},
        {'type': 'file', 'file': {'filename': wav.name,
                                  'file_data': 'data:audio/wav;base64,' + payload}}]}],
    'max_tokens': 16000,
}).encode()
req = urllib.request.Request('http://127.0.0.1:8645/v1/chat/completions', data=body,
                             headers={'Content-Type': 'application/json', 'Authorization': 'Bearer local-proxy'})
with urllib.request.urlopen(req, timeout=560) as r:
    data = json.load(r)
msg = data['choices'][0]['message']
out = RUN_ROOT / 'review' / 'timeline2-raw-reply.txt'
out.write_text(msg.get('content') or '(empty content)', encoding='utf-8')
print('CONTENT_LEN', len(msg.get('content') or ''), 'REFUSAL', msg.get('refusal'), 'finish', data['choices'][0].get('finish_reason'))
print(out)
