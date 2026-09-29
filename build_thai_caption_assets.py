import json, re
from difflib import SequenceMatcher
from pathlib import Path

from pythainlp.tokenize import word_tokenize
from pythainlp.util import Trie
from pythainlp.corpus.common import thai_words

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "caption_assets_final"
OUT.mkdir(exist_ok=True)
JOBS = json.loads((ROOT / "timeline_caption_jobs.json").read_text(encoding="utf-8"))
CUSTOM_WORDS = Trie(thai_words() | {
    "Copper", "Golem", "Copper Golem", "Creeper", "Ruby", "X-ray", "NPC",
    "คอปเปอร์", "โกเลม", "ซอมบี้", "แม่ง", "ขี้เกียจ", "เอ็กซ์เรย์",
    "ชาวบ้าน", "ดินเหนียว", "ทองแดง", "เหล็ก", "ผสมพันธุ์", "แบล็กลิสต์",
    "เลเซอร์", "ลูกตา", "หัวใจ", "ราฟี่", "คุณหมอก", "แคปซูล", "ขนมปัง",
})

def collapse_repetitions(text):
    text = re.sub(r"\s+", "", text).replace("ๆ", "")
    for _ in range(3):
        text = re.sub(r"(.{1,12}?)\1{2,}", r"\1", text)
        text = re.sub(r"(.)\1{5,}", r"\1", text)
    return text.strip()

def fix_text(i, s):
    s = collapse_repetitions(s)
    s = s.replace("ทํา", "ทำ").replace("กําลัง", "กำลัง")
    # Clearly identifiable names and game terminology in these timelines.
    pairs = [
        (r"ซ้อมบี้|ซอมมี่|ซอมปี้|ซอมบี้", "ซอมบี้"),
        (r"คลิปเปอร์|ครีปเปอร์|คีปเปอร์|ชี้เปอร์", "Creeper"),
        (r"ค็อปหูไอโกเล็มค็อปเปอร์|คอปหูไอโกเล็มคอปเปอร์", "Copper Golem"),
        (r"คอปเปอร์โกเล็ม|ค็อปเปอร์โกเล็ม|คอปเปอร์โกเลม", "Copper Golem"),
        (r"ค็อปเปอร์", "Copper"),
        (r"คอปเปอร์", "Copper"),
        (r"กี้เกียจ", "ขี้เกียจ"),
        (r"หวานแจ๊บ|หวานแจ๊ก", "หวานเจี๊ยบ"),
        (r"เอ็กเรย์|เอกเรย์|เอ็กรีย์|เอกรีย์|เอกเร", "เอ็กซ์เรย์"),
        (r"แบล็คลิสต์|แบ็คคลิสต์|แบ็คลิสต์|แบล็กลิส", "แบล็กลิสต์"),
        (r"มอนฮานะ|มอนฮันนะ|มอนฮาน|มอนฮา", "มอนฮัน"),
        (r"ราจัง|ราชัง", "คุรุยาคุ"),
        (r"ราฟี", "ราฟี่"),
        (r"ฮาร์ทโหมด", "Hard Mode"),
        (r"แคปซูน|แคปซูล", "แคปซูล"),
        (r"ฮิว", "ฮีล"),
        (r"เลเซอ", "เลเซอร์"),
    ]
    for pat, val in pairs:
        s = re.sub(pat, val, s, flags=re.I)
    # The speaker refers to the Copper Golem in timeline 2; Whisper joined
    # several adjacent syllables into a false phrase.
    if i == 2:
        s = re.sub(r"ตัว\s*Copper\s*Golem(?:อะ)?ครับ", "ตัว Copper Golem ครับ", s)
        s = re.sub(r"ตัวค็?อปหูไอโกเล็มค็?อปเปอร์อะ?ครับ", "ตัว Copper Golem ครับ", s)
        s = re.sub(r"ตัวคอปเปอร์.*?ครับ", "ตัว Copper Golem ครับ", s)
    # Keep transliterated English game names spaced for readability.
    s = re.sub(r"(?<=[ก-๙])(?=(?:Copper|Creeper|Golem|NPC|Ruby|X-ray)\b)", " ", s, flags=re.I)
    s = re.sub(r"(?<=[A-Za-z])(?=[ก-๙])", " ", s)
    return s.strip()

def is_noise(i, text, duration):
    x = re.sub(r"\s+", "", text).lower()
    if not x or x in {"ๆ", "ครับครับครับ", "อื้อ", "อือ", "อืม", "ฮ่า", "555"}:
        return True
    # The Thai-tuned recognizer hallucinated this same unrelated phrase across
    # a long silent/ambiguous stretch of the Barroth clip; the other ASR pass
    # did not detect it, and the surrounding gameplay context does not support it.
    if i == 23 and x == "สล็อตออนไลน์":
        return True
    if len(x) > 22 and len(set(x)) <= 4:
        return True
    if re.fullmatch(r"(?:อ+|อื+|อุ+|ฮ+|ๆ+|[ฮา]+|(?:ครับ)+|(?:เฮ้ย)+)", x) and duration > 2.2:
        return True
    # Repeated short onomatopoeia is often game audio/laughter hallucinated by ASR.
    if len(x) >= 30 and re.search(r"(.{1,4})\1{5,}", x):
        return True
    return False

def tokenize_display(text):
    toks = [t.strip() for t in word_tokenize(text, engine="newmm", custom_dict=CUSTOM_WORDS, keep_whitespace=False) if t.strip()]
    # Merge unrecognized proper-name syllables where the adjacent tokens form
    # an obvious known game term.
    joined = "".join(toks)
    known = {
        "ซอมมี่": "ซอมบี้", "ซอมบี้": "ซอมบี้", "คอปเปอร์โกเลม": "Copper Golem",
        "Creeper": "Creeper", "เอ็กซ์เรย์": "เอ็กซ์เรย์", "รูบี้": "รูบี้",
    }
    if joined in known:
        return [known[joined]]
    out = []
    for t in toks:
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9'._-]*", t):
            if out and out[-1].endswith("ENG"):
                out[-1] = out[-1][:-3] + " " + t
            else:
                out.append(t + "ENG")
        else:
            out.append(t)
    return out

def display_group(tokens):
    s = ""
    for t in tokens:
        if t.endswith("ENG"):
            s += (" " if s else "") + t[:-3] + " "
        else:
            s += t
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.!?])", r"\1", s)
    return s

def build_cues(i, raw):
    source = []
    for seg in raw.get("segments", []):
        start, end = float(seg["start"]), float(seg["end"])
        if end <= start or start >= raw["duration_seconds"]:
            continue
        original = seg.get("text", "").strip()
        text = fix_text(i, original)
        if is_noise(i, text, end-start):
            continue
        # Drop verbatim hallucinated repeats emitted around overlap boundaries,
        # while retaining repeated short reactions when they are separated.
        norm = re.sub(r"[^0-9A-Za-zก-๙]", "", text).lower()
        duplicate = None
        for j, old in enumerate(source[-20:]):
            oldnorm = re.sub(r"[^0-9A-Za-zก-๙]", "", old["text"]).lower()
            gap = start - old["start"]
            similar = SequenceMatcher(None, norm, oldnorm, autojunk=False).ratio()
            if len(norm) >= 8 and gap >= 0 and gap <= 10 and similar >= .91:
                duplicate = len(source)-len(source[-20:])+j
                break
        if duplicate is not None:
            continue
        source.append({"start":start,"end":min(end, float(raw["duration_seconds"])),"text":text})

    cues = []
    for seg in source:
        tokens = tokenize_display(seg["text"])
        if not tokens:
            continue
        raw_dur = seg["end"]-seg["start"]
        # A few forced-alignment tails stretch a short transcript over a VAD
        # gap. Keep the speech span proportional to its readable text.
        natural = max(.65, len(seg["text"]) * .15)
        duration = min(raw_dur, max(1.2, min(8.0, natural)))
        if raw_dur > 12 and len(seg["text"]) < 35:
            duration = min(duration, 2.0)
        if duration <= 0:
            continue
        weights = [max(1.0, len(t.replace("ENG", ""))) for t in tokens]
        total = sum(weights)
        pos = 0
        groups = []
        group = []
        group_w = 0.0
        group_start_weight = 0.0
        for token, weight in zip(tokens, weights):
            if group and (len(group) >= 4 or group_w >= total * .55):
                groups.append((group, group_start_weight, group_w))
                group_start_weight += group_w
                group, group_w = [], 0.0
            group.append(token); group_w += weight
        if group:
            groups.append((group, group_start_weight, group_w))
        if not groups:
            continue
        for group, offset_w, group_weight in groups:
            st = seg["start"] + duration * offset_w / total
            en = seg["start"] + duration * (offset_w + group_weight) / total
            st = max(0.0, st)
            en = max(st + .2, en)
            # Keep each dynamic card within the requested short-form range.
            if en-st > 1.8:
                en = st + 1.8
            cues.append({"start":st,"end":en,"text":display_group(group)})

    cues.sort(key=lambda c:(c["start"],c["end"]))
    out = []
    for cue in cues:
        cue["start"] = max(0.0, cue["start"])
        cue["end"] = min(float(raw["duration_seconds"]), cue["end"] + .07, cue["start"] + 1.8)
        if out and cue["start"] < out[-1]["end"]:
            cue["start"] = out[-1]["end"]
        if cue["end"] - cue["start"] < .55:
            cue["end"] = min(float(raw["duration_seconds"]), cue["start"] + .60)
        cue["text"] = cue["text"].strip()
        if cue["text"] and cue["end"] > cue["start"]:
            if out and cue["text"] == out[-1]["text"] and cue["start"] - out[-1]["end"] <= .05:
                continue
            out.append(cue)
    for j in range(len(out)-1):
        if out[j]["end"] > out[j+1]["start"]:
            out[j]["end"] = out[j+1]["start"]
    return [c for c in out if c["end"]-c["start"] >= .2]

def srt_time(t):
    ms = max(0, int(round(t*1000)))
    hh, ms = divmod(ms, 3600000); mm, ms = divmod(ms, 60000); ss, ms = divmod(ms, 1000)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

def ass_time(t):
    t=max(0.0,t); h=int(t//3600); t-=h*3600; m=int(t//60); t-=m*60; s=int(t); cs=int((t-s)*100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Mitr,66,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,100,100,360,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
summary=[]
for job in JOBS:
    i=job["index"]
    raw=json.loads((ROOT/"transcripts_thai"/f"K404_{i:02d}_thai.json").read_text(encoding="utf-8"))
    cues=build_cues(i,raw)
    stem=f"K404_{i:02d}"
    srt=[]; events=[]
    for n,c in enumerate(cues,1):
        srt.append(f"{n}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n")
        text=c['text'].replace("\\","\\\\").replace("{",r"\{").replace("}",r"\}").replace("\u2028",r"\N").replace("\u2029",r"\N")
        events.append(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Default,,0,0,0,,{text}")
    (OUT/f"{stem}_captions.srt").write_text("\n".join(srt),encoding="utf-8-sig")
    (OUT/f"{stem}_captions.ass").write_text(header+"\n".join(events)+"\n",encoding="utf-8-sig")
    durations=[c['end']-c['start'] for c in cues]
    summary.append({"index":i,"name":job['name'],"duration":raw['duration_seconds'],"cues":len(cues),
                    "average":sum(durations)/len(durations) if durations else 0,
                    "max":max(durations,default=0),"overlaps":sum(1 for a,b in zip(cues,cues[1:]) if a['end']>b['start']),
                    "sample":[c['text'] for c in cues[:8]]})
(OUT/"caption_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
