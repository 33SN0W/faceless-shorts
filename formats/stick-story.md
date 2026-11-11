# Format 4: Stick Story (`stick-story`)

**Role in 33SN0W:** Fast, humorous stick-figure survival guides and hypothetical scenarios.

## Use Cases
- Survival situations (power outages, blizzards, wilderness, rip currents)
- Practical life hacks & emergency protocols
- "What would you do if…?" hypothetical tests
- Everyday problem-solving & safety myths

## Visual Direction
- **Expressive Stick Figures:** Ink-black articulated figures (`K.person` / `K.bigHead`) where oversized expressive white eyes lead every reaction (look → eyebrow/mood → body pose). Night scenes use a subtle warm rim glow (`glow: true`) so characters remain readable against dark backgrounds.
- **Clear Step Demonstration:** Gold numbered step cards (`K.stepCard`) pop in cleanly on each actionable step; green checks (`check`) mark safe choices, red crosses (`cross`) mark dangerous mistakes.
- **Environments:** Illustrated flat rooms (`livingRoom`, `kitchen`, `hallway`) in matching day and night palettes.

## Narrative Pacing & Audio
- **Duration:** `25–45 s`.
- **Shape:** Urgent scenario hook → immediate common mistake (`cross`) → Step 1 / Step 2 / Step 3 (verified against official safety guidance like Red Cross / Ready.gov / CDC) → safe resolution.
- **Default Voice & Music:** `am_puck` (`1.05x`), `"bed"` + `pop`, `whoosh`, `thud`, `slam`, `plop`.

## Art Style Compatibility
- Best with: `minimal-line`, `chalkboard`, `glow-sketch`, `flat-vector`, `comic-art`, `pixel-art`, `explainer-2d`.
