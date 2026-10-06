# SDD ledger — plan: .hermes/plans/2026-10-06_100141-aomimama-all-timeline-subtitles.md

Execution approved by user: โอเค เริ่มทำได้เลย

Confirmed policy: natural phrase captions; split long text without losing words or severing names/negations. No hard 3-word/1.5-second limit.

Workspace: C:/Users/warit/AppData/Local/hermes/cache/scratch/aomimama-subtitle-worktree (branch work/aomimama-subtitles); no commits/push authorized.

Preflight shared interfaces:
| Producer | Consumer | Check |
|---|---|---|
| inventory | renderer | UUID, timeline start/end/fps; 49 baseline rows; all tracks empty |
| renderer | ASR | mix WAV from full timeline, 16 kHz mono after conversion, duration matches baseline |
| ASR | caption core | raw segment words preserve timestamps and text; weak spans flagged |
| caption core | transcript reviewer | proposal only; no silent truncation, approval after review |
| reviewed cues | importer/readback | UUID identity, SRT text/timing and original clip signatures |

Ruling: authoritative user phrase policy supersedes all old 3-word/1.5-second draft code/tests — those would contradict the approved design — cost if wrong: re-splitting sidecar cues before import.
Ruling: use documented Resolve render API if proven on pilot instead of 49 manual Deliver jobs — it produces the same timeline audible mix without retime guesses — cost if wrong: rerender audio, no subtitle import until mix validation.
Ruling: implementation isolated in an external worktree; main stays untouched by helper code; no automatic commits — protects unrelated installer/plan changes — cost if wrong: helper files remain in worktree until explicit integration.

Verified setup:
- fresh Python 3.11 venv .venv-aomimama; faster-whisper/pythainlp installed.
- inventory read and saved at manifest.json: exactly 49 timeline UUIDs, zero subtitle tracks.
- initial-state.json captured active timeline UUID, playhead, page and render jobs.
- SaveProject True; ExportProject True; DRP readback non-empty 1,066,230 bytes.
- Backup: backups/aomimama-2026-09-p1-before-subtitles.drp.
- GUI capture through cua-driver UIA currently times out on Resolve Qt tree; Resolve scripting remains responsive.
- GetAudioRenderFormats reports Wave/wav; GetAudioRenderCodecs('wav') reports Linear PCM/lpcm; no pre-existing render jobs.

Implementation subagent completed core + ASR helper, four new untracked source/test files in isolated worktree; implementation-report.md and implementation-tests.log retained. Parent full-suite rerun: 17 tests OK in 1.289 sec. Independent helper review delivered FAIL / CHANGES REQUIRED: timed whitespace holds captions over silence; nested internal intervals truncate occupied time; malformed raw cache with matching metadata can become empty speech; multiline text can inject SRT blocks. Fix subagent delivered: all4 issues repaired with regressions; actual timeline4 root cause zero-duration lexical tail at24.22s, handled without text loss with reconciliation flags. Parent independently ran25 tests OK in0.636sec. Scoped re-review delivered PASS for spec and task/code quality: all4 findings ADDRESSED, eight targeted tests passed, real transcript4 replay 26 cues/26 blocks preserving417 non-whitespace characters; raw unchanged. Report scoped-review.md verified by parent. Helper task complete for code scope, NOT for speech accuracy. Parent exclusively owns Resolve.

User selected an audio-capable provider such as Gemini for transcription/QC before import. Connection discovery: Gemini auth status logged out; OpenRouter saved credential metadata reports auth failed403. No auxiliary settings changed. Browser real-profile route refused because Edge profile locked; alternate isolated Gemini browser reached sign-in. Vault contained no saved login; save-login masked prompt was declined, so do not request saved password again this turn. User approved closing all Edge windows. `hermes browser close-profile` initially left a background Edge tree alive; authorized `taskkill /IM msedge.exe /T /F` then readback showed no matching processes. Retried real-profile Gemini browser session successfully, but Gemini shows Sign in. Guest Upload & tools says 'Sign in to try tools' and exposes no file input. Edge's copied profile therefore does not supply a logged-in Gemini session. No upload attempted. Waiting for user-controlled Google sign-in or secure Gemini API setup; do not request credentials in chat. No audio uploaded to Gemini and no cloud charges initiated. Provider authentication remains an external blocker; do not call native ASR drafts audio-verified.

Working audio-capable route discovered: Nous Portal catalog (425 models) includes google/gemini-3.8-flash with explicit audio input modality. `hermes proxy start --provider nous` listening 127.0.0.1:8645. Pilot call: base64 WAV of timeline 1 (90.6s true duration) to gemini-3.8-flash returned JSON, audio_available true, accurate_timestamps, 12 speech segments over 4.14–87.78s, explicit [ฟังไม่ชัด] at 21.0–23.5 (voice-effect game name) and 86.6–87.78 (tail cut). Gemini duration 88.0 vs true 90.6 — timing within ~2.6s tolerance, consistent with speech-only coverage of a mostly-game-audio file. Content far more coherent than all Whisper passes. Saved review/gemini-api-pilot-response-v1.json. NO subtitle approved yet; no batch run until user confirms; proxy cost billed against Nous Portal.

Current verified progress:
- Audio render Complete and mono 16 kHz duration readback passed for ALL 49 timeline UUIDs. audio-progress.json has 49 verified indices, no pending jobs.
- Real CUDA cached large-v3 smoke completed, not fake inference: pilot1 draft 20 cues; timelines2/3 drafts 24/20 cues. Raw transcript4 persisted but draft generation failed validator (invalid/overlapping timing); timeline5 not processed.
- All drafts unapproved; NO subtitle tracks created. Poor Thai text and implausible long single-word cards are blockers, not acceptable captions.
- Pilot alternative passes ran cached large-v3-turbo raw+filtered and cached bjak/distill-whisper-th-large-v3. Outputs saved separately; turbo still garbled, bjak returned repeated hallucinations/null timestamps. None approved.
- Attempted actual audio QC using video_analyze on a 90.6-second black video wrapper with real WAV audio. Tool rejected: Codex Responses does not support video_url input. No listening-based accuracy claim may be made from that failed call.
- Diagnostic original-source decode at offset 195.05 s compared against rendered mix: correlation 0.9999599074071611; RMS 772.9082311149012 vs 772.9618104422623. Render closely matches source; bad ASR is not evidence that the render changed speech.
- Re-read all49 baseline timeline IDs/name/start/end and video/audio signatures unchanged, subtitle tracks0. Original active timeline/playhead/edit page restored and project saved; baseline-verification.json retained.

Integration observations: ReplaceExistingFilesInPlace False is documented but SetRenderSettings returns False for that key in this version; omit it and enforce new paths/absence checks instead. Audio codec readback is literal 'lpcm', not display label 'Linear PCM'.

