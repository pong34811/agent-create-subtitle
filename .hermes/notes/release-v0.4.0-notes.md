## 🚀 Release v0.4.0 — ตรวจสอบทั้งโปรเจค จัด skill ให้ตรงกับท่อ Gemini และล้างไฟล์ไม่จำเป็น

รุ่นนี้ไม่เพิ่มฟีเจอร์ถอดเสียงใหม่ แต่แก้ความไม่ตรงกันระหว่าง **skill / เอกสาร / โค้ด**
ที่ทำให้ agent ที่ถูกสั่งให้สร้างซับไทยเริ่มจากท่อที่เลิกใช้แล้ว

---

### 🔎 ปัญหาที่ตรวจพบ

1. **skill `thai-subtitles-resolve` ในรีโปเป็นเวอร์ชันเก่า** — v0.3.0 บอกว่าเพิ่มเอกสารท่อ Gemini
   แต่ไฟล์จริงอยู่แค่ในโฟลเดอร์ Hermes ไม่เคยเข้ารีโป agent จึงถูกพาไปใช้ Whisper
2. **`create-subtitle` สอนแต่ Whisper/K404** และชี้ไดรฟ์ `G:`
3. **Claude Code ไม่โหลด `.agents/skills/`** — โหลดเฉพาะ `.claude/skills/`
4. **path แข็ง** `C:/Users/warit/Desktop/...` ใน 6 สคริปต์
5. มีไฟล์ขยะที่ถูก commit (`work/`, `transcript-work/`, ตัวอย่างและ PNG ที่ root, สำเนา skill ซ้ำ)

### 🛠️ สิ่งที่เปลี่ยนแปลง

- **Skill**: sync `thai-subtitles-resolve` (+ `references/gemini-asr-pipeline.md`) และ
  `thai-proofread` เข้ารีโป, เขียน `create-subtitle` ใหม่ให้ Gemini เป็นค่าเริ่มต้น
  และ Whisper เป็น legacy
- **`scripts/sync_skills.py`** (`--check`): `.agents/skills` เป็นต้นฉบับ
  `.claude/skills` เป็นสำเนาที่ Claude Code โหลดจริง
- **สคริปต์**: ไม่ใช้ path แข็งอีก ใช้ `AOMIMAMA_RUN_ROOT` หรือตำแหน่งสคริปต์,
  รองรับ `GEMINI_API_KEY` จาก environment
- **โครงสร้าง**: ย้ายท่อ K404/Whisper ทั้งชุดไป `legacy/k404-whisper/` (ใช้งานได้เหมือนเดิม
  รันจากในโฟลเดอร์นั้น)
- **เอกสาร**: เขียน `AGENTS.md` ใหม่, เพิ่ม `docs/REVIEW-th.md`

### 🧹 ไฟล์ที่ลบ

- `work/2026-10-02_190418/` (41 ไฟล์ รวม `speech.wav`), `transcript-work/`
- ตัวอย่าง K404_29 และ `caption-sample*.png` ที่ root
- `.hermes/skills/` (ซ้ำกับ `.claude/skills` ทุกไบต์)
- ในเครื่องเท่านั้น: `.mov` 2 ไฟล์ และ `caption_assets_final/rendered/` รวม ~930 MB
  (สร้างใหม่ได้จากไฟล์ ASS), แคช pytest/`__pycache__`

### ⚠️ จุดด้อยที่ยังเหลือ (รายละเอียดใน `docs/REVIEW-th.md`)

- ซับทั้ง 49 ไทม์ไลน์ยัง `approved: false` — ยังไม่มีคนฟังเทียบเสียงจริง
- คุณภาพไม่คงที่: มาจาก 7 โมเดลเพราะโควตาฟรีหมด
- ไม่มีตัวรันรวม ต้องสลับ `python` 3.11 กับ `py -3.12` เอง
- `thai-subtitles-resolve` ยาว ~21 KB ควรแยกเป็น references
- ยังไม่มีไฟล์คำศัพท์ชื่อเกม/ตัวละครส่งเข้า prompt

### ✅ การตรวจสอบ

- `python -m pytest tests` — **32 passed**
- `python scripts/sync_skills.py --check` — skills ตรงกัน
- คอมไพล์สคริปต์ทุกไฟล์ผ่าน (`py_compile`)
- **ไม่ได้ทดสอบ**: การเรียก Gemini API จริง และการเขียนเข้า Resolve (ไม่ได้รันในรอบนี้)

### 📦 อัปเกรด

ไม่มี breaking change ต่อท่อปัจจุบัน ผู้ที่เรียกสคริปต์ K404 เดิมต้องเปลี่ยนไปรันจาก
`legacy/k404-whisper/`
