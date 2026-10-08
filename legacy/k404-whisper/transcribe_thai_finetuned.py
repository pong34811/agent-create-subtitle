import json, subprocess, time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq, pipeline

ROOT = Path(__file__).resolve().parent
JOBS = json.loads((ROOT / "timeline_caption_jobs.json").read_text(encoding="utf-8"))
OUT = ROOT / "transcripts_thai"
OUT.mkdir(exist_ok=True)
REPO = "bjak/distill-whisper-th-large-v3"

torch.backends.cuda.matmul.allow_tf32 = True
processor = AutoProcessor.from_pretrained(REPO)
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    REPO, torch_dtype=torch.float16, low_cpu_mem_usage=True, use_safetensors=True
).to("cuda")
asr = pipeline(
    "automatic-speech-recognition", model=model,
    tokenizer=processor.tokenizer, feature_extractor=processor.feature_extractor,
    return_timestamps="word", torch_dtype=torch.float16, device="cuda"
)

only = int(__import__("os").environ.get("THAI_ASR_ONLY", "0"))
selected = JOBS[:only] if only else JOBS
print(f"model={REPO} jobs={len(selected)} device=cuda batch=1", flush=True)

for job in selected:
    i = job["index"]
    dest = OUT / f"K404_{i:02d}_thai.json"
    if dest.exists():
        continue
    t0 = time.time()
    duration = float(job["source_end_seconds"] - job["source_start_seconds"])
    decoded = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(job["source_start_seconds"]),
        "-i", job["source_path"], "-t", str(duration), "-vn", "-ac", "1", "-ar", "16000",
        "-f", "f32le", "pipe:1"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    audio = np.frombuffer(decoded.stdout, dtype=np.float32)
    sr = 16000
    win = 28 * sr
    step = 24 * sr
    windows = []
    starts = []
    for start in range(0, len(audio), step):
        chunk = audio[start:min(start + win, len(audio))]
        if len(chunk) < sr * 1.0:
            continue
        windows.append(chunk)
        starts.append(start / sr)
    decoded_segments = []
    for p, batch_audio in enumerate(windows):
        batch = [batch_audio]
        results = asr(batch, batch_size=1, generate_kwargs={
            "language": "thai", "task": "transcribe", "return_timestamps": True,
        })
        if isinstance(results, dict):
            results = [results]
        for j, result in enumerate(results):
            offset = starts[p+j]
            core_end = offset + step / sr
            for chunk in result.get("chunks", []):
                ts = chunk.get("timestamp") or (None, None)
                a, b = ts
                if a is None:
                    continue
                a = float(a) + offset
                b = float(b if b is not None else a - offset + 1.0) + offset
                mid = (a+b)/2
                # 4s overlap between inference windows; retain each phrase
                # from the window whose 24s core contains its midpoint.
                if mid >= core_end and core_end < duration - .05:
                    continue
                if offset > 0 and mid < offset:
                    continue
                if mid >= duration:
                    continue
                text = (chunk.get("text") or "").strip()
                if not text:
                    continue
                decoded_segments.append({"start": max(0.0,a), "end": min(duration,b), "text": text,
                                         "window_start": offset})
    decoded_segments.sort(key=lambda x: (x["start"], x["end"]))
    # Deduplicate phrases at overlap boundaries. Preserve the phrase with the
    # more central window if the model produced it twice.
    dedup = []
    for seg in decoded_segments:
        norm = "".join(seg["text"].split()).lower()
        duplicate = next((k for k,x in enumerate(dedup)
                          if "".join(x["text"].split()).lower() == norm
                          and abs(x["start"]-seg["start"]) < 1.8), None)
        if duplicate is None:
            dedup.append(seg)
        else:
            old = dedup[duplicate]
            if old["end"]-old["start"] <= .05 and seg["end"] > seg["start"]:
                dedup[duplicate] = seg
    result = {
        "timeline_index": i, "timeline_name": job["name"],
        "source_path": job["source_path"], "duration_seconds": duration,
        "model": REPO, "language": "th", "segments": dedup,
    }
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"job": i, "segments": len(dedup), "elapsed": round(time.time()-t0,1),
                      "sample": [s["text"] for s in dedup[:3]]}, ensure_ascii=False), flush=True)
