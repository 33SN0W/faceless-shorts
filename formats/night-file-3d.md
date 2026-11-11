# Format 5: Night File 3D (`night-file`)

**Role in 33SN0W:** Atmospheric investigative storytelling for mysteries and true historical crimes.

## Use Cases
- Unsolved mysteries & aviation/maritime vanishings
- Strange historical crimes & cold-case artifacts
- Creepy historical incidents & unexplained phenomena
- Suspenseful real-world investigations

## Visual Direction
- **Dark 3D Realism & Chiaroscuro:** One primary practical light source with visible volumetric light cone (`SETS.lightCone()`); deep atmospheric darkness and fog everywhere else.
- **Subject Isolation:** Faceless 3D human figures (`Human({ face: false })`) — witnesses in near-black with subtle rim light (`witnessMat()`), while the central subject glows crimson (`subjectMat()`).
- **Evidence Inserts:** 2D case files, flight/train tickets, polaroids, redacted documents, and red marker circles (`K.redCircle`), plus top-left typewriter date stamps (`K.dateStamp`).
- **Camera Language:** Slow, tense push-ins and drifts (3–5 s shots), wider lenses (`fov: 58`) in cramped interiors to avoid blocked dark frames.

## Ethical & Factual Guardrails (Strict)
- **No sensationalism & no gore:** Never depict graphic violence or weapons.
- **Respect victims & living individuals:** Never fabricate details, speculate recklessly, or accuse a living person. Cite primary records (FBI archives, court records, verified outlets) in `research.json`.

## Narrative Pacing & Audio
- **Duration:** `35–55 s`.
- **Default Voice & Music:** `am_onyx` (`0.95x`), `"tension"` + sparse `tock`, `thud`, `whoosh`.

## Art Style Compatibility
- Best with: `vintage-film`, `cgi-motion`, `comic-art`, `ps2-retro`, `glow-sketch`, `chalkboard`, `minimal-line`.
