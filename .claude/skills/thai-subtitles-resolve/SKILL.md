---
name: thai-subtitles-resolve
description: Thai audio to Resolve subtitle tracks via Gemini ASR.
---

# Thai subtitles into Resolve timelines

Use when adding Thai (or any non-spaced-script) subtitles to DaVinci Resolve
timelines from audio: Whisper ASR -> N-words-per-caption SRT -> scripted import
to subtitle tracks, verified by readback.

Built and proven on Resolve Studio 21.1.0.17, RTX 4060, 12 gameplay shorts.

## Subtitle-track-only workflow

Create and continue dialogue captions only on native Resolve Subtitle tracks.
Do not substitute Text+ / TextPlus, Fusion titles, or text clips on video
tracks, even when their styling is easier. The user wants the existing
Subtitle-track workflow preserved. Treat historical Text+ captions as legacy
content, not permission to create more; an authorized migration must preserve
all caption text and timing and leave unrelated titles and overlays alone.
For authorized legacy migration or interrupted-work verification, read
`references/native-caption-migration.md` before any mutation.
If the user handles fonts/styles, stop at verified cue insertion; do not apply
an old font/style plan, copy a style blob, or write SQL on their behalf.

## ASR route: Gemini, not Whisper

**On real Thai gameplay audio, Whisper is unusable — do not start there.**
Measured on 49 clips (Resolve Studio 21.1.0.17): faster-whisper large-v3,
large-v3-turbo, medium, and `bjak/distill-whisper-th-large-v3` all produced
garbled or hallucinated Thai, and Groq-hosted `whisper-large-v3` turned
"ฮัลโหล" into "เหลื่อการพังสะพาน". Gemini's audio input transcribed the same
files cleanly, including game names (Alien Shooter, Minecraft, Resident Evil).

For the working route — model ranking, the prompt that stops timestamp drift,
chunked transcription for long clips, failure handling, and the provider
comparison — read `references/gemini-asr-pipeline.md`.

The Whisper-specific material below is kept because its findings still hold
when Whisper IS the right tool (clean studio speech, CJK, subtitle timing).

## The three findings that matter

### 1. SRT import IS scriptable (most guides, and this repo's own api_truth, said it is not)

```python
items = mp.ImportMedia([srt_path])      # -> MediaPoolItem, Type == "Subtitle"
tl.AddTrack("subtitle")                 # MUST exist first
mp.AppendToTimeline([{"mediaPoolItem": items[0]}])
```

Traps, each of which makes it look broken:

- **The target timeline must be CURRENT first.** `AddTrack` and
  `AppendToTimeline` act on the ACTIVE timeline, not on the object you called
  them through. Without `project.SetCurrentTimeline(tl)` the track is added to
  whatever timeline happens to be active and the append lands nowhere. First
  measured attempt placed 0 of 3 for exactly this reason:

  ```python
  project.SetCurrentTimeline(tl)
  tl = project.GetCurrentTimeline()   # re-fetch; the handle you held may be stale
  ```

- `AppendToTimeline` returns a **non-empty list while placing nothing** when the
  timeline has no subtitle track. Add the track first.
- Appending to a track that already holds captions **stacks the file after
  them** instead of using its own timecodes. Never append twice to one track.
- `Timeline.ImportIntoTimeline(srt)` returns `False` — it is AAF-only.
- The import interpreter must be one Resolve's `fusionscript.dll` accepts
  (`py -3.12` here). A venv that holds your tokenizer deps may load the module
  but fail at the DLL — dry run works, `--apply` does not. See Environment.

Verify by readback: `GetItemListInTrack("subtitle", idx)`, compare item count
and `GetStart()/fps` against the SRT. Expect sub-frame drift (<0.5 frame).

### 1b. Re-importing a CORRECTED SRT: ImportMedia is path-cached

Fixing an SRT and re-importing the same path **silently does nothing** — the
media pool returns the item parsed at first import, and reports success.
Measured: bin stayed at 12 items instead of 24, timeline kept the old text.
Deleting the subtitle track does not help; the stale pool item is the source.

So a replace path must do all three, in order:

```python
for idx in range(tl.GetTrackCount("subtitle"), 0, -1):
    tl.DeleteTrack("subtitle", idx)               # 1. old track
stale = [c for c in bin.GetClipList()
         if c.GetClipProperty("File Path") == srt_path]
mp.DeleteClips(stale)                             # 2. cached pool item
mp.ImportMedia([srt_path])                        # 3. now re-reads disk
```

Never trust the item count printed right after append — read it back in a
separate pass. After replacing a track, reapply any whole-track subtitle style
only when style work is authorized; otherwise report that it is deferred.
SRT import/AddTrack recreates the track's style blob as an unstyled stub. Verify
both cue content/timing and style after the replacement. And when a re-run writes
a per-item result file, MERGE with the previous record instead of overwriting, or
a targeted fix erases the verified state of every timeline it did not touch.

### 2. Whisper's Thai "words" are sub-character fragments

Do **not** treat `word_timestamps` entries as words for non-spaced scripts. Real
measured output: `'เล' 'ื' 'อ' 'ด' 'น' '้' 'อย'` — 48 tokens for 65 characters,
bare consonants and floating vowel marks. Tokenizing each fragment separately
yields garbage.

What holds: **concatenating a segment's tokens reproduces the segment text
exactly**. So build a character-level time index:

1. join tokens, recording each CHARACTER's time span (interpolate across token);
2. `pythainlp.tokenize.word_tokenize(text, engine="newmm")` for real words;
3. each word takes the start of its first char and end of its last.

Then merge back tokenizer artefacts that would steal a caption slot: a lone Thai
character (`แม่ง` -> `แม่`+`ง`) and the repetition mark `ๆ`. Count block size in
list entries, **never** by `line.split()` — a rendered `ได้ ๆ` is one word.

**Render the words JOINED, with no separator.** The N-word grouping is a TIMING
decision (how much text appears at once); it is not something to spell out on
screen. Thai has no inter-word space, so emitting `ถ้า จำ ไม้` looks broken to a
Thai viewer even though it makes the grouping visible — the user will ask for it
to be removed. Insert a space only where one side of the boundary is Latin
(`คำ likes ด้วย`), and never before punctuation. A pre-existing space around `ๆ`
from the ASR text is correct Thai typography; leave it.

### 3. Game audio makes Whisper hallucinate across languages

Symptoms in real output: `El操าnament`, `まりAR`, `Mensch`, `participant`.
Detect numerically instead of by eye:

```python
foreign_ratio = non_thai_alpha / (thai + non_thai_alpha)   # > 0.12 is suspect
avg_logprob   = mean(seg.avg_logprob)                      # < -1.5 is suspect
```

Remedy — re-extract voice-band audio and retranscribe:
`highpass=f=80, lowpass=f=7000, afftdn=nf=-25, dynaudnorm=f=150:g=15:p=0.7`

**Choose per clip part, not globally.** Measured: one part went -2.25 -> -0.32
(20 -> 110 words), another went -0.87 -> -1.68. Blanket-swapping trades a clean
transcript for a degraded one. Select on `avg_logprob` and record the decision.

English that looks wrong may be real: RoV/LoL announcer lines (`First blood`,
`Let death bloom`) are genuine game audio, not hallucination. Listen before
stripping.

### 3b. A single foreign GLYPH survives every segment-level gate

Segment-level ratio checks cannot see one bad character inside otherwise-clean
Thai: `มันมี를..`, `เต็ม膈ับ`, `อ่าฮะей`, `เอ่업อ`. These reach the screen.

Filter by SCRIPT, never by confidence. Measured on this material, 180 word
tokens sit below p=0.05 and most are valid Thai fragments (`'ถ'` p=0.003,
`'ไม'` p=0.006) — a probability gate deletes real speech. Foreign glyphs are
unambiguous instead: `를`/`업`/`ей` all p=0.000.

Drop Hangul/Han/Kana/Cyrillic/Arabic/Devanagari; KEEP Latin (game audio).
Do it inside the character-time-index pass so the character and its time span
die together — removing from the text alone shifts every later timing.

Removing a glyph from mid-word leaves debris the tokenizer then mis-splits, so
also rejoin to the previous word any token that (a) is a lone Thai character,
(b) starts with a combining vowel/tone mark `[\u0E31\u0E34-\u0E3A\u0E47-\u0E4E]`
(`เต็ม膈ับ` -> `เต็ม` + `ับ`), or (c) is pure punctuation (`..`).

## Transcribe settings that worked

```python
model.transcribe(wav, language="th", word_timestamps=True, beam_size=5,
    temperature=[0.0,0.2,0.4,0.6,0.8,1.0],
    condition_on_previous_text=False,   # stops hallucination loops on game audio
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms":400, "speech_pad_ms":200})
```

## Caption timing for short-form

- `MAX_DISPLAY_S ≈ 2.2` — Whisper stretches a trailing token over silence, which
  parks a 3-word caption ~5 s and reads as a stuck subtitle.
- Clamp order: display cap, then `next_start - min_gap`, then timeline end.
- `MIN_GAP_S ≈ 0.034` (2 frames @60) so blocks do not visually merge.
- Break early on a pause `>= 0.7 s` — otherwise captions straddle sentences.
- Never drop words to fit; flag low confidence instead and report it.
- Apply these limits to newly authored cues. Do not shorten or split legacy
  cues in a preserve-text-and-timing migration; report exceptions instead.

## Curating existing multi-pass ASR without a new model run

- Align independent full-stream and voice-filtered passes with the short-window pass on one absolute clip clock. Short windows may overlap; deduplicate shared speech instead of captioning it twice. Inspect character/word times only after choosing a corroborated phrase; a segment's outer boundary may stretch across silence.
- Treat repeated tokens and implausibly long segments as hallucination, not evidence of speech. Preserve only phrases corroborated by another pass, using any long-source SRT as a weak cross-check; omit unresolved spans and log them rather than inventing full coverage.
- Use contact frames for game context, never as evidence for words. Preserve English only when clear; record uncertain name spellings and exclude stray foreign-script glyphs.
- Keep curation separate from Resolve when only SRT sidecars are requested. Reparse the written UTF-8 SRTs to assert consecutive indices, non-overlapping one-line cues, a brief gap, short display duration, no foreign junk, and the final cue before `end_frame / fps`; report omitted intervals and uncertain terms per clip.

## Timebase

Whisper time is relative to the extracted WAV. WAV t=0 is the clip's
`tl_start_frame`, so `timeline_time = wav_time + tl_start_frame/fps`. Multi-clip
timelines need this or part 2 lands at zero. Get ranges from
`GetLeftOffset()`/`GetDuration()` per timeline item, and check
`GetProperty("Speed")` — a retimed clip breaks the linear mapping.

## Environment (Windows)

- **Resolve scripting needs its own interpreter.** Verified: `py -3.12` loads
  `fusionscript.dll`; a Python 3.11 venv holding `pythainlp` does not
  (`ModuleNotFoundError: DaVinciResolveScript` even with `sys.path` set). Keep
  tokenizer work and Resolve work in separate interpreters.
- `scriptapp('Resolve')` intermittently returns `None` on a cold connection.
  Retry in a loop (10 attempts, 5 s apart) — it succeeds on retry every time.
- **Guard the project before writing.** A probe can leave Resolve showing
  "Untitled Project" with 0 timelines. Refuse to mutate unless
  `GetCurrentProject().GetName()` is the expected project, and re-open it with
  `pm.GotoRootFolder()` -> `OpenFolder(...)` -> `LoadProject(name)` when wrong.
- faster-whisper/ctranslate2 needs CUDA DLLs registered **before** import.
  On Windows with a CUDA-enabled PyTorch wheel, `torch/lib` can contain the
  required `cublas64_12.dll`/cuDNN DLLs: import torch, call
  `os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), 'lib'))`,
  and prepend that directory to PATH. Alternatively register the installed
  `site-packages/nvidia/*/bin` pip-wheel directories. Probe model loading before
  a long batch; ordinary `torch.cuda.is_available()` alone proves too little.
- Resolve's own python bridge: set `RESOLVE_SCRIPT_API`/`RESOLVE_SCRIPT_LIB`,
  add the install dir via `add_dll_directory`, then `import DaVinciResolveScript`.
- Probe API presence with `name in dir(obj)` — `hasattr` returns True for every
  name on a Resolve object, real or invented.
- Activate each timeline before capturing its playhead: on observed 21.1.0.17,
  an inactive `Timeline.GetCurrentTimecode()` returns the active timeline's
  timecode. Never restore an inactive-read value onto another timeline. Wait
  after activation and read its own timecode; capture the current active state
  again when resuming instead of restoring stale session state.
- `OpenPage()` can return True before `GetCurrentPage()` changes. Wait and read
  back the requested page before final save/state assertions, and serialize
  live Resolve calls; a successful render can otherwise be followed by a false
  restoration failure.
- Resolve constants (`resolve.SUBTITLE_LANGUAGE`, `AUTO_CAPTION_THAI`) are
  absent from `dir()` yet readable via `getattr` — absence from dir() is not
  absence.

## Safety

Source media is read-only: ffmpeg decodes the original and writes NEW scratch
WAVs. Only project-database state changes (subtitle track + items + one media
pool item per SRT). Create/delete a scratch timeline only within explicit scope;
when extra timelines are prohibited, use a verified DRP backup instead.
Skip timelines that already have a subtitle track unless `--replace` is passed,
so a re-run cannot silently double captions.

### Copying a user-approved subtitle-track style

Direct database writes require explicit authorization for that operation;
permission to insert subtitles or change a font is not permission to write SQL.

Read before writing: inspect one reference track in Resolve's Track Inspector and compare the `EffectFiltersBA` keyed-dict value on every target `Sm2TiTrack.FieldsBlob` (`Type=2`). If all values are byte-identical, the whole-track style already matches; leave the database untouched. Different non-style keys (such as `ExcludeTrackFromSequenceCaching`) do not require replacement. Qt's QFont descriptor `pointSize` is **not** the Inspector Size (e.g. an 8.14286 descriptor displayed as Size 58), so do not set an Inspector size by assigning that number to `pointSize`. Resolve's Stroke checkbox is labeled **Outside Only**, not Outline Only: checked keeps the white fill and places the stroke outside the glyph.

When no supported scripting setter exposes Subtitle Track Inspector styling,
use the **current** saved track's style blob, not an older template: a UI edit
of Position Y changes the live `Sm2TiTrack.FieldsBlob`. First export a `.drp`,
verify target timeline IDs/counts/texts and the reference track's approved GUI
position, save and **close the Resolve project**, then take a SQLite backup.
Update only the exact new subtitle-track rows (`Type=2`) with a transaction;
never alter source media or unrelated tracks. Reopen and save the project, then
verify every target cue/text/frame and exact blob equality with the reference.
If the style blob has an unexpected shape or the project cannot close, stop
before writing SQL; do not assume a stale style template still has the user's
latest Y value.

### Subtitle track presets (Inspector > Load Preset) are just style bytes

No scripting API loads a subtitle-track preset (21.1.0.17). User presets live in
`<library>/Resolve Projects/Users/guest/User.db`, `SM_User.FieldsBlob` -> QVariantMap
key `SubtitlePresetsBA` = `<u32 1><u32 n>{QString name, QByteArray style}`. The style
bytes are IDENTICAL to the track's `EffectFiltersBA` in `Sm2TiTrack.FieldsBlob`
(Type=2), so "Load Preset" = copy bytes into that key (verified on 60 real tracks).
Blobs are big-endian QDataStream: `<u32 1><u32 count>{QString key, u32 type, u8 null, value}`
(types seen: 1 bool, 2 int, 12 bytearray). Unstyled tracks lack `EffectFiltersBA`; append it.
Timeline `GetUniqueId()` == `Sm2Timeline.Sm2Timeline_id`. Active library path comes from
`Preferences/dblist.conf` (drive colon stripped: `G\My Drive\...`). Projects can sit in
nested folders under `Projects/`. Style payload is `00000002 <len> 0x81 + zstd`; Python 3.14
`compression.zstd` decodes it (protobuf with a QFont string). For applying
presets by orientation (Mitr Font = 16:9, Mitr-short-001 = 9:16), load the
`resolve-mitr-subtitle-presets` skill.

## Adding SFX / BGM / reaction GIFs to the same timelines

The same machinery extends to sweetening. Verified on Studio 21.1.0.17:

**Rapid AppendToTimeline CRASHES Resolve.** A tight loop placing 3 SFX + 1 BGM
+ 1 GIF killed the process mid-sequence. Every single call was proven
survivable in isolation, so the trigger is the RATE — Resolve is still saving
the project and writing timeline backups when the next append lands
(`davinci_resolve.log` shows back-to-back "Start saving project"). Sleep ~0.35s
between appends and print progress per item so a crash names the step.

**Do not trust the crash log's last lines.** Here they read `Video decoder is
destroyed with live file handle` + `Unsupported clip format for audio decoding
... GIF`, which framed the GIF as the culprit. The identical pair appears in
runs that succeed. Isolate by re-running each operation separately against a
DUPLICATE of a real timeline.

**Isolation probes must reproduce the real condition.** A first probe placed a
GIF over an empty V1 and "passed", proving nothing — the media pool's video
masters live in a SUBFOLDER, so a root-only scan found no spine. Duplicate an
actual timeline (`DuplicateTimeline`) instead of assembling a fake one.

**Audio level is `AudioVolume`, in dB** — `Volume`, `Gain`, `Level`,
`AudioGain`, `ClipVolume` all return False from both Set and Get, looking like
a working call that did nothing. `GetProperty()` with NO arguments enumerates
the real keys; do that before guessing. `SetTrackProperty` does not exist, so
level is per item, and there is no keyframe/fade API — a music bed can only be
a flat level (~-26 dB under speech), never ducked.

**GIFs**: `ImportMedia` accepts them, Resolve conforms the frame rate itself
(47 frames @25fps -> 112 @60fps), but they carry **no alpha** — a full-frame
placement is an opaque rectangle. Scale to ~0.25 via `ZoomX/ZoomY` and place
with `Pan/Tilt` (pixels from centre). Check a rendered frame: on gameplay the
right side is usually HUD (clock/score/FPS) and the far left is the minimap.

**Choose cues from evidence, not randomly.** Merge energy peaks (RMS rise above
the clip's OWN rolling baseline — a fixed dB gate mis-fires across clips that
differ by 10 dB) with the subtitle words at that moment for mood. Require a
large rise (~25 dB) before placing anything on a peak with no mood word, or
most cues end up unjustified. Filter explicit filenames out of automatic
selection.

**A cue must END inside the timeline, not merely start inside it.** Guard the
cue's start + duration against the timeline length; checking only the start
extended a 45s clip to 48s and added black frames after the picture. Verify by
comparing each timeline's current length against its original.

**ffprobe's GIF duration is not what Resolve uses.** A malformed or
single-frame GIF (ffprobe: 0.1s / 1 frame) is placed as a **5s still**. 25 of
163 files in one library were like this. Treat any GIF under ~0.4s as 5s when
budgeting room, or the tail guard above silently fails.

## Two Python traps that cost real debugging time here

- **Do not name a loop-local `text`** when the enclosing loop scans a string
  called `text` with `text.find(tok, cursor)`. Shadowing it makes every later
  lookup search the previous token, return -1, and silently drop the rest of
  the segment — output collapses to one word per segment with no error.
- **`all()` on an empty iterable is True**, and Thai vowel/tone marks are not
  `isalnum()`. Testing "is this token punctuation?" with
  `not any(c.isalnum() ...)` classifies ordinary Thai words as punctuation.
  Use `unicodedata.category(c).startswith("P")`.

When a fix changes more files than predicted, diff before importing: here 6 of
12 SRTs changed rather than the expected 3, and the extra 3 turned out to be
genuine improvements (`Jr . 2` -> `Jr. 2`). Verify the surprise, do not assume
it is either fine or broken.
