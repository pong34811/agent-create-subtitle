"""Build reviewed caption cues from Gemini segment transcripts.

Splits each Gemini speech segment into readable phrase cues without dropping or
reordering any word. Heuristics (soft, flagged when exceeded):
  - prefer a natural break at a real pause inside the segment
  - keep one line under ~36 visible glyphs (Thai combining marks count 0)
  - do not sever protected names, negations, or `ๆ`

Writes reviewed/<id>.json (approved=false) and srt/<id>.draft.srt. No Resolve access.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

from pythainlp.tokenize import word_tokenize

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thai_text import clean_cue_text, collapse_stutter  # noqa: E402

# Override with AOMIMAMA_RUN_ROOT; default resolves from this script, not a fixed drive path.
import os as _os
RUN_ROOT = Path(_os.environ.get('AOMIMAMA_RUN_ROOT') or Path(__file__).resolve().parents[1] / 'runs' / 'aomimama-2026-09-p1')
MAX_GLYPHS = 36
MIN_GAP = 0.05
NEGATIONS = {'ไม่', 'ไม่ได้', 'อย่า', 'มิ', 'ไม่ต้อง', 'ไม่เคย'}
PROTECTED = (
    'Alien Shooter', 'alien shooter', 'Minecraft', 'League of Legends',
    'Last Hope', 'Hard Mode', 'Copper Golem', 'Creeper', 'Windows XP',
)


def glyphs(text):
    return sum(0 if unicodedata.category(c).startswith('M') else 1 for c in text)


def protected_ranges(text):
    forbidden = set()
    for term in PROTECTED:
        for m in re.finditer(re.escape(term), text, re.I):
            forbidden.update(range(m.start() + 1, m.end()))
    return forbidden


def split_units(text):
    """Word tokens with char offsets, whitespace preserved as attachable glue."""
    tokens = word_tokenize(text, engine='newmm', keep_whitespace=True)
    assert ''.join(tokens) == text, 'tokenizer changed source text'
    forbidden = protected_ranges(text)
    units, pos = [], 0
    for tok in tokens:
        end = pos + len(tok)
        if tok.isspace():
            if units:
                units[-1]['text'] += tok
                units[-1]['chars'].append((pos, end))
            pos = end
            continue
        merge = bool(units) and (
            pos in forbidden
            or unicodedata.category(tok[0]).startswith('M')
            or tok.strip() == 'ๆ'
            or all(unicodedata.category(c).startswith('P') for c in tok)
            or units[-1]['text'].strip() in NEGATIONS)
        if merge:
            units[-1]['text'] += tok
            units[-1]['chars'].append((pos, end))
        else:
            units.append({'text': tok, 'chars': [(pos, end)]})
        pos = end
    return units


def split_segment(segment, next_start):
    """Return cue dicts for one Gemini segment, times interpolated by glyph share."""
    text = clean_cue_text(segment['text'])
    if not text:
        return []
    start, end = float(segment['start']), float(segment['end'])
    units = [u for u in split_units(text) if u['text'].strip()]
    if not units:
        return []
    if next_start is not None:
        end = min(end, next_start - MIN_GAP)
    if end <= start:
        end = start + 0.4
    total = sum(max(1, glyphs(u['text'])) for u in units)
    groups, group = [], []
    for unit in units:
        candidate = ''.join(u['text'] for u in group) + unit['text']
        if group and glyphs(candidate) > MAX_GLYPHS:
            groups.append(group)
            group = []
        group.append(unit)
    if group:
        groups.append(group)
    cues, consumed = [], 0.0
    for group in groups:
        weight = sum(max(1, glyphs(u['text'])) for u in group)
        st = start + (end - start) * consumed / total
        consumed += weight
        en = start + (end - start) * consumed / total
        display = re.sub(r'\s+', ' ', ''.join(u['text'] for u in group)).strip()
        display = re.sub(r'\s+([,.;:!?…])', r'\1', display)
        display = strip_thai_internal_spaces(display)
        if display:
            cues.append({'start': round(st, 3), 'end': round(max(en, st + 0.4), 3),
                         'text': display, 'source_segment': segment.get('start'),
                         'gemini_uncertain': bool(segment.get('uncertain')),
                         'flags': []})
    return cues


def build(transcript, duration):
    segments = sorted(transcript['gemini'].get('segments') or [],
                      key=lambda s: s['start'])
    cues = []
    for i, seg in enumerate(segments):
        next_start = segments[i + 1]['start'] if i + 1 < len(segments) else None
        cues.extend(split_segment(seg, next_start))
    cues.sort(key=lambda c: c['start'])
    overrun = [c for c in cues if c['start'] >= duration]
    out = []
    for cue in cues:
        # The model sometimes reports timestamps past the end of the file (e.g. a
        # segment starting at 148s in a 116s clip). Clamping the START to the file
        # duration collapsed the cue to zero length and the text was then dropped.
        # Instead: keep every word, pin the overrunning cue to the tail, and flag it.
        if cue['start'] >= duration:
            cue['flags'].append('timestamp_beyond_duration')
            cue['start'] = max(0.0, duration - 2.0)
            cue['end'] = duration
        cue['start'] = max(0.0, min(cue['start'], duration))
        cue['end'] = max(0.0, min(cue['end'], duration))
        if out and cue['start'] < out[-1]['end']:
            # Overlapping cues happen when the model's segment boundaries touch.
            # Clipping the start keeps the phrase split intact; only merge when the
            # remaining slot is too short to display, which otherwise produced
            # 270-glyph blobs.
            room = out[-1]['end'] - cue['start']
            if cue['end'] - cue['start'] - room >= 0.2:
                cue['start'] = out[-1]['end'] + MIN_GAP
                cue['flags'].append('start_clipped_to_previous')
            else:
                merged = collapse_stutter(strip_thai_internal_spaces(
                    out[-1]['text'] + ' ' + cue['text']))
                if glyphs(merged) <= MAX_GLYPHS * 1.5:
                    out[-1]['text'] = merged
                    out[-1]['end'] = max(out[-1]['end'], cue['end'])
                    out[-1]['flags'].append('overlap_merged')
                    continue
                # Merging many overlapping segments produced a 290-glyph wall of
                # text. Keep the words as their own cue, placed right after the
                # previous one (late, but readable) and flag the timing.
                cue['start'] = out[-1]['end'] + MIN_GAP
                cue['end'] = min(duration, max(cue['end'], cue['start'] + 0.6))
                cue['flags'].append('forced_after_previous')
        if cue['end'] - cue['start'] < 0.3:
            cue['end'] = min(duration, cue['start'] + 0.4)
        if cue['text'].strip() and cue['end'] > cue['start']:
            # Merged text bypassed the per-group strip in split_segment; re-apply
            # here so every emitted cue is space-clean (the function is idempotent).
            cue['text'] = strip_thai_internal_spaces(cue['text'])
            if glyphs(cue['text']) > MAX_GLYPHS:
                cue['flags'].append('glyph_heuristic_exceeded')
            out.append(cue)
    return out, overrun


def strip_thai_internal_spaces(text):
    """Remove spaces between Thai characters. Thai is written without word spaces.

    Any whitespace whose neighbours are both Thai-range characters is dropped,
    which includes the repetition mark ๆ (U+0E46) and combining marks. Spaces next
    to Latin words, digits or punctuation are kept ("เกม Alien Shooter", "555 ดี").
    """
    thai = r'\u0e00-\u0e7f'
    return re.sub(rf'(?<=[{thai}])\s+(?=[{thai}])', '', text)


def srt_time(t):
    ms = max(0, int(round(t * 1000)))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def main():
    only = [int(x) for x in sys.argv[1:]] or None
    rows = json.loads((RUN_ROOT / 'manifest.json').read_text(encoding='utf-8'))['timelines']
    summary = []
    for row in rows:
        if only and row['index'] not in only:
            continue
        uid = row['id']
        src = RUN_ROOT / 'transcripts' / f'{uid}.gemini.json'
        if not src.exists():
            print(row['index'], uid, 'NO_TRANSCRIPT', flush=True)
            continue
        transcript = json.loads(src.read_text(encoding='utf-8'))
        if not transcript['gemini'].get('audio_available'):
            print(row['index'], uid, 'NO_SPEECH_OR_BLOCKED', flush=True)
            continue
        duration = transcript['duration_seconds']
        cues, overrun = build(transcript, duration)
        reviewed = RUN_ROOT / 'reviewed' / f'{uid}.gemini.json'
        reviewed.parent.mkdir(parents=True, exist_ok=True)
        reviewed.write_text(json.dumps({
            'timeline_id': uid, 'timeline_name': row['name'], 'approved': False,
            'source_model': transcript['metadata']['model'], 'duration_seconds': duration,
            'cues': cues, 'qc_required': True, 'status': 'unreviewed_draft',
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        srt = RUN_ROOT / 'srt' / f'{uid}.draft.srt'
        srt.parent.mkdir(parents=True, exist_ok=True)
        srt.write_text(''.join(
            f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n\n"
            for i, c in enumerate(cues, 1)), encoding='utf-8-sig')
        flagged = sum(1 for c in cues if c['flags'])
        summary.append({'index': row['index'], 'cues': len(cues), 'flagged': flagged,
                        'overrun_segments': len(overrun)})
        if overrun:
            print(row['index'], uid, 'WARNING: segments past file end:',
                  [round(c['start'], 1) for c in overrun], flush=True)
        print(row['index'], uid, 'CUES', len(cues), 'flagged', flagged, flush=True)
    total = sum(s['cues'] for s in summary)
    print('TOTAL_TIMELINES', len(summary), 'TOTAL_CUES', total, flush=True)


if __name__ == '__main__':
    main()
