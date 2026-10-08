# Thai Gaming Subtitles

Turns the speech in Thai gaming clips into reviewed subtitle cues that sit on the
edited timelines of a DaVinci Resolve project.

## Language

**Clip**:
A piece of source gameplay footage with commentary, before editing.
_Avoid_: Video, recording

**Timeline**:
An edited sequence in the Resolve project that receives subtitles. One Timeline is one unit of work.
_Avoid_: Job, project, sequence

**Run**:
One batch of Timelines processed together, with its own manifest and evidence.
_Avoid_: Job, batch

**Transcript**:
The machine-heard speech of one Timeline, as timed segments, before any cleanup.
_Avoid_: Subtitle, caption

**Segment**:
One timed stretch of speech in a Transcript.
_Avoid_: Line, chunk

**Cue**:
One subtitle shown on screen for a span of time. Cues are built from Segments.
_Avoid_: Caption, line, card

**Draft**:
The set of Cues for a Timeline that no person has checked against the speech yet.
_Avoid_: Final, approved

**Approved**:
A Draft that a person has checked against the speech and accepted.
_Avoid_: Verified, passed

**Uncertain span**:
A stretch of speech the transcriber could not hear clearly, marked rather than guessed.
_Avoid_: Gap, error

**Phrase style**:
Cues that follow natural spoken phrases of any length. The current default.
_Avoid_: Sentence mode

**Card style**:
The older gaming style of very short Cues of one to four Thai words. Kept only in the archived K404 batch.
_Avoid_: Short mode

**Subtitle track**:
Resolve's native subtitle lane on a Timeline. The only place Cues may live; never Text+ or titles.
_Avoid_: Caption track, text layer

**Preset**:
A saved subtitle look (font, size, position) applied to a whole Subtitle track, chosen by Timeline orientation.
_Avoid_: Style, theme

**Plausibility check**:
The automatic test of whether audio exists under each Cue. It never proves the words are right; only a person can Approve.
_Avoid_: Verification, QA pass
