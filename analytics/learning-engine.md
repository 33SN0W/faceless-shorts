# Analytics: Continuous Learning Engine

`scripts/analytics.py recommend` analyzes actual historical data in `~/.faceless-shorts/analytics.json` across:
- **Storytelling Format** (`tall-tale`, `deep-dive`, `inside-out`, `stick-story`, `night-file`, `paper-atlas`)
- **Visual Art Style** (`comic-art`, `watercolour`, `glow-sketch`, etc.)
- **Topic Category** & **Hook Type** & **Duration Tier**

## Anti-Vanity Metric Scoring
Raw `views` alone are never treated as success (because a video with a high swipe-away rate can get brief empty autoplay views). The learning score weights:
1. **Hook Survival (`viewed_pct`)** — weight `0.35`
2. **Completion (`avg_pct_viewed`)** — weight `0.35`
3. **Conversion & Depth (`subs / 1000 engaged_views` + shares/saves)** — weight `0.30`

When insufficient performance rows exist (`< 3` videos with imported metrics), the engine explicitly states that API/analytics data is not yet populated and falls back to creative diversity weighting (favoring untried format × art-style pairings).
