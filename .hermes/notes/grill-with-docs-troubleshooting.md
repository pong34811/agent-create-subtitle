# /grill-with-docs เรียกไม่ทำงาน — สาเหตุและวิธีแก้

ตรวจเมื่อ 2026-10-06 บน Hermes ที่ `C:\Users\warit\AppData\Local\hermes\hermes-agent`

---

## สรุปสาเหตุ (มีหลักฐานยืนยัน)

**ไม่ใช่บั๊กของสกิล** — สกิลผ่านตัวกรองทุกข้อ และตัวสแกนก็เจอมันจริง
ปัญหาคือ **แคชของ process ที่กำลังรันอยู่** ซึ่งถูกสร้างก่อนที่สกิลจะถูกติดตั้ง

หลักฐาน:

```
scan_skill_commands() -> 68 commands
   /domain-modeling -> domain-modeling
   /grill-with-docs -> grill-with-docs
   /grilling -> grilling
```

ตัวสแกน **สด** เห็นครบ แต่ process ที่กำลังคุยกับคุณอยู่เห็นแผนที่เก่า

---

## ลำดับเหตุการณ์ที่ทำให้พัง

| เวลา | เหตุการณ์ |
|---|---|
| 09:55 | เริ่ม session นี้ → Hermes สแกนสกิลและแคชผลไว้ |
| 10:08 | ติดตั้ง `grill-with-docs` (แคชไม่รู้) |
| 15:24 | ติดตั้ง `grilling` + `domain-modeling` (แคชไม่รู้) |
| 15:30 | คัดลอกเข้า profile dir (แคชก็ยังไม่รู้) |

แคช `_skill_commands_by_key` ใน `agent/skill_commands.py` จะถูกล้างเฉพาะเมื่อเรียก
`reload_skills()` หรือเริ่ม process ใหม่

---

## หลักฐานว่า `/reload-skills` แก้ได้จริง

จำลอง process ที่มีแคชเก่า แล้วเรียก `reload_skills()`:

```
BEFORE reload, visible grill commands: []
added : 83
grill/domain in added:
   domain-modeling, grill-with-docs, grilling
AFTER reload, visible grill commands: ['/grill-with-docs', '/grilling', '/domain-modeling']
```

---

## วิธีแก้ (เลือกอย่างใดอย่างหนึ่ง)

**วิธีที่ 1 — เร็วที่สุด พิมพ์ในแชทนี้เลย**

```
/reload-skills
```

`/reload-skills` มีอยู่ใน CLI (ไม่ใช่ `cli_only`) alias คือ `/reload_skills`
จะสแกนใหม่และรายงานว่าอะไรถูกเพิ่ม

**วิธีที่ 2 — เริ่ม session ใหม่**

ปิดแล้วเปิด Hermes ใหม่ แคชจะถูกสร้างใหม่พร้อมสกิลครบ

**วิธีที่ 3 — ตรวจสอบก่อนว่าเห็นแล้วหรือยัง**

```
/help skills
```

จะแสดงรายการ skill commands ทั้งหมด ถ้าเห็น `/grill-with-docs` แสดงว่าพร้อมใช้

---

## ทำไมถึงไม่เจอสกิลตอน plan mode

ตอนอยู่ใน plan mode ผมเรียก `skill_view("grill-with-docs")` แล้วได้ "not found" —
ด้วยเหตุผล**สองชั้นที่ซ้อนกัน** ซึ่งตอนนั้นแก้ไปแล้วชั้นเดียว:

1. ~~สกิล `grilling` และ `domain-modeling` ไม่มีในเครื่อง~~ → ติดตั้งแล้ว 15:24
2. ~~สกิลอยู่ใน `.agents/skills` ของโปรเจกต์ ซึ่ง Hermes ไม่โหลด~~ → คัดลอกเข้า
   profile dir `~/AppData/Local/hermes/skills/` แล้ว 15:30
3. **แคชของ process ยังไม่ถูกล้าง** ← เหลือชั้นนี้ ที่ต้อง `/reload-skills`

---

## ตัวกรองที่สกิลต้องผ่าน (ตรวจแล้วผ่านหมด)

จาก `agent/skill_commands.py::_scan_skill_md` — ถ้าข้อใดไม่ผ่าน สกิลจะไม่ถูก
ลงทะเบียนเป็น `/command` โดยไม่แจ้งเตือนชัดเจน

| ตัวกรอง | ผลของ `grill-with-docs` |
|---|---|
| `skill_matches_platform(frontmatter)` | ผ่าน (True) |
| `skill_matches_environment(frontmatter)` | ผ่าน (True) |
| `skill_matches_apps(frontmatter)` | ผ่าน (True) |
| ชื่อชนกับคำสั่งระบบ (`skill_command_collision_note`) | ไม่ชน (None) |
| ชื่อซ้ำกับสกิลอื่น (`seen_names`) | ไม่ซ้ำ |
| slug ไม่ว่าง (`slugify_skill_name`) | ได้ `grill-with-docs` |

ผลลัพธ์: `frontmatter keys: ['name', 'description', 'disable-model-invocation']`
— `disable-model-invocation: true` **ไม่ได้บล็อก** slash command แต่บล็อกการที่
โมเดลเรียกสกิลเองโดยไม่ถูกสั่ง (ซึ่งเป็นเจตนาของสกิลนี้)

---

## ข้อสังเกตเรื่องตำแหน่งสกิล

Hermes สแกน 3 ที่ (เรียงตามความสำคัญ):

| ที่ | พาธ |
|---|---|
| project | `<project>/.hermes/skills`, `<project>/.agents/skills` |
| home | `C:\Users\warit\AppData\Local\hermes\skills\<category>\` |

**สกิลที่ติดตั้งด้วย `npx skills add` จะไปอยู่ที่ project (`.agents/skills`)** ซึ่ง
ถ้าเปิด Hermes จากโปรเจกต์อื่นจะมองไม่เห็น ถ้าต้องการใช้ทุกโปรเจกต์ให้วางที่ home
(`~/AppData/Local/hermes/skills/`) — ซึ่งคัดลอกให้แล้วทั้ง 3 ตัว

---

## บั๊กเล็กที่ไม่เกี่ยวข้องแต่เจอระหว่างทาง

```
Failed to parse ...\plugins\superpowers\.muse-plugin\plugin.json:
plugin.json declares an unsupported or missing Agent Plugins schema
```

เป็นคำเตือนของ plugin `superpowers` (ไฟล์ `.muse-plugin/plugin.json` schema ไม่ตรง)
**ไม่เกี่ยวกับ grill-with-docs** และไม่กระทบการทำงาน — แต่ถ้าต้องการให้ log สะอาด
สามารถแจ้งได้

---

## คำสั่งที่ใช้ตรวจซ้ำ

```bash
cd /c/Users/warit/AppData/Local/hermes/hermes-agent
venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'.')
from agent.skill_commands import scan_skill_commands
c=scan_skill_commands()
print('total:',len(c))
print([k for k in c if 'grill' in k or 'domain' in k])
"
```

ผลที่ต้องได้: `total: 68` และ `['/grill-with-docs', '/grilling', '/domain-modeling']`
