# Quality Assurance: Visual QA

## Automated Frame Inspection (`qa_check.py`)
1. **Contact Sheet Generation & Visual Review:** Never ship without visually reading `review/all.jpg`.
2. **Black Frame Detection:** Samples frames from `renders/*.mp4` (or `review/all.jpg`) via `ffmpeg` + `numpy` and flags any unexpected pure-black interior frames (`mean luma < 8.0` outside the 0.25s start/end fade windows).
3. **Frozen/Duplicate Scene Check:** Computes frame-to-frame luminance delta across shots; warns if consecutive scenes show zero camera/subject movement (`MAD < 0.5`).
4. **Character Consistency Verification:** Verifies `characters.json` exists and that recurring characters referenced in `storyboard.json` match defined `LOOK` entries in `src/shots.js`.
5. **Safe-Area Subtitle Audit:** Checks `CAP.y` / rendered caption bounds stay within `y <= 1480` and `maxW <= 920` (clear of Shorts & Reels UI).
