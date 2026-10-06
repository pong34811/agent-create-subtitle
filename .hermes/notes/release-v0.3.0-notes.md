## 🚀 Release v0.3.0 — สร้างซับไทยทั้ง 49 Timeline ด้วย Gemini ASR

รุ่นนี้ปิดงาน subtitle ของโปรเจกต์ `aomimama-2026-09-p1` ครบวงจร: ถอดเสียง 49
ไทม์ไลน์ → นำเข้า Resolve → ใส่สไตล์ Mitr Font พร้อมเครื่องมือที่ใช้ทำทั้งหมด

---

### 🛠️ สิ่งที่เปลี่ยนแปลง

#### 1. นำซับเข้า Resolve ได้จริงด้วยสคริปต์ (`scripts/import_subtitles_resolve.py`)

สคริปต์นำไฟล์ SRT เข้า subtitle track แล้ว**อ่านกลับเพื่อยืนยัน** ทุกครั้ง
ค่าเริ่มต้นเป็น dry run (ไม่เขียนอะไร) ต้องสั่ง `--apply` จึงจะเขียนจริง

```bash
# ดูแผนก่อน (ไม่แตะ Resolve)
py -3.12 scripts/import_subtitles_resolve.py

# นำเข้าจริงทั้งหมด / บางไทม์ไลน์ / แทนที่ของเดิม
py -3.12 scripts/import_subtitles_resolve.py --apply
py -3.12 scripts/import_subtitles_resolve.py --apply --only 1 2 3
py -3.12 scripts/import_subtitles_resolve.py --apply --replace
```

**สำคัญ:** ต้องใช้ `py -3.12` เท่านั้น เพราะ venv ที่มี pythainlp (3.11)
โหลด `fusionscript.dll` ของ Resolve ไม่ได้

#### 2. ท่อถอดเสียงภาษาไทยด้วย Gemini

- `scripts/gemini_direct_transcribe.py` — ถอดเสียงพร้อมสลับโมเดลอัตโนมัติเมื่อโควตาหมด
  และ**บอกความยาวไฟล์ให้โมเดลรู้** ซึ่งแก้อาการ timestamp เพี้ยน
- `scripts/transcribe_chunked.py` — ไฟล์ที่ยาวเกิน ~100 วินาที ตัดเป็นท่อนที่จุดเงียบที่สุด
  แล้วต่อเวลา offset กลับ ทำให้ timestamp ถูกต้อง

#### 3. ไลบรารีที่ผ่านการทดสอบ 25 เทสต์

`scripts/aomimama_caption_core.py` และ `scripts/aomimama_asr.py` พร้อมเทสต์
ย้ายจาก worktree ชั่วคราวเข้าโปรเจกต์แล้ว (ถ้าไม่ย้ายจะหายเมื่อระบบเก็บกวาด)
รวมกับเทสต์ของสคริปต์นำเข้า เป็น **32 เทสต์**

#### 4. `TOOLING.md` — คลังเครื่องมือที่ตรวจสดทุกบรรทัด

 interpreters, แพ็กเกจ, provider, สคริปต์, คำสั่งที่ใช้บ่อย และกับดัก 8 ข้อ
ที่ทำให้เสียเวลาจริง

#### 5. แก้ `/grill-with-docs` ที่เรียกไม่ทำงาน

สาเหตุคือ **แคชใน process ที่รันอยู่** ไม่ใช่ตัวสกิล — สแกนสดเจอสกิลครบ
แต่ process ถือแผนที่คำสั่งที่แคชไว้ตั้งแต่เริ่ม session ก่อนสกิลถูกติดตั้ง
แก้ด้วย `/reload-skills` (บันทึกไว้ที่ `.hermes/notes/grill-with-docs-troubleshooting.md`)

ติดตั้ง `grilling` และ `domain-modeling` เพิ่ม เพราะ `grill-with-docs` เป็น
wrapper ที่สั่งให้เรียกสองตัวนี้ ซึ่งไม่เคยมีในเครื่องมาก่อน

#### 6. อัปเดตสกิล

- `thai-subtitles-resolve` — แก้ description จาก Whisper เป็น Gemini ASR
  เพิ่ม `references/gemini-asr-pipeline.md` และบันทึกกับดัก `SetCurrentTimeline`
- `thai-proofread` — ตัด description ให้พอดี 60 ตัวอักษร

#### 7. `.gitignore` กันไฟล์สื่อหลุดเข้า git

เพิ่ม `*.wav` `*.mp3` `*.m4a` `*.flac` และ `runs/*/audio/`, `runs/*/backups/`
**หลังพบว่าไฟล์ WAV 101 ไฟล์ (964 MB) ติดเข้า commit ไปโดยไม่ตั้งใจ** ในสาขานี้
แก้โดยเขียน commit ที่ยังไม่ push ใหม่ (ไฟล์บนดิสก์ไม่หายแม้แต่ไฟล์เดียว)

---

### ✅ ผลการตรวจสอบ

| รายการ | ผล |
|---|---|
| ไทม์ไลน์ที่มี subtitle track | **49 / 49** |
| จำนวน cue ตรงกับ SRT | **49 / 49** |
| Cue ทั้งหมดใน Resolve | **963** |
| ข้อความครบถ้วน (transcript → cue) | **100.00 %** |
| Cue ที่ timestamp เกินความยาวไฟล์ | **0** |
| เว้นวรรคผิดในคำไทย | **0** |
| SRT อ่านได้ เวลาไม่ย้อนกลับ | **49 / 49** |
| สไตล์ Mitr Font | **49 / 49 track** |
| เทสต์ | **32 passed** |

**การตรวจซับทำ 2 ทางอิสระ:** ครั้งแรกจาก readback ของสคริปต์นำเข้า ครั้งที่สอง
จากคำสั่ง Resolve โดยตรง ทั้งคู่ให้ผลตรงกัน

**การตรวจสไตล์:** เทียบ blob ใน `Project.db` กับ snapshot ก่อนเขียน (111 → 288 bytes
ทุก track) และรัน dry run ซ้ำได้ `0 of 49 subtitle track(s) would change.`

**ไฟล์สำรอง:** `~/Documents/resolve-subtitle-preset-backups/aomimama-2026-09-p1_20261006-150958/`
(`.drp` + `Project.db` snapshot)

---

### 📋 รายละเอียดทางเทคนิค

**Commit หลัก**

| Commit | รายละเอียด |
|---|---|
| `4101c85` | `feat(resolve)`: สคริปต์นำซับเข้า Resolve + ตรวจอ่านกลับ |
| `75e62e0` | `fix(resolve)`: เปิดใช้ไทม์ไลน์เป้าหมายก่อนนำเข้า (แก้ 0/3) |
| `c9ff732` | `docs(sdd)`: ปิดงานนำซับ + สไตล์ Mitr Font |
| `c6c0ef5` | `docs`: `TOOLING.md` |
| `4b765ff` | `docs+skills`: เหลือ Google provider เดียว + ติดตั้งสกิลที่ขาด |
| `bc6d902` | `docs`: วินิจฉัย `/grill-with-docs` |
| `f6393dc` | `chore`: ย้ายไลบรารี `aomimama_*` เข้าโปรเจกต์ |
| `0bc6194` | `chore(release)`: v0.3.0 |

**กับดักสำคัญที่เจอ (บันทึกไว้ในสกิลแล้ว)**

1. `AddTrack` / `AppendToTimeline` ทำงานกับ **ไทม์ไลน์ที่ active** ไม่ใช่ object ที่เรียกผ่าน
   ต้อง `SetCurrentTimeline` ก่อน — ถ้าลืมจะได้ 0/3 โดยไม่มี error
2. `ImportMedia` **cache ตาม path** — แก้ SRT แล้ว import ซ้ำจะไม่เห็นของใหม่
3. ตรวจสไตล์ด้วยการ grep `EffectFiltersBA` **ไม่ได้** เพราะอยู่ใน zstd ที่บีบอัด
   ต้องเทียบ blob กับ snapshot
4. `scriptapp('Resolve')` คืนค่า `None` เป็นระยะ ต้อง retry
5. โปรเจกต์อาจกลายเป็น "Untitled Project" ได้ สคริปต์จึงปฏิเสธการเขียนถ้าไม่ใช่เป้าหมาย

**ข้อจำกัดที่ยังเหลือ**

- **ซับยังไม่ผ่านการตรวจจากคน** — ทุกไฟล์เป็น `approved: false` ยังไม่มีใครฟังเทียบเสียงจริง
- 49 ไฟล์มาจาก **7 โมเดลต่างกัน** เพราะโควตาฟรีหมดระหว่างทาง ต้องสลับอัตโนมัติ
  (9 ไฟล์ใช้ `gemini-2.5-flash` ซึ่งอ่อนที่สุดในชุด)
- **14 cue มี flag เรื่องเวลา** (`timestamp_beyond_duration`, `start_clipped_to_previous`,
  `overlap_merged`) — ข้อความครบ แต่เวลาที่แสดงถูกปรับ
- **ไทม์ไลน์ 11** เป็นเสียงเกมล้วนไม่มีเสียงพูด (ตรวจสเปกตรัม: zcr 1595 Hz,
  ช่วงเงียบ 0 %) ได้ 1 cue ซึ่งเป็นของจริง
- ไฟล์ WAV ใน `runs/*/audio/` ถูก ignore — ต้องเรนเดอร์ใหม่ถ้าต้องใช้
