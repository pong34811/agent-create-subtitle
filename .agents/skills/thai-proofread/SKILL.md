---
name: thai-proofread
description: Proofread and correct Thai spelling, grammar, and tone markers.
version: 0.1.0
author: Hermes
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [thai, proofreading, editing, language, linguistics]
    category: creative
---

# Thai Proofreading and Correction

Proofread Thai text for spelling, grammar, punctuation, and tone consistency. Correct errors and explain each change in plain English.

**Key insight:** Thai has no word boundaries in the source text — spaces are optional between words — so spelling errors hide inside long unbroken strings. A correct proofread must segment the text into words, check each against a reference lexicon, and flag anything unmatched.

## When to Use

Load this skill whenever the user asks to:
- proofread, check, or correct Thai text
- "ตรวจสอบ ความถูกต้อง ภาษาไทย เเก้ไขคำผิด"
- find spelling or grammar mistakes in Thai
- fix typos, wrong tone markers, or malformed characters in Thai
- review Thai writing before publishing or sending

## Prerequisites

No installation required. The skill operates on text the user provides inline or via file path. For file input, use `read_file` to load it.

## How to Run

1. **Receive the text** — inline pasted text, or a file path. If a file, `read_file` it first.
2. **Segment the text** into words. Thai has no spaces between words, so segment using a dictionary-based approach (e.g. `pythainlp` if available, otherwise manual analysis).
3. **Check each word** against a Thai dictionary. Flag unmatched words as potential errors.
4. **Verify tone markers** — each syllable must carry exactly one vowel and one tone marker (or none for mid tone). Check for duplicate or misplaced markers (่ ้ ๊ ๋).
5. **Verify character validity** — strip invisible/bidi control characters before analysis.
6. **Report findings** — list each error with the wrong form, the correction, and the reason.
7. **Apply corrections** — use `patch` for file edits, or reply with the corrected text for inline input.

## Quick Reference

| Task | Tool |
|------|------|
| Read Thai text file | `read_file` |
| Segment Thai words | `pythainlp` (if installed) or manual analysis |
| Check spelling | Thai dictionary (e.g. `pythainlp` word list) |
| Edit file | `patch` |
| Verify result | `read_file` again |

## Procedure

1. Get the Thai text from the user (inline or file path).
2. If from a file: `read_file` the path.
3. Strip invisible Unicode control characters (zero-width, bidi embeddings) before analysis.
4. Segment the text into words.
5. Check each word against a Thai dictionary.
6. Verify tone markers per syllable.
7. Report each error: wrong form → correction → reason.
8. Apply corrections with `patch` (file) or present corrected text (inline).
9. Verify with `read_file` after patching.

## Pitfalls

- **No word boundaries:** Thai text often has no spaces between words. Do not assume a space-delimited split is correct — segment using a dictionary.
- **Tone marker collisions:** A syllable can only have one tone marker. Two markers (่ ้) on the same syllable is an error.
- **Mixed scripts:** Thai text may contain Latin characters, digits, or punctuation. Handle these separately — do not flag them as Thai errors.
- **Slang and informal words:** Not all Thai words exist in standard dictionaries. Flag as "unverified" rather than "error" when unsure.
- **Context-dependent corrections:** A word may be spelled correctly but used incorrectly (wrong homophone). Flag these as "check context" rather than auto-correcting.

## Verification

After correcting, re-read the file with `read_file` and confirm:
- No duplicate tone markers on any syllable.
- All flagged words have been addressed (corrected or explicitly left as-is with a reason).
- No invisible control characters remain.