# Production: Voiceover Pipeline (`voice.py` & `words.py`)

## Local TTS (`Kokoro-82M` via `kokoro-onnx`)
- Outputs 24 kHz mono WAV (`data/narration.wav`) + exact sentence/clause timestamps (`data/lines.json`).
- **Voice Casting by Format:**
  - `tall-tale-3d`: `am_michael` (`1.05x`) or `am_puck` (`1.05x`)
  - `deep-dive-3d`: `am_michael` (`1.0x`)
  - `inside-out`: `am_michael` or `af_heart` (`1.0x`)
  - `stick-story`: `am_puck` (`1.05x`)
  - `night-file-3d`: `am_onyx` (`0.95x`)
  - `paper-atlas`: `bm_george` (`1.0x`)
- **Human Voiceover Mode:** Pass `--audio path/to/recording.m4a` to `words.py` to transcribe and align custom human narration via `faster-whisper` (`small.en`).
- **Resampling Guarantee:** `tools/mix.py` resamples all 24 kHz narration cleanly to `48000 Hz` stereo before muxing to prevent playback anomalies on mobile devices.
