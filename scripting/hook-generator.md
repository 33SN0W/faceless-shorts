# Scripting: Three-Hook Generator

## Rules for Opening Hooks (0–2.5 seconds)
YouTube Shorts **Viewed vs. Swiped Away** is decided in the first 1–2 seconds.
- **Immediate Intrigue:** Open directly with the sharpest contrast, impossible action, specific date + absurdity, or visceral "What happens if…?" premise.
- **Forbidden Cliché Openers (automatically flagged by `qa_check.py`):**
  - `"Hey guys..."` / `"What's up guys..."`
  - `"Welcome back..."`
  - `"Today we are going to discuss..."` / `"Today we're talking about..."`
  - `"In this video..."`
  - `"Did you know..."` (weak filler; state the surprising fact directly!)
- **Truthfulness:** Never exaggerate numbers or invent fake stakes in the hook.

## Mandatory 3-Hook Workflow
For every topic, generate **three distinct hook angles** inside `script.json` (`"hooks": [...]`) and select the strongest:
1. **Absurd Action / Contrast Hook:** *"In 1925, a con man sold the Eiffel Tower for scrap metal."*
2. **Stakes / Paradox Hook:** *"The cheapest way to buy a four-million-dollar bank is with a single one-dollar bill."*
3. **Curiosity / Scenario Hook:** *"If you tie forty-two weather balloons to a lawn chair, you don't hover—you enter airline airspace."*

Log which hook pattern was used (`"hookType": "absurd-action | paradox | curiosity | countdown | mystery-date"`) so `analytics.py` can learn which hook styles drive the highest **Viewed %**.
