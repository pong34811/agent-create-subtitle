# Repository Guidelines

## Project Structure & Module Organization

This repository generates Thai gaming subtitles using standalone Python scripts.

- `transcribe_caption_jobs.py`: CPU Whisper transcription into `transcripts_raw/`.
- `transcribe_thai_finetuned.py`: CUDA Thai transcription into `transcripts_thai/`.
- `build_caption_assets.py` and `build_thai_caption_assets.py`: convert matching transcripts into SRT/ASS in `caption_assets/` and `caption_assets_final/`, respectively.
- `timeline_caption_jobs.json`: source paths, extraction ranges, and job indices.
- `fonts/` and sample PNGs: subtitle font and appearance references.
- `.agents/skills/create-subtitle/`: project-specific agent workflow.

There is no package layout or tests directory. Script paths resolve relative to each script's location.

## Build, Test, and Development Commands

Run from the repository root with FFmpeg on PATH and the relevant Python dependencies installed. Both paths use NumPy; builders use PyThaiNLP. CPU transcription requires `faster-whisper`; CUDA transcription requires CUDA-enabled PyTorch, Transformers, Accelerate, and Safetensors.

```powershell
python -X utf8 transcribe_caption_jobs.py
python -X utf8 build_caption_assets.py
```

These commands transcribe all jobs on CPU, then build captions from raw transcripts.

```powershell
python -X utf8 transcribe_thai_finetuned.py
python -X utf8 build_thai_caption_assets.py
```

These commands use the Thai CUDA model, then build final captions. Reuse existing transcripts when only caption formatting changes. `THAI_ASR_ONLY` limits CUDA transcription to the first N jobs, not a specific index.

## Coding Style & Naming Conventions

Use four-space Python indentation, `snake_case` functions and variables, and uppercase constants. Keep JSON readable with two-space indentation and preserved Thai characters. Maintain UTF-8 JSON and UTF-8 BOM subtitle output. Preserve filenames such as `K404_01_raw.json`, `K404_01_thai.json`, and `K404_01_captions.srt`. No formatter or linter is configured.

## Testing Guidelines

No automated test framework or coverage threshold is configured. Validate changed behavior on a selected clip in a separate working folder containing copied scripts and a reduced job list. Check `caption_summary.json`, positive cue durations, clip bounds, overlaps, Thai text, and speech synchronization. Preview ASS with the bundled Mitr font when changing styling. Report which checks were performed.

## Commit & Pull Request Guidelines

The available history uses `feat: <description>`. Follow that format with an appropriate prefix such as `fix:` or `docs:`. PRs should describe affected jobs, behavioral changes, validation, and related issues where applicable. Include preview images for visual changes.

## Configuration & Generated Outputs

Verify source paths, especially existing `G:` references. Builders overwrite captions; CPU transcription overwrites transcripts, while CUDA transcription skips existing files. Preserve original inputs when processing subsets. Subtitle times are relative to extracted clips; timeline placement requires an explicit mapping. Keep secrets and large media out of commits, consistent with `.gitignore`.
