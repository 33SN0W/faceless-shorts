# Quality Assurance: Audio QA

Automated by `bash scripts/py scripts/qa_check.py <project>`:
1. **Voiceover Completeness:** Confirms `data/narration.wav` exists and matches `data/lines.json` duration (`±0.25 s`).
2. **Silence Detection:** Scans `data/mix.wav` with `numpy` RMS envelope (`50 ms` windows); fails if any silent gap exceeds `2.0 s` inside the active body (`0.5 s` after start to `1.5 s` before end).
3. **Clipping Check:** Verifies peak sample amplitude stays below `-0.2 dBFS` (`max_abs < 0.98`) and mean volume sits in the healthy `-22 dBFS` to `-14 dBFS` broadcast sweet spot.
4. **Music-to-Voice Balance:** Checks voice RMS (`-19 dBFS`) vs. ducked background music level (`<= -24 dBFS` ducked) so narration remains crisp over music.
5. **Subtitle Sync Verification:** Confirms `data/words.json` word count aligns with `script.json` spoken words and timestamps are strictly monotonic (`s <= e`).
