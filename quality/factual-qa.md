# Quality Assurance: Factual & Story QA

Automated by `bash scripts/py scripts/qa_check.py <project>`:

## Factual QA Checks
1. **Source Presence:** `script.json` `"sources"` or `research.json` contains ≥2 reliable sources with valid URLs or archival citations.
2. **Claim Grounding:** Key numbers/dates in `script.json` cross-checked against `research.json` `"claims"`.
3. **Disputed Information Guard:** Any claim marked `"disputed": true` must not assert an absolute unverified figure.

## Story QA Checks
1. **Hook Audit:** Opening line (`lines[0]`) contains zero cliché openers (`hey guys`, `welcome back`, `in this video`, `today we are going to`).
2. **Alternative Hooks:** `script.json` `"hooks"` includes 3 distinct alternatives when generated via studio workflow.
3. **Word Budget & Duration:** Total word count matches declared `durationTier` (`short` 50–85w, `standard` 85–130w, `extended` 125–180w) and total runtime stays inside target bounds (`20–60 s`).
4. **Cut Pacing:** Individual scene durations are neither too short (`< 0.7 s`) nor overly static (`> 6.0 s`).
