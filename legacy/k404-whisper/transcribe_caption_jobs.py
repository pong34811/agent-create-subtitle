import json, os, subprocess, sys, time
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parent
JOBS = json.loads((ROOT / "timeline_caption_jobs.json").read_text(encoding="utf-8"))
OUT = ROOT / "transcripts_raw"
OUT.mkdir(exist_ok=True)

model = WhisperModel("large-v3", device="cpu", compute_type="int8",
                     cpu_threads=8, num_workers=1)
print(f"model=large-v3 device=cpu compute=int8 jobs={len(JOBS)}", flush=True)

for index, job in enumerate(JOBS, 1):
    started = time.time()
    duration = float(job["source_end_seconds"] - job["source_start_seconds"])
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-ss", str(job["source_start_seconds"]), "-i", job["source_path"],
        "-t", str(duration), "-vn", "-ac", "1", "-ar", "16000",
        "-acodec", "pcm_s16le", "-f", "s16le", "pipe:1"
    ]
    decoded = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             check=True)
    audio = np.frombuffer(decoded.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if len(audio) == 0:
        raise RuntimeError(f"no decoded audio for timeline {job['index']}")
    segments, info = model.transcribe(
        audio, language="th", task="transcribe", word_timestamps=True,
        vad_filter=True, beam_size=5, temperature=0,
        condition_on_previous_text=False,
        vad_parameters={"min_silence_duration_ms": 350, "speech_pad_ms": 120}
    )
    rows = []
    for seg in segments:
        words = []
        for w in (seg.words or []):
            words.append({
                "start": float(w.start), "end": float(w.end), "text": w.word,
                "probability": float(w.probability)
            })
        rows.append({
            "start": float(seg.start), "end": float(seg.end), "text": seg.text,
            "avg_logprob": float(seg.avg_logprob),
            "no_speech_prob": float(seg.no_speech_prob),
            "compression_ratio": float(seg.compression_ratio),
            "words": words
        })
    result = {
        "timeline_index": job["index"], "timeline_name": job["name"],
        "source_path": job["source_path"],
        "source_start_seconds": job["source_start_seconds"],
        "source_end_seconds": job["source_end_seconds"],
        "duration_seconds": duration,
        "language": info.language, "language_probability": float(info.language_probability),
        "model": "large-v3", "segments": rows
    }
    dest = OUT / f"K404_{job['index']:02d}_raw.json"
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "job": index, "timeline": job["name"], "segments": len(rows),
        "duration_seconds": duration, "elapsed_seconds": round(time.time()-started, 1),
        "output": str(dest)
    }, ensure_ascii=False), flush=True)

