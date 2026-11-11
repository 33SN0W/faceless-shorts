# Analytics: Performance Tracking (`scripts/analytics.py`)

Data store: `~/.faceless-shorts/analytics.json` (never fabricated; records actual exported video specs and user-supplied or API-fetched metrics).

## Tracked Dimensions
- **Production Attributes:** `project`, `title`, `format`, `artStyle`, `topicCategory`, `hookType`, `durationSec`, `loopEnabled`, `uploadDate`, `platform` (`youtube` | `instagram`).
- **YouTube Shorts Metrics** (when YouTube Analytics API / YouTube Studio CSV/values are supplied):
  - `views`, `engaged_views`
  - `viewed_pct` vs. `swiped_away_pct` (Primary hook survival indicator)
  - `avg_view_duration_sec`, `avg_pct_viewed`
  - `watch_time_hours`, `subscribers_gained`
  - `likes`, `comments`, `shares`
- **Instagram Reels Metrics** (when Meta Insights permissions/data are provided):
  - `plays`, `reach`, `avg_watch_time_sec`, `saves`, `shares`, `likes`, `comments`

## CLI Commands
```bash
# Log a newly rendered video
bash scripts/py scripts/analytics.py log-video ~/faceless-shorts/my-short

# Record actual analytics observed from YouTube Studio / API
bash scripts/py scripts/analytics.py import-metrics --project my-short --platform youtube --views 12500 --engaged-views 9100 --viewed-pct 72.8 --avg-duration 34.2 --subs 45
```
