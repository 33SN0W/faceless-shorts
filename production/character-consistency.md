# Production: Character & Visual Consistency (`characters.json`)

Every project locks recurring characters, props, and world lighting inside `<project>/characters.json` before rendering shots.

```json
{
  "protagonist": "character_id",
  "characters": [
    {
      "id": "victor",
      "display_name": "Victor Lustig",
      "role": "protagonist",
      "clothing": "Tailored charcoal suit, crimson bow tie, black top hat",
      "facial_features": "Neat handlebar mustache, brass monocle over left eye",
      "body_proportions": "Tall Tale standard 1.75m Toon cut-out",
      "color_palette": { "body": "#3A3A48", "hat": "#1E1B29", "accent": "#D8343F" },
      "accessories": ["monocle", "tophat", "cane"],
      "personality": "Smooth, overconfident, manipulative charm",
      "expression_library": ["smug", "sly", "proud", "laugh", "neutral"],
      "reference_spec": "Reuse exact LOOK object across every set (ST, HC, TR) without changing hat or palette"
    }
  ],
  "environment_locks": {
    "lighting_rig": "Consistent key/fill orientation per set",
    "scale_reference": "Characters 1.75m; two-shot horizontal spacing <= ±0.45m in 9:16"
  }
}
```

## Engineering Rules for Consistency
1. **Single Look Definition:** Define one `LOOK` entry per character in `src/shots.js` matching `characters.json` and instantiate all set clones from that single definition (`person('victor')`).
2. **Prop Continuity:** Props held across scenes (e.g., `$1 bill`, `brass keys`, `shell crate`) use identical dimensions, colors, and hand attachment (`holdL`/`holdR`).
3. **9:16 Safe Framing:** Keep two-shots within `x = ±0.45 m` at `z ≈ 3.5 m` distance so faces are never clipped on the left/right edges, and anchor 2D overlay badges at `y = 290..360` (never over faces).
