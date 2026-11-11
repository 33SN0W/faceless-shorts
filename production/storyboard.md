# Production: Storyboard & Scene Planning (`storyboard.json`)

Before writing `src/shots.js`, generate `<project>/storyboard.json` containing the 14-field production plan for every scene:

```json
{
  "title": "...",
  "format": "tall-tale-3d | deep-dive-3d | inside-out | stick-story | night-file-3d | paper-atlas",
  "artStyle": "comic-art | watercolour | pixel-art | ...",
  "durationTier": "standard",
  "scenes": [
    {
      "scene_number": 1,
      "id": "S01",
      "duration_sec": 3.0,
      "voiceover": "Exact line(s) spoken during this scene",
      "visual_description": "What happens visually in the frame",
      "character_appearance": "IDs from characters.json + attire/state",
      "character_action": "Gesture, pose, mood beat (e.g. smug wink, shocked jump)",
      "background_environment": "3D set / 2D stage & props",
      "camera_angle": "eye-level | low-angle | high-angle | macro",
      "camera_movement": "push-in | crane-down | track-left | whip-pan | slow-drift",
      "lighting": "midday-sun | dark-cone | x-ray-cyan | chalkboard-ambient",
      "animation_instructions": "Key motion keyframes & word-synced triggers (Wd)",
      "transition": "flash-cut | crossfade | swipe | hard-cut",
      "sound_effect": "whoosh + ding on keyword",
      "subtitle_text": "Exact caption chunk(s) with *highlight word"
    }
  ]
}
```

## Pacing Philosophy (Narrative-Driven, Not Mechanical)
- **Let the story dictate shot length:** Fast action/comedy lines = `1.2–2.5 s`; atmospheric mysteries (`Night File 3D`) or complex diagrams (`Deep Dive 3D` / `Paper Atlas`) = `3.0–5.0 s`. **Never** force artificial 2-second cuts when a visual beat needs room to land.
- **Visual Variety:** Alternate wide establishing shots, medium two-shots, reaction close-ups, tracking shots, cutaways, and visual metaphors.
