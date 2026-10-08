# TOOLING.md — เครื่องมือทั้งหมดที่ใช้ในงาน subtitle ของ aomimama-2026-09-p1

ตรวจสอบเมื่อ 2026-10-06 (ทุกรายการตรวจสด ไม่ได้คัดจากความจำ)
โปรเจกต์: `C:\Users\warit\Desktop\agent-create-subtitle`

---

## 1. Python interpreters (สำคัญที่สุด — เลือกผิดจะล้มเหลว)

| ใช้ทำอะไร | คำสั่ง | เวอร์ชัน | เหตุผล |
|---|---|---|---|
| **Resolve scripting** | `py -3.12` | 3.12.10 | โหลด `fusionscript.dll` ได้ (ยืนยันแล้ว) |
| ตัดคำไทย + สร้าง SRT | `./.venv-aomimama/Scripts/python.exe` | 3.11.16 | มี pythainlp — **โหลด fusionscript.dll ไม่ได้** |
| สคริปต์ทั่วไป | `python` | 3.14.7 | Hermes tool python |

**กฎ:** `--apply` (เขียน Resolve) ต้องใช้ `py -3.12` เท่านั้น ส่วน dry run ใช้ venv ก็ได้
นี่คือสาเหตุที่ dry run ผ่านแต่ apply ล้มเหลวในครั้งแรก

---

## 2. Packages

| แพ็กเกจ | เวอร์ชัน | สถานะ |
|---|---|---|
| `faster_whisper` | 1.2.1 | ติดตั้งแล้ว (แต่ผลไทยแย่ — ไม่ได้ใช้) |
| `pythainlp` | 5.3.8 | ติดตั้งแล้ว — ใช้ตัดคำ |
| `numpy` | 2.4.6 | ติดตั้งแล้ว |
| `pytest` | 9.1.1 | ติดตั้งแล้ว — 46 tests ผ่าน |
| `torch` | — | **ไม่มี** (ไม่ต้องใช้ เพราะไม่ใช้ Whisper) |
| `zstandard` | — | **ไม่มี** — ถ้าต้องแกะ style blob ด้วย Python 3.11 ให้ติดตั้ง |

---

## 3. External binaries

| เครื่องมือ | สถานะ | ใช้ทำอะไร |
|---|---|---|
| `ffmpeg` | n9.0.1 | ตัดท่อนเสียง + loudnorm |
| `ffprobe` | n9.0.1 | ตรวจความยาวไฟล์ |
| `npx` | 11.19.0 | ติดตั้งสกิล (`npx skills add`) |
| `git` | ใช้งานได้ | commit / worktree |

---

## 4. DaVinci Resolve

| รายการ | ค่า |
|---|---|
| สถานะ | กำลังเปิด (ตรวจสด: PID เปลี่ยนได้ทุกครั้ง) |
| `fusionscript.dll` | `C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll` |
| `DaVinciResolveScript.py` | `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\` |
| โปรเจกต์ | `aomimama-2026-09-p1` (49 timelines, 1920x1080@60) |
| ที่ตั้งโปรเจกต์ | `G:\My Drive\Projects\Resolve Project Library\...\Aommi-mama\2026-09\aomimama-2026-09-p1` |
| ฐานข้อมูล | Disk database |

**ข้อควรระวังที่เจอจริง:**
- `scriptapp('Resolve')` คืนค่า `None` ได้เป็นระยะ → ต้อง retry (สคริปต์ทำ 10 ครั้ง)
- โปรเจกต์อาจกลายเป็น "Untitled Project" ได้ → `connect()` ปฏิเสธการเขียนถ้าไม่ใช่เป้าหมาย
- `AddTrack`/`AppendToTimeline` ทำงานกับ **timeline ที่ active** → ต้อง `SetCurrentTimeline` ก่อน

---

## 5. Providers

**เหลือ Google (Gemini API) ตัวเดียว** — เป็นผู้ให้บริการเดียวที่ใช้อยู่ในงานนี้

| ผู้ให้บริการ | สถานะ |
|---|---|
| **Google Gemini API** | **ใช้งานอยู่ — ตัวเดียวของงานนี้** |

คีย์เก็บที่ `%LOCALAPPDATA%\hermes\.env` ชื่อ `GEMINI_API_KEY` เท่านั้น

### ผู้ให้บริการที่ทดสอบแล้วใช้ไม่ได้ (ลบออกหมดแล้ว)

เก็บไว้เป็นบันทึกว่า **อย่าเสียเวลาลองซ้ำ** เพราะแต่ละตัวมีเหตุผลเชิงโครงสร้าง ไม่ใช่ปัญหาชั่วคราว:

| ผู้ให้บริการ | เหตุผลที่ใช้ไม่ได้ |
|---|---|
| OpenRouter | free tier ไม่มีโมเดลรับเสียงจริง (403 "agentic harnesses only"); ตัวที่รับได้ต้องมีเครดิตขั้นต่ำ $0.50 |
| Ollama Cloud | API ไม่มีช่องรับเสียง — ทุกโมเดลตอบ "ฉันไม่ได้ยินเสียง" |
| Groq | รับเสียงได้ แต่คุณภาพไทยแย่มาก ("ฮัลโหล" → "เหลื่อการพังสะพาน") |
| opencode zen | free tier ล็อกให้ใช้ได้เฉพาะในแอป OpenCode (403) |
| FreeLLMAPI | เสียงไม่ถึงโมเดล (แนบได้แต่โมเดลไม่เห็น) |
| Hermes/Nous proxy | ลบตามคำสั่งผู้ใช้ |

คีย์ของทุกตัวข้างบน **ถูกลบออกจากเครื่องแล้ว** ทั้งใน `.env` และไฟล์ชั่วคราว

---

## 6. สคริปต์ในโปรเจกต์

| ไฟล์ | หน้าที่ | ต้องใช้ python ตัวไหน |
|---|---|---|
| `scripts/gemini_direct_transcribe.py` | ถอดเสียงผ่าน Gemini API + สลับโมเดลอัตโนมัติ | 3.14 หรือ venv |
| `scripts/transcribe_chunked.py` | ถอดไฟล์ยาวเป็นท่อน (กัน timestamp เพี้ยน) | 3.14 หรือ venv |
| `scripts/build_gemini_cues.py` | สร้าง cue + SRT จาก transcript | **venv** (pythainlp) |
| `scripts/import_subtitles_resolve.py` | นำ SRT เข้า Resolve + ตรวจอ่านกลับ | **`py -3.12`** สำหรับ `--apply` |
| `scripts/compare_asr_v2.py` | เทียบคุณภาพโมเดล (ใช้ตอบคำถาม "โมเดลไหนดีสุด") | 3.14 |
| `scripts/aomimama_caption_core.py` | ตัวแบ่งวลี + ตรวจความถูกต้องของ cue (ไลบรารี) | **venv** |
| `scripts/aomimama_asr.py` | ตัวเรียก ASR + ตรวจคุณภาพ transcript (ไลบรารี) | **venv** |
| `.agents/skills/resolve-mitr-subtitle-presets/scripts/load_subtitle_preset.py` | ใส่สไตล์ Mitr Font ให้ subtitle track | **`py -3.12`** |
**สคริปต์ที่เลิกใช้แล้ว** (เก็บไว้เป็นประวัติการทดลอง provider — ไม่ต้องรัน):
`scripts/gemini_batch_transcribe.py` (Nous proxy), `scripts/compare_asr_models.py`,
`scripts/debug_timeline2_reply.py`

### สคริปต์ไลบรารี (`aomimama_*`)

สองไฟล์นี้เป็นไลบรารีที่ทดสอบแล้ว 25 เทสต์ ไม่ได้รันตรง ๆ จากบรรทัดคำสั่ง
แต่เป็นตรรกะที่ผ่านการรีวิวแล้วสำหรับแบ่งวลีและตรวจคุณภาพ transcript
ปัจจุบันท่อหลักใช้ `build_gemini_cues.py` — ไฟล์เหล่านี้เก็บไว้เป็นฐานอ้างอิง
ถ้าต้องแก้ตรรกะการแบ่งวลีควรย้ายมาใช้ตัวนี้

```bash
# รันเทสต์ของไลบรารีคู่นี้โดยเฉพาะ
./.venv-aomimama/Scripts/python.exe -m pytest tests/test_aomimama_asr.py tests/test_aomimama_captions.py -q
```

---

## 7. Tests

```bash
./.venv-aomimama/Scripts/python.exe -m pytest tests/ -q
```

ผลล่าสุด: **32 passed**

| ไฟล์เทสต์ | จำนวน | ทดสอบอะไร |
|---|---|---|
| `tests/test_import_subtitles.py` | 7 | อ่าน SRT, วางแผน import, ไม่มี cue เกินความยาวไทม์ไลน์ |
| `tests/test_aomimama_asr.py` | 12 | ตรวจคุณภาพ transcript |
| `tests/test_aomimama_captions.py` | 13 | แบ่งวลี + ความถูกต้องของ cue |

---

## 8. คำสั่งที่ใช้บ่อย (คัดลอกได้เลย)

```bash
# ถอดเสียง Timeline ที่ยังไม่มี (ข้ามอันที่ทำแล้ว)
python scripts/gemini_direct_transcribe.py

# ถอดเฉพาะบางอัน
python scripts/gemini_direct_transcribe.py 5 12 13

# ไฟล์ยาวที่ timestamp เพี้ยน (>~100 วิ)
python scripts/transcribe_chunked.py 13 41 46

# สร้าง cue + SRT ใหม่จาก transcript
./.venv-aomimama/Scripts/python.exe scripts/build_gemini_cues.py

# ดูแผนนำเข้า (ไม่เขียนอะไร)
py -3.12 scripts/import_subtitles_resolve.py

# นำเข้าจริง (ทั้งหมด / บางอัน / แทนที่ของเดิม)
py -3.12 scripts/import_subtitles_resolve.py --apply
py -3.12 scripts/import_subtitles_resolve.py --apply --only 1 2 3
py -3.12 scripts/import_subtitles_resolve.py --apply --replace

# ใส่สไตล์ Mitr Font (dry run ก่อน แล้วค่อย --apply, รันใน background)
py -3.12 .agents/skills/resolve-mitr-subtitle-presets/scripts/load_subtitle_preset.py \
  --preset "Mitr Font" --orientation horizontal
```

---

## 9. กับดักที่เจอจริง (อย่าทำซ้ำ)

1. **`AddTrack` ก่อน `AppendToTimeline`** — ถ้าไม่มี subtitle track ก่อน append จะวางไม่ได้แต่คืนค่าไม่ว่าง
2. **`SetCurrentTimeline` ก่อนทุกอย่าง** — ไม่งั้น track ไปเพิ่มผิด timeline
3. **ห้าม append ซ้ำใน track เดียว** — มันจะต่อท้ายแทนการใช้ timecode เอง
4. **`ImportMedia` cache ตาม path** — แก้ SRT แล้ว import ซ้ำจะไม่เห็นของใหม่ ต้องลบ pool clip ก่อน
5. **เว้นจังหวะ 0.5 วิ ระหว่าง append** — ยิงติดกันทำให้ Resolve crash
6. **อย่าตรวจสไตล์ด้วยการ grep `EffectFiltersBA`** — มันอยู่ใน zstd ที่บีบอัด ต้องเทียบ blob กับ snapshot
7. **บอกความยาวไฟล์ให้โมเดลรู้** — ไม่งั้น timestamp ครึ่งหลังจะเกินความยาวไฟล์
8. **`frequencyPenalty` ไม่ได้ทุกโมเดล** — ถ้าได้ 400 "Penalty is not enabled" ให้ลองใหม่โดยไม่ใส่
