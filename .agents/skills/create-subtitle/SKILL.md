---
name: create-subtitle
description: Create Thai subtitles from audio, video, or selected timeline clips using this project's Whisper transcription and caption pipeline. Use for generating or correcting SRT/ASS captions, including short gaming captions and batches from timeline_caption_jobs.json.
---

# Create Subtitle

Use the subtitle pipeline in this repository. The repository root is three
directories above this skill folder; resolve it from the skill location rather
than assuming the shell's current directory. Read the relevant scripts before
running them because their input and output paths are relative to the scripts.

## Inputs and scope

Determine the requested source, clip range, language, and deliverable from the
user's request. This pipeline transcribes Thai by default and produces separate
SRT and styled ASS files. A request to create subtitles does not itself request
a video render or changes to a DaVinci Resolve timeline.

For existing project clips, select jobs from `timeline_caption_jobs.json`.
For another source, build a job list with the fields the scripts consume:

```json
[
  {
    "index": 1,
    "name": "example_clip",
    "source_path": "D:/media/example.mp4",
    "source_start_seconds": 0,
    "source_end_seconds": 30
  }
]
```

Use unique integer indices and a positive source range. Confirm that the source
file exists. For a whole file, obtain its actual duration with ffprobe. Existing
jobs reference media on `G:`; do not assume that drive is available. The
`estimated_seconds` field in existing jobs is not the source duration.

The scripts process every job in their adjacent job list. For a subset or new
media, create a separate working folder under the repository, copy the relevant
transcriber and caption builder into it, and write only the selected jobs to
that folder's `timeline_caption_jobs.json`. Keep original job indices. Copy
matching existing transcript files into the appropriate transcript subfolder
when reusing them. This avoids changing the project's original job list or
regenerating unrelated outputs. The output filenames still use `K404_XX`; map
each index to its job name when delivering files.

## Choose the transcription path

Reuse matching transcripts when available. Check source path, job index, and
duration against the requested clip; a matching filename alone is insufficient.

| Path | Transcriber | Transcript files | Builder | Caption output |
| --- | --- | --- | --- | --- |
| Thai model on CUDA | `transcribe_thai_finetuned.py` | `transcripts_thai/K404_XX_thai.json` | `build_thai_caption_assets.py` | `caption_assets_final/` |
| Whisper on CPU | `transcribe_caption_jobs.py` | `transcripts_raw/K404_XX_raw.json` | `build_caption_assets.py` | `caption_assets/` |

Both paths require Python, FFmpeg on PATH, and NumPy. Caption builders require
PyThaiNLP. The CPU path requires `faster-whisper` and uses `large-v3` with int8.
The CUDA path requires a CUDA-capable PyTorch installation, Transformers,
Accelerate, and Safetensors; it uses `bjak/distill-whisper-th-large-v3` with
float16. Inspect the existing Python environment before installing missing
dependencies. Model files may need downloading on first use.

Select the CUDA path when its environment is available; otherwise use the CPU
path and its matching builder. Do not feed CPU transcript files to the Thai
builder. Both transcribers currently force Thai; adapt a working copy if the
user requests another language, and review the builders' Thai text processing
before using them for that language.

Run the appropriate pair from the chosen working folder, for example:

```powershell
python -X utf8 .\transcribe_thai_finetuned.py
python -X utf8 .\build_thai_caption_assets.py
```

Or use the CPU pair:

```powershell
python -X utf8 .\transcribe_caption_jobs.py
python -X utf8 .\build_caption_assets.py
```

The CUDA transcriber skips existing transcript files. To correct a stale
transcript, preserve it and regenerate in a separate working folder. Its
`THAI_ASR_ONLY` environment variable selects the first N jobs, not a job index;
select arbitrary jobs through the working folder's job list instead. The CPU
transcriber overwrites matching transcripts, and both builders overwrite
matching caption outputs.

## Text, timing, and style

Read and correct the transcript before generating final captions. Preserve
spoken meaning and review uncertain game terms against the audio. The builders
contain corrections, noise rules, and special cases for the original gaming
batch. Inspect those rules for new media; change only the working copy when
they would replace legitimate speech or discard meaningful content.

Caption timing starts at zero for the extracted source range. To put captions
on an edited timeline, use that clip's actual timeline position and edits.
`source_start_seconds` is the extraction offset in the original recording; it
is not automatically the offset for placing subtitles in the edited timeline.
Single source ranges do not describe timelines containing multiple cuts,
retiming, or reordered clips; obtain that mapping before claiming sync.

The existing builders produce short cards of roughly one to four Thai tokens,
usually held for about 0.6 to 1.8 seconds. Use these settings for the existing
gaming style and adapt a working copy if the user requests full sentences or
another reading pace. CUDA captions divide phrase duration using token length;
those subdivisions are estimates rather than measured word boundaries.

ASS defaults are 1920x1080, bold white Mitr at size 66, a black outline, and
bottom-centered placement. The Thai builder uses MarginV 360; the CPU builder
uses MarginV 185. The font asset is `fonts/Mitr-Bold.ttf` in the repository.
Adapt ASS resolution and margins to the user's target video when requested.
SRT contains plain text and timing; ASS carries the visual style.

## Deliver and check

Deliver the requested files with their job names and clickable paths. Each
builder also writes `caption_summary.json`, useful for spotting empty jobs and
unusual cue durations. Before reporting generation as complete, check that
requested files exist, text is readable as UTF-8, cue ends follow starts,
timings stay within clip duration, and cues do not overlap. Review speech at
the beginning, end, and uncertain sections when audio access is available.
State whether audio sync or visual appearance was actually reviewed.

For a request to edit subtitles only, update the relevant transcript or caption
files without rerunning recognition unnecessarily. For a requested video render
or timeline import, use the corresponding available video or Resolve workflow
and preserve the subtitle timing mapping established above.
