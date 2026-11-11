# Research: Source Management (`research.json`)

Every generated video maintains a structured `research.json` alongside `script.json`:

```json
{
  "topic": "Short descriptive topic",
  "category": "historical-scam | science | survival | mystery | history | bizarre-true-story",
  "researched_at": "2026-11-11",
  "topic_score": {
    "curiosity": 9, "originality": 9, "emotion": 8, "shareability": 9,
    "visual": 9, "storytelling": 9, "reliability": 9, "weighted_total": 8.9
  },
  "sources": [
    {
      "id": "S1",
      "title": "Authoritative Source Title",
      "publisher": "Smithsonian / Britannica / CDC / etc.",
      "url": "https://...",
      "retrieved_at": "2026-11-11"
    }
  ],
  "claims": [
    {
      "claim": "Specific historical/scientific statement used in the script",
      "source_ids": ["S1", "S2"],
      "verified": true,
      "disputed": false,
      "notes": ""
    }
  ],
  "disputed_or_uncertain": []
}
```
Scaffold automatically with: `bash scripts/py scripts/studio.py scaffold <project>`.
