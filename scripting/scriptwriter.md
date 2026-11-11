# Scripting: Conversational Scriptwriter

## Narration & Spoken-English Rules
- **Talk like a sharp storyteller to a friend:** Use natural connectors (*"See,"*, *"Turns out,"*, *"Only problem?"*, *"So instead,"*) rather than robotic AI transitions (*"Furthermore,"*, *"Additionally,"*, *"In conclusion,"*).
- **Short, crisp sentences:** One main idea per clause.
- **No repetitive rhetorical questions:** Limit questions to 1 (hook or key turn).
- **Numbers spelled as spoken:** Write `"nineteen eighty-two"`, `"forty-two"`, `"five thousand dollars"` in `"text"`, and clean digits `"1982"`, `"42"`, `"$5,000"` in `"caps"`.
- **Line = Cut, Sentence = Voice Pass:** Split multi-clause sentences across 2–3 lines (`text` ends with `,` or space, final clause ends with `. ? !`) so `voice.py` speaks the whole sentence smoothly while visuals cut dynamically on clauses.

Validate script length, clichés, hooks, and sources anytime:
```bash
bash scripts/py scripts/studio.py check-script <project>
```
