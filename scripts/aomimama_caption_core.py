"""Conservative, text-preserving phrase drafts; all output needs human QC."""
import math
import logging
import re
import unicodedata
from pythainlp.tokenize import word_tokenize


def visible_glyphs(text):
    """Display-width heuristic, not a font measurement (Thai marks count zero)."""
    return sum(not unicodedata.category(c).startswith('M') for c in text)


def _aligned(segment):
    text = segment.get('text', '')
    pieces = segment.get('words') or []
    joined = ''.join(p.get('word', p.get('text', '')) for p in pieces)
    # A disagreement could omit a negation/name; require reconciliation rather
    # than choosing one conflicting source and silently losing the other.
    flags = []
    times = []
    if joined.strip() == text.strip() and pieces:
        text = joined
        occupied_end = -math.inf
        for piece in pieces:
            fragment = piece.get('word', piece.get('text', ''))
            start, end = float(piece['start']), float(piece['end'])
            if not (math.isfinite(start) and math.isfinite(end) and end >= start):
                raise ValueError('invalid fragment timing')
            count = sum(not c.isspace() for c in fragment)
            if count:
                if start == end and 'zero_duration_fragment_reconciliation' not in flags:
                    flags.append('zero_duration_fragment_reconciliation')
                    logging.getLogger(__name__).warning(
                        'zero-duration fragment timing reconciliation required in segment [%s, %s]',
                        segment['start'], segment['end'])
                if start < occupied_end and 'fragment_overlap_review' not in flags:
                    flags.append('fragment_overlap_review')
                occupied_end = max(occupied_end, end)
            i = 0
            for character in fragment:
                if character.isspace():
                    times.append(None)
                else:
                    times.append((start + (end-start)*i/count,
                                  start + (end-start)*(i+1)/count))
                    i += 1
    else:
        if pieces:
            raise ValueError('fragment/segment text mismatch; human reconciliation required')
        flags.append('missing_word_times_segment_fallback')
        start, end = float(segment['start']), float(segment['end'])
        if not (math.isfinite(start) and math.isfinite(end) and end >= start):
            raise ValueError('invalid segment timing')
        count = sum(not c.isspace() for c in text)
        i = 0
        for character in text:
            if character.isspace():
                times.append(None)
            else:
                times.append((start + (end-start)*i/count,
                              start + (end-start)*(i+1)/count))
                i += 1
    return text, times, flags


def _units(text, times, protected_terms):
    tokens = word_tokenize(text, engine='newmm', keep_whitespace=True)
    if ''.join(tokens) != text:
        raise ValueError('tokenizer changed source text')
    forbidden = set()
    for term in protected_terms:
        if not term:
            continue
        for match in re.finditer(re.escape(term), text):
            forbidden.update(range(match.start()+1, match.end()))
    units, pos = [], 0
    for token in tokens:
        end = pos + len(token)
        if not token:
            continue
        if token.isspace() and units:
            # Preserve the boundary in text, never in occupied time. Keeping it
            # attached also preserves protected phrases and Latin negations.
            units[-1]['text'] += token
            pos = end
            continue
        merge = bool(units) and (
            pos in forbidden or unicodedata.category(token[0]).startswith('M')
            or token.strip() == 'ๆ'
            or all(unicodedata.category(c).startswith('P') for c in token)
            or units[-1]['text'].strip().lower() in {'ไม่', 'ไม่ได้', 'อย่า', 'มิ', 'not', 'never'})
        spans = [t for t in times[pos:end] if t is not None]
        unit = {'text': token, 'start': min(t[0] for t in spans) if spans else None,
                'end': max(t[1] for t in spans) if spans else None}
        merge = merge and bool(spans) and units[-1]['start'] is not None
        if merge:
            units[-1]['text'] += token
            units[-1]['start'] = min(units[-1]['start'], unit['start'])
            units[-1]['end'] = max(units[-1]['end'], unit['end'])
        else:
            units.append(unit)
        pos = end
    return units


def validate(cues, duration):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('duration must be finite and positive')
    previous = 0.0
    for cue in cues:
        start, end = cue['start'], cue['end']
        if not (math.isfinite(start) and math.isfinite(end)
                and previous <= start < end <= duration):
            raise ValueError('invalid or overlapping cue timing')
        if not isinstance(cue['text'], str) or '\r' in cue['text'] or '\n' in cue['text']:
            raise ValueError('cue text must be a single-line string')
        if not cue['text'].strip():
            raise ValueError('empty cue')
        if not (round(previous*1000) <= round(start*1000) < round(end*1000)
                <= round(duration*1000)):
            raise ValueError('invalid timing at SRT millisecond precision')
        previous = end
    return True


def build_cues(raw, duration, *, max_glyphs=36, target_seconds=4.0,
               pause_seconds=0.5, protected_terms=()):
    """36 visible characters and ~4 seconds are soft drafting heuristics.

    No word-count limit, confidence gate, repetition removal or spelling fix.
    Add verified proper names to protected_terms (or raw['protected_terms']).
    Unbreakable phrases may exceed the heuristics; human QC is mandatory.
    """
    if max_glyphs < 1 or target_seconds <= 0 or pause_seconds <= 0:
        raise ValueError('phrase heuristics must be positive')
    cues = []
    names = tuple(protected_terms) + tuple(raw.get('protected_terms', ()))
    for segment in raw.get('segments', []):
        text, times, flags = _aligned(segment)
        if any(t is not None and (t[0] < 0 or t[1] > duration + 0.0005)
               for t in times):
            logging.getLogger(__name__).warning('out-of-bounds fragment timing; reconciliation required')
            raise ValueError('out-of-bounds fragment timing; human reconciliation required')
        if not text.strip():
            continue
        if any(c.isalpha() and not ('\u0e00' <= c <= '\u0e7f')
               and 'LATIN' not in unicodedata.name(c, '') for c in text):
            flags.append('suspect_foreign_script')
        if segment.get('avg_logprob', 0) < -1.5 or segment.get('no_speech_prob', 0) > 0.8:
            flags.append('low_confidence_review')
        units = _units(text, times, names)
        group = []

        def flush():
            if not group:
                return
            display = re.sub(r'\s+', ' ', ''.join(u['text'] for u in group)).strip()
            display = re.sub(r'\s+([,.;:!?…])', r'\1', display)
            if display:
                spoken = [u for u in group if u['text'].strip()]
                cues.append({'start': min(u['start'] for u in spoken),
                             'end': max(u['end'] for u in spoken),
                             'text': display, 'flags': list(flags)})
            group.clear()

        for unit in units:
            if any(u['text'].strip() for u in group) and unit['text'].strip():
                current = ''.join(u['text'] for u in group)
                previous = next((u for u in reversed(group) if u['text'].strip()), group[-1])
                pause = unit['start'] - previous['end']
                proposed = visible_glyphs(current + unit['text'])
                conjunction = unit['text'].strip() in {'แต่', 'เพราะ', 'ดังนั้น', 'แล้ว', 'แต่ถ้า'}
                sentence = bool(re.search(r'[.!?…]$', current.rstrip()))
                first = next(u for u in group if u['text'].strip())
                long = proposed > max_glyphs or unit['end']-first['start'] > target_seconds
                natural = conjunction and visible_glyphs(current) >= max_glyphs * 0.55
                spoken = [u for u in group if u['text'].strip()]
                # A point-aligned tail inside an occupied interval cannot become
                # its own zero-length SRT cue. Retain it in that phrase and flag
                # the raw alignment; never invent a new speech interval.
                contained_point = (unit['start'] == unit['end']
                                   and min(u['start'] for u in spoken) <= unit['start']
                                   <= max(u['end'] for u in spoken))
                if not contained_point and (pause >= pause_seconds or sentence or long or natural):
                    flush()
            group.append(unit)
        flush()
    repaired = []
    for cue in cues:
        cue['start'] = round(cue['start'] * 1000) / 1000
        rounded_end = round(cue['end'] * 1000) / 1000
        if rounded_end > duration:
            cue['flags'].append('timeline_edge_rounding_clamped')
        cue['end'] = min(rounded_end, duration)
        if repaired and cue['start'] < repaired[-1]['end']:
            previous = repaired[-1]
            glue = ' ' if (re.search(r'[A-Za-z0-9]$', previous['text'])
                           or re.match(r'[A-Za-z0-9]', cue['text'])) else ''
            previous['text'] += glue + cue['text']
            previous['start'] = min(previous['start'], cue['start'])
            previous['end'] = max(previous['end'], cue['end'])
            previous['flags'] = sorted(set(previous['flags'] + cue['flags'] + ['overlap_merged']))
        else:
            repaired.append(cue)
    for cue in repaired:
        if visible_glyphs(cue['text']) > max_glyphs:
            cue['flags'].append('glyph_heuristic_exceeded')
        if cue['end'] - cue['start'] > target_seconds:
            cue['flags'].append('duration_heuristic_exceeded')
    validate(repaired, duration)
    return repaired


def render_srt(cues):
    """Render only validated, non-overlapping millisecond-safe cues."""
    validate(cues, max((c['end'] for c in cues), default=1.0))

    def stamp(seconds):
        milliseconds = round(seconds * 1000)
        hours, milliseconds = divmod(milliseconds, 3600000)
        minutes, milliseconds = divmod(milliseconds, 60000)
        seconds, milliseconds = divmod(milliseconds, 1000)
        return f'{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}'

    return ''.join(f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}\n\n"
                   for i, c in enumerate(cues, 1))
