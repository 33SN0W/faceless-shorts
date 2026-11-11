# Research: Topic Discovery & Scoring

## 1. Discovery Sources
Explore high-signal sources before proposing topics:
- **Discovery leads (initial spark only):** Google Trends, Wikipedia ("List of unusual deaths", "Confidence tricks", historical events), Reddit (`r/todayilearned`, `r/AskHistorians`, `r/Damnthatsinteresting`).
- **Verification & depth (mandatory before scripting):** Britannica, Smithsonian Magazine, National Geographic, BBC / NYT / Chicago Tribune / Guardian archives, FBI Vault, NASA / NIH / CDC / Red Cross, peer-reviewed journals.

## 2. Originality Check (Mandatory)
Run before committing to a topic:
```bash
bash scripts/py scripts/studio.py check-originality --topic "<topic>"
```
This scans all existing projects in `~/faceless-shorts/*` (`script.json`, `research.json`, `metadata.json`) and flags duplicate or overly similar topics.

## 3. Seven-Factor Topic Scorecard (0–10 each)
Score via `studio.py score-topic`:
1. **Curiosity Potential** (weight 1.5): Does the premise break an assumption immediately?
2. **Originality** (weight 1.3): Fresh angle not overdone on Shorts?
3. **Emotional Engagement** (weight 1.2): Surprise, humor, awe, tension, or schadenfreude?
4. **Shareability** (weight 1.1): Would a viewer send this to a friend ("Wait till you hear this")?
5. **Visual Potential** (weight 1.3): Clear physical actions, contrasts, maps, or x-ray moments?
6. **Storytelling Potential** (weight 1.2): Clean hook → escalation → twist/payoff arc?
7. **Factual Reliability** (weight 1.4): Documented across ≥2 reliable primary/secondary sources?

Minimum recommended score to greenlight: **7.5 / 10**. Topics with reliability < 7.0 are rejected or pivoted.
