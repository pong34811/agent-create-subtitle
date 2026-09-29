import json
import math
import re
from pathlib import Path

from pythainlp.tokenize import word_tokenize

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "caption_assets"
OUT.mkdir(exist_ok=True)
JOBS = json.loads((ROOT / "timeline_caption_jobs.json").read_text(encoding="utf-8"))

# Normalize obvious Whisper misspellings from the game-specific context. The
# replacements affect display text only; timings still come from the original
# token stream.
FIXES = [
    (r"ซ้อมบี้|ซอมมี่|ซอมปี้|ซ้อมมี่", "ซอมบี้"),
    (r"คีปเปอร์|คิปเปอร์|ครีปเปอร์|ครีปเปอร์", "Creeper"),
    (r"คอปเปอร์\s*โกเลม", "Copper Golem"),
    (r"มอนฮานะ|มอนฮันนะ|มอนฮา", "มอนฮัน"),
    (r"เอกเลส|เอกรีย์|เอ็กเลส", "เอ็กซ์เรย์"),
    (r"หวานแจ๊บ|หวานแจ๊ก", "หวานเจี๊ยบ"),
    (r"แบล็กลิสต์", "แบล็กลิสต์"),
]

def tc(t):
    t = max(0.0, t)
    h = int(t // 3600); t -= h * 3600
    m = int(t // 60); t -= m * 60
    s = int(t)
    cs = int(round((t - s) * 100))
    if cs == 100:
        s += 1; cs = 0
    if s == 60:
        m += 1; s = 0
    if m == 60:
        h += 1; m = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def clean_display(s):
    s = re.sub(r"\s+", " ", s).strip()
    for pat, val in FIXES:
        s = re.sub(pat, val, s, flags=re.I)
    # NewMM sometimes breaks an uncommon proper noun at the syllable boundary.
    s = re.sub(r"ซอม\s*(?:มี่|บี้|ปี้)", "ซอมบี้", s)
    s = re.sub(r"คอป\s*เปอร์", "คอปเปอร์", s)
    s = re.sub(r"ครีป\s*เปอร์", "Creeper", s, flags=re.I)
    s = s.replace("ทํา", "ทำ").replace("กําลัง", "กำลัง")
    s = re.sub(r"\s+([,.!?])", r"\1", s)
    return s

def bad_repeated(seg, display_words):
    # Drop prolonged non-verbal laughter/groans and obvious sound-effect
    # hallucinations. A few lexical calls such as "ระวัง" are kept.
    txt = re.sub(r"\s+", "", seg.get("text", ""))
    if not txt:
        return True
    if len(display_words) >= 24:
        norm = [re.sub(r"[^\wก-๙]", "", w).lower() for w in display_words]
        norm = [w for w in norm if w]
        if norm:
            counts = {}
            for w in norm: counts[w] = counts.get(w, 0) + 1
            dominant, count = max(counts.items(), key=lambda kv: kv[1])
            if count / len(norm) >= .72 and dominant in {"ฮ่า", "ฮา", "อื้อ", "อือ", "เฮ", "เฮเฮ", "ตี", "ไอ"}:
                return True
    if len(txt) >= 60 and len(set(txt)) <= 4:
        return True
    if txt.count("ๆ") >= 10:
        return True
    if len(txt) > 50 and re.search(r"(.{1,3})\1{12,}", txt):
        return True
    return False

def make_cues(raw):
    cues = []
    for seg in raw.get("segments", []):
        if seg.get("no_speech_prob", 1) >= .82 or seg.get("avg_logprob", -9) < -1.0:
            continue
        pieces = seg.get("words", [])
        text = "".join(p.get("text", "") for p in pieces)
        if not text.strip():
            continue
        char_times = []
        for p in pieces:
            char_times.extend([(float(p["start"]), float(p["end"]))] * len(p.get("text", "")))
        toks = word_tokenize(text, engine="newmm", keep_whitespace=True)
        spans = []
        pos = 0
        for tok in toks:
            if not tok or tok.isspace():
                pos += len(tok)
                continue
            n = len(tok)
            chunk = char_times[pos:pos+n]
            pos += n
            if not chunk:
                continue
            st = min(p[0] for p in chunk)
            en = max(p[1] for p in chunk)
            if en <= st:
                en = st + .025
            # Whisper sometimes stretches a final Thai character over a long
            # VAD gap. A spoken word cannot occupy most of a 5–50s segment, so
            # cap that faulty token interval before constructing a caption.
            en = min(en, st + 1.35)
            spans.append({"text": tok, "start": st, "end": en})
        if not spans or bad_repeated(seg, [x["text"] for x in spans]):
            continue

        # Runs of a repeated interjection are represented in readable bursts,
        # not as a long wall of identical caption cards.
        compact = []
        i = 0
        while i < len(spans):
            j = i + 1
            base = spans[i]["text"].strip()
            while j < len(spans) and spans[j]["text"].strip() == base and spans[j]["start"] - spans[j-1]["end"] < .55:
                j += 1
            run = spans[i:j]
            if len(run) >= 4 and base in {"โอ๊ย", "โอ้ย", "โทษ", "ระวัง", "เฮ้ย"}:
                # Keep one clear cue per 1.5s of an actual repeated call.
                last_kept = -999.0
                for x in run:
                    if x["start"] - last_kept >= 1.35:
                        compact.append(x); last_kept = x["start"]
            elif len(run) >= 4:
                compact.append(run[0])
            else:
                compact.extend(run)
            i = j
        spans = compact

        group = []
        def flush():
            nonlocal group
            if not group:
                return
            st = group[0]["start"]
            en = group[-1]["end"]
            display = ""
            for x in group:
                part = x["text"].strip()
                if not part:
                    continue
                if re.search(r"[A-Za-z0-9]", part):
                    display += (" " if display and not display.endswith(" ") else "") + part
                    display += " "
                else:
                    display += part
            display = clean_display(display)
            display = display.replace(" ,", ",").replace(" .", ".")
            if display:
                cues.append({"start": st, "end": en, "text": display})
            group = []

        for w in spans:
            if group:
                pause = w["start"] - group[-1]["end"]
                group_dur = w["end"] - group[0]["start"]
                # Phrase boundary on a real pause or punctuation; average card
                # time stays near 1.1s while keeping at most four Thai words.
                punct = bool(re.search(r"[.!?…]$", group[-1]["text"].strip()))
                if pause > .34 or punct or len(group) >= 4 or (group_dur >= 1.25 and len(group) >= 2) or group_dur >= 1.72:
                    flush()
            group.append(w)
        flush()

    cues.sort(key=lambda x: (x["start"], x["end"]))
    # Keep true word onset and remove any overlaps from grouped recognizer spans.
    out = []
    for cue in cues:
        st = max(0.0, cue["start"])
        en = min(float(raw["duration_seconds"]), cue["end"] + .08)
        if out and st < out[-1]["end"]:
            # Simultaneous model fragments are one phrase; start the next card
            # at the prior card's end rather than letting captions overlap.
            st = out[-1]["end"]
        if en <= st:
            continue
        # Fast interjections may be short; hold at least 0.6s unless the next
        # spoken card starts sooner.
        min_end = st + .60
        if len(out) and min_end > out[-1]["end"] and st < out[-1]["end"]:
            st = out[-1]["end"]
            min_end = st + .60
        en = max(en, min_end)
        en = min(en, float(raw["duration_seconds"]))
        en = min(en, st + 1.8)
        if out and st < out[-1]["end"]:
            st = out[-1]["end"]
        if en > st:
            out.append({"start": st, "end": en, "text": cue["text"]})
    # Cap any unusually long minimum-duration hold at the next cue onset.
    for i in range(len(out)-1):
        if out[i]["end"] > out[i+1]["start"]:
            out[i]["end"] = out[i+1]["start"]
    return [c for c in out if c["end"] - c["start"] >= .2]

def ass_escape(s):
    s = s.replace("\\", "\\\\").replace("{", r"\{").replace("}", r"\}")
    s = s.replace("\u2028", r"\N").replace("\u2029", r"\N")
    return s

summary = []
for job in JOBS:
    ix = job["index"]
    raw = json.loads((ROOT / "transcripts_raw" / f"K404_{ix:02d}_raw.json").read_text(encoding="utf-8"))
    cues = make_cues(raw)
    stem = f"K404_{ix:02d}"
    # SRT timings at millisecond precision.
    srt = []
    for n, c in enumerate(cues, 1):
        def sm(t):
            ms = int(round(t*1000)); hh, ms = divmod(ms, 3600000); mm, ms = divmod(ms, 60000); ss, ms = divmod(ms, 1000)
            return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"
        srt.append(f"{n}\n{sm(c['start'])} --> {sm(c['end'])}\n{c['text']}\n")
    (OUT / f"{stem}_captions.srt").write_text("\n".join(srt), encoding="utf-8-sig")

    # A separate, styled alpha overlay render is used in Resolve because the
    # current scripting bridge cannot reliably style native subtitle events.
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Mitr,66,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,100,100,185,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for c in cues:
        events.append(f"Dialogue: 0,{tc(c['start'])},{tc(c['end'])},Default,,0,0,0,,{ass_escape(c['text'])}")
    (OUT / f"{stem}_captions.ass").write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")
    summary.append({"index": ix, "name": job["name"], "duration": raw["duration_seconds"], "cues": len(cues),
                    "min": min((c['end']-c['start'] for c in cues), default=0),
                    "avg": (sum(c['end']-c['start'] for c in cues)/len(cues) if cues else 0),
                    "max": max((c['end']-c['start'] for c in cues), default=0),
                    "first": cues[:4], "last": cues[-2:]})

(OUT / "caption_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps([{k:v for k,v in x.items() if k not in {"first","last"}} for x in summary], ensure_ascii=False, indent=2))
