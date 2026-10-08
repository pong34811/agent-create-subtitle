# Gemini ASR pipeline for Thai subtitles

End-to-end route that produced 963 verified cues across 49 Resolve timelines.
Replaces the Whisper path for noisy game audio. Everything here was measured,
not inferred.

## Why not Whisper

Measured on the same 49 clips: `large-v3`, `large-v3-turbo`, `medium`, and
`bjak/distill-whisper-th-large-v3` all returned garbled or invented Thai;
several produced null timestamps or repetition loops. Gemini's audio input
handled the same files cleanly. Do not re-litigate this without new evidence.

## Model ranking (same audio, same prompt)

| Rank | Model | Note |
|---|---|---|
| 1 | `gemini-3.7-flash` | newest; best names + fluency |
| 2 | `gemini-3.6-flash` | equivalent in practice |
| 3 | `gemini-3.5-flash` | reliable workhorse |
| 4 | `gemini-3.5-flash-lite` | faster, slightly weaker |
| 5 | `gemini-3-flash-preview` | best of the older set |
| 6 | `gemini-3.1-flash-lite` | stable, but inserts Thai word spaces |
| 7 | `gemini-2.5-flash` | **inserts a space between EVERY Thai word** |
| — | `*-lite-latest` | last resort; may answer all-`[ฟังไม่ชัด]` stubs |

Free-tier quota is **per model per day**. Build the list newest-and-best first
and fall through on 429/5xx — a run legitimately mixes models.

## The prompt requirements that matter

1. **State the file's exact duration** and forbid timestamps past it:
   `ไฟล์เสียงนี้ยาว {d:.1f} วินาทีพอดี ทุก timestamp ต้องอยู่ระหว่าง 0 ถึง {d:.1f} ห้ามเกิน {d:.1f} เด็ดขาด`.
   Without this, models drift badly: an 84 s clip came back with its back half
   at 104-124 s. The text was correct and every timestamp was unusable.
2. Ask for **natural phrases**, not N-word chunks; forbid inserting text during
   silence; require `[ฟังไม่ชัด]` with a time range for anything unclear.
3. Demand **JSON only**, and pair it with `responseMimeType: application/json`
   plus a `responseSchema`. Free-form long Thai strings fail to parse.

## Four failure modes and their handling

**Character-repetition loops.** Long Thai transcripts make the model emit
`โอ้ยยยยย…` for hundreds of characters, eating the token budget so the JSON is
cut off (`finishReason: MAX_TOKENS`). Fix: send `frequencyPenalty: 0.7` and
`presencePenalty: 0.4`. **Not every model accepts them** — a 400
`"Penalty is not enabled for this model"` means retry the SAME model without
the penalties, then continue the chain.

**Truncated JSON.** Salvage complete leading segments by scanning the raw text
for the last balanced `}`; mark the result `truncated_reply_repaired`. Treat an
unsalvageable reply as a per-model failure so the next model gets a turn — do
not abort the batch.

**Missing `candidates`.** A safety block returns a payload with no `candidates`
key at all. `data['candidates'][0]` raises `KeyError` and kills the whole run.
Check `data.get('candidates')` and read `promptFeedback.blockReason`.

**Lazy all-uncertain replies.** A model can return valid JSON whose every
segment is `[ฟังไม่ชัด]`. That parses fine and would be saved as "transcribed",
silently poisoning the run. Gate it: strip `[ฟังไม่ชัด]` from each segment and
require at least one non-empty remainder, else try the next model.

## Long clips: chunk, do not trust the prompt alone

Clips over ~100 s still drifted even with the duration stated (116 s file came
back at 150 s). Split the audio at its **quietest seconds** near each 45 s
boundary, transcribe each chunk, then add the chunk offset back:

```bash
ffmpeg -y -v error -ss {start:.3f} -to {end:.3f} -i in.wav -ar 16000 -ac 1 part.wav
```

Cutting on a quiet second avoids slicing a word. Assert afterwards that no
segment ends past the file duration.

## Thai spacing normalisation (non-negotiable)

Thai has no inter-word spaces; several models add them anyway
(`แล้ว วัน นี้ ก็ ยัง`). Strip whitespace whose neighbours are BOTH in
`[\u0e00-\u0e7f]`:

```python
text = re.sub(r'(?<=[\u0e00-\u0e7f])\s+(?=[\u0e00-\u0e7f])', '', text)
```

This also collapses the repetition mark `ๆ` (`ฮ่าๆ ๆ` -> `ฮ่าๆๆ`) — correct for
the house style where NO space sits between Thai characters. Keep spaces around
Latin, digits and punctuation (`เกม Alien Shooter`, `555 ดี`).

**Apply it to every emitted cue, including merged ones.** A merge path that
concatenates two cues bypasses the per-group strip and reintroduces the spaces;
re-run the strip on the merged text (it is idempotent).

## Never silently drop text

Clamping a cue's start to the file duration collapses an overrunning cue to zero
length, and the empty cue is then discarded — the words vanish with no error.
Measured: text retention fell to 92 % before this was caught. Instead, pin the
overrunning cue to the tail, flag it `timestamp_beyond_duration`, and keep the
text. Assert retention is 100 % (compare normalised source vs cue characters)
as a standing gate.

## Pipeline commands

```bash
# 1. transcribe (resumable; skips timelines already on this route)
python scripts/gemini_direct_transcribe.py
python scripts/gemini_direct_transcribe.py 5 12 13      # specific indexes

# 2. long clips that still drift
python scripts/transcribe_chunked.py 13 41 46

# 3. build cues + SRT (needs the tokenizer venv)
./.venv-aomimama/Scripts/python.exe scripts/build_gemini_cues.py
```

## Provider comparison — all rejected, do not retry

Each failed for a structural reason, not a transient one:

| Provider | Reason |
|---|---|
| Groq `whisper-large-v3` | accepts audio, Thai output unreadable |
| OpenRouter | free tier has no real audio model (403 "agentic harnesses only"); the one that works needs a $0.50 minimum balance |
| Ollama Cloud | API has no audio input — every model answers "I cannot hear audio" |
| opencode zen | free tier is locked to the OpenCode app (403) |
| FreeLLMAPI (local) | audio never reaches the model |

Check a provider's **audio** capability before building anything on it: send one
short WAV and ask a question whose answer is only in the audio. A model that
did not receive the file will still answer confidently.
