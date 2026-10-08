"""Rule-based proofreading of Thai subtitle cues (no network, no model).

Finds what a script can find reliably; it cannot judge meaning or correct homophones.
Every finding is a *candidate* for a person to read, with a severity:

  error   cannot be right (foreign-script junk, doubled tone mark, orphan vowel,
          cue starting with a combining mark, empty text, leftover marker)
  warn    probably wrong (character stretched 4+ times, spaces between every Thai
          word, reading speed over MAX_CPS, words not in the PyThaiNLP dictionary)
  info    worth a glance (digits, Latin words, [ฟังไม่ชัด])

  python scripts/check_thai_text.py                 # all SRTs in the run
  python scripts/check_thai_text.py --only 36 8
  python scripts/check_thai_text.py --srt a.srt

Writes <run>/text-check.json. Exit 1 when any `error` exists. Needs pythainlp, so run
it with the .venv-aomimama interpreter (run_pipeline.py check does this).
"""
import argparse
import collections
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_subtitles_resolve import parse_srt  # noqa: E402

RUN_ROOT = Path(os.environ.get('AOMIMAMA_RUN_ROOT') or Path(__file__).resolve().parents[1] / 'runs' / 'aomimama-2026-09-p1')
VOCAB = Path(__file__).resolve().parents[1] / 'vocab' / 'games.json'
MAX_GLYPHS = 72         # twice the builder's per-cue target; beyond this a cue is a wall of text
MAX_CPS = 17.0          # Thai characters per second a viewer can read
TONES = '่้๊๋'
ABOVE_BELOW = 'ัิีึืฺุู็์ํ๎'
FOREIGN = re.compile(r'[ᄀ-ᇿ぀-ヿ㐀-鿿가-힯Ѐ-ӿ؀-ۿऀ-ॿ]')
STRETCH = re.compile(r'([ก-ฮะ-ฺเ-ๅ])\1{3,}')
COMBINING_START = re.compile(r'^[ัิ-ฺ็-๎]')


def thai_words():
    from pythainlp.corpus import thai_words as tw
    words = set(tw())
    if VOCAB.is_file():
        data = json.loads(VOCAB.read_text(encoding='utf-8'))
        terms = list(data.get('common', [])) + [x for g in data.get('games', []) for x in g['terms']]
        words |= {term for term in terms}
    return words


def check_text(text, duration, dictionary=None):
    """Return a list of (severity, code, detail) for one cue."""
    found = []
    plain = text.replace('[ฟังไม่ชัด]', '')
    if not text.strip():
        return [('error', 'empty_text', '')]
    if '[ฟังไม่ชัด]' in text:
        found.append(('info', 'uncertain_marker', ''))
    if FOREIGN.search(text):
        found.append(('error', 'foreign_script', ''.join(FOREIGN.findall(text))))
    if re.search(f'[{TONES}]{{2,}}', text) or re.search(f'[{TONES}][{ABOVE_BELOW}]?[{TONES}]', text):
        found.append(('error', 'doubled_tone_mark', ''))
    if COMBINING_START.match(plain.strip()):
        found.append(('error', 'starts_with_combining_mark', plain.strip()[:6]))
    if re.search(r'[เ-ไ](?=\s|$)', plain):
        found.append(('error', 'dangling_leading_vowel', ''))
    if STRETCH.search(plain):
        found.append(('warn', 'stretched_character', STRETCH.search(plain).group(0)))
    thai_tokens = re.findall(r'[฀-๿]+', plain)
    if len(plain.split()) >= 4 and len(thai_tokens) >= 4 and sum(len(t) <= 4 for t in thai_tokens) / len(thai_tokens) > 0.8:
        found.append(('warn', 'space_between_every_word', plain))
    chars = len(re.sub(r'\s', '', plain))
    if chars > MAX_GLYPHS:
        found.append(('error', 'cue_too_long', f'{chars} chars'))
    if re.search(r'\[[^\]]+\]', plain):
        found.append(('warn', 'bracketed_annotation', ' '.join(re.findall(r'\[[^\]]+\]', plain))))
    if duration > 0 and chars / duration > MAX_CPS:
        found.append(('warn', 'reading_speed', f'{chars / duration:.1f} chars/s'))
    if re.search(r'\d', plain):
        found.append(('info', 'has_digits', ''.join(re.findall(r'\d+', plain))))
    latin = re.findall(r'[A-Za-z]{2,}', plain)
    if latin:
        found.append(('info', 'latin_words', ' '.join(latin)))
    if dictionary is not None:
        from pythainlp.tokenize import word_tokenize
        unknown = [w for w in word_tokenize(plain, engine='newmm', keep_whitespace=False)
                   if re.fullmatch(r'[฀-๿]+', w) and len(w) > 1 and w not in dictionary
                   and not (w.endswith('ๆ'))]
        if unknown:
            found.append(('warn', 'not_in_dictionary', ' '.join(unknown)))
    return found


def check_cues(cues, dictionary=None):
    results = []
    for i, cue in enumerate(cues, 1):
        issues = check_text(cue['text'], cue['end'] - cue['start'], dictionary)
        if issues:
            results.append({'cue': i, 'start': round(cue['start'], 2), 'text': cue['text'],
                            'issues': [{'severity': s, 'code': c, 'detail': d} for s, c, d in issues]})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--only', type=int, nargs='+')
    parser.add_argument('--srt', type=Path)
    parser.add_argument('--srt-dir', type=Path, help='default: <run>/srt')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    dictionary = thai_words()
    if args.srt:
        findings = check_cues(parse_srt(args.srt), dictionary)
        print(json.dumps(findings, ensure_ascii=False, indent=2))
        sys.exit(1 if any(i['severity'] == 'error' for f in findings for i in f['issues']) else 0)
    rows = json.loads((RUN_ROOT / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    srt_dir = args.srt_dir or RUN_ROOT / 'srt'
    report, totals, cues_total = {}, collections.Counter(), 0
    for row in rows:
        if args.only and row['index'] not in args.only:
            continue
        srt = srt_dir / f"{row['id']}.draft.srt"
        if not srt.is_file():
            continue
        cues = parse_srt(srt)
        cues_total += len(cues)
        findings = check_cues(cues, dictionary)
        for f in findings:
            for i in f['issues']:
                totals[(i['severity'], i['code'])] += 1
        report[row['id']] = {'index': row['index'], 'name': row['name'], 'cues': len(cues), 'findings': findings}
    out = args.out or RUN_ROOT / 'text-check.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(report)} timelines, {cues_total} cues')
    for (sev, code), n in sorted(totals.items()):
        print(f'  {sev:<5} {code:<28} {n}')
    print('wrote', out)
    sys.exit(1 if any(sev == 'error' for sev, _ in totals) else 0)


if __name__ == '__main__':
    main()
