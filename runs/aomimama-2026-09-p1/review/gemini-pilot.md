# Gemini web audio QC — pilot timeline 1

Scope: only audio/4720b0bd-a3f4-4106-bdcb-18101a54c2f6.wav from the rendered timeline mix. User switched account in Chrome and authorized continuing. Visible Gemini account identity selected by user; no account switch or login performed by agent.

Browser: existing Google Chrome, user session; browser automation default profile still Edge, so the user-selected Chrome surface was operated through accessibility/native file-dialog controls. No cookie/password reads, no subscription/purchase/settings change.

Upload was read back as a WAV attachment, then prompt was read back in the composer before sending. Posted message and attachment verified in exact conversation:
https://gemini.google.com/u/1/app/5f53087f578acb5d

Submitted prompt:
ตรวจฟัง WAV ที่แนบจริงแล้วถอดบทพูดภาษาไทยครบทั้งไฟล์เป็นวลีธรรมชาติ พร้อมเวลาเริ่มและจบเป็นวินาทีจากต้นไฟล์ ไม่เติมคำ ไม่เดาชื่อเกม ไม่ใส่ข้อความช่วงเงียบ ถ้าไม่ได้รับเสียงให้บอกตรง ๆ และหยุด ถ้าฟังไม่ชัดให้ใช้ [ฟังไม่ชัด] ส่ง JSON ที่มี audio_available, duration_seconds, segments [{start,end,text,uncertain}] และ uncertainties ระบุด้วยว่าเวลาที่ให้เป็นการประมาณหรือวัดได้จริง

At last readback: Gemini Flash Extended analyzing, no final transcript collected yet. Source WAV duration independently verified90.6seconds; provider must match source and explicitly establish actual audio availability before batch QC. No subtitle approved or inserted based on a loading spinner.
