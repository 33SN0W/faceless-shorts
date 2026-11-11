# Research: Fact Checking & Verification

## Strict Truthfulness Rules
- **Zero Fabrication:** Never invent statistics, dollar figures, dates, quotations, casualty counts, or legal outcomes.
- **No Fiction Framed as Fact:** Fictional legends or urban myths must never be presented as verified true stories.
- **Disputed Details Protocol:** When reputable sources disagree on a figure (e.g., exact pound/dollar count or date), record the discrepancy in `research.json` (`"disputed": true`), use the most widely corroborated consensus figure, and phrase carefully (e.g., *"over three million"*, *"around 16,000 feet"*).
- **Multi-Source Corroboration:** Every key numerical or historical claim requires ≥2 independent reliable sources (Wikipedia or Reddit alone is never sufficient as final verification).

## Verification Workflow
1. Search primary/authoritative outlets (`search_web` / archives).
2. Map each factual claim in the script to specific supporting source URLs inside `<project>/research.json`.
3. Run `bash scripts/py scripts/qa_check.py <project>` to confirm claims, dates, and sources validate before rendering.
