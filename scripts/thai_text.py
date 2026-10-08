"""Deterministic clean-up of Thai subtitle text. Standard library only.

These are fixes a script can make without hearing the audio. Anything that needs
judgement about meaning (homophones, names, mis-heard words) is left alone and
reported by scripts/check_thai_text.py instead.
"""
import re

UNCERTAIN = '[ฟังไม่ชัด]'
_DECOMPOSED_SARA_AM = re.compile('([่-๋]?)ํา')
# a short unit (a vowel sound like อื้อ, a laugh like ฮ่า) repeated 4+ times in a row
_STUTTER = re.compile(r'([ก-๎]{2,6}?)\1{3,}')


def fix_sara_am(text):
    """ทํา (U+0E4D + U+0E32) -> ทำ (U+0E33). Some ASR output decomposes sara am.

    It looks identical on screen but breaks search, spell-checkers and some fonts.
    A tone mark that sits between the consonant and the vowel is kept in place.
    """
    return _DECOMPOSED_SARA_AM.sub(lambda m: m.group(1) + 'ำ', text)


def collapse_stutter(text, keep=2):
    """'อื้ออื้ออื้ออื้ออื้อ' -> 'อื้ออื้อ'. A subtitle needs the sound, not 20 copies of it."""
    return _STUTTER.sub(lambda m: m.group(1) * keep, text)


def strip_uncertain(text):
    """Remove the [ฟังไม่ชัด] placeholder; it must never be shown to a viewer."""
    return re.sub(r'\s+', ' ', text.replace(UNCERTAIN, ' ')).strip()


def clean_cue_text(text):
    """Full deterministic pass used when building cues. Returns '' if nothing is left."""
    text = fix_sara_am(text)
    text = strip_uncertain(text)
    return collapse_stutter(text)
