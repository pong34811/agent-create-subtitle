# Use Gemini audio input, not Whisper, for Thai gaming speech

Whisper variants (`large-v3`, `large-v3-turbo`, `medium`, `bjak/distill-whisper-th-large-v3`, Groq-hosted `whisper-large-v3`) returned garbled or invented Thai on noisy game audio across 49 Timelines, while Gemini audio input transcribed the same files cleanly, including game names. We therefore use Gemini as the single provider, with a model fallback chain (newest first) because free-tier quota is per model per day. The Whisper pipeline is archived in `legacy/k404-whisper/`; revisit only with new measurements, not preference.

Consequences: transcripts depend on a cloud API and are not reproducible (the same model on the same audio gave different words, and timestamps up to about 2 s apart, on re-run), so every Draft needs a Plausibility check and a person's Approval before it is trusted.
