# Gatekeepify

**Prove you listened first.**

Gatekeepify tracks your Spotify listening history and lets you competitively compare with friends. Settle the debate with timestamps, not opinions.

## What It Does

- **Track listening history** automatically via Spotify API polling every 15 minutes
- **Upload your full history** from Spotify's data export for years of data
- **Compare with friends** -- see who discovered an artist first, with verified vs. self-reported badges
- **12 competitive awards** -- Crown, Archaeologist, Patient Zero, The Obsessive, Night Owl, Genre Snob, and more
- **Head-to-head matchups** -- compare all metrics against any friend
- **Discover new music** -- see what friends are listening to, find artists you're late on, track rising artists
- **Predicted Spotify Wrapped** -- your year-in-review, available any time with historical data
- **Artist deep-dives** -- listening timeline charts, Last.fm global stats, gatekeep comparison, challenge cards
- **Data integrity** -- 5-layer fraud detection including release date validation, anomaly detection, and trust scores

## Tech Stack

**Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, Celery + Redis, spotipy

**Frontend:** Next.js 14, TypeScript, Tailwind CSS

**Deployment:** Railway (backend + PostgreSQL + Redis), Vercel (frontend)

**CI:** GitHub Actions runs 199 tests on every push

## Architecture

```
Frontend (Vercel)          Backend (Railway)
Next.js + Tailwind    -->  FastAPI + SQLAlchemy
                           |
                     PostgreSQL (Railway)
                           |
                     Celery Worker + Beat
                           |
                     Redis (Railway)
                           |
                     Spotify API + Last.fm API
```

Three processes run in a single Railway container via supervisord:
- **Web server** (uvicorn) -- serves the API
- **Celery Worker** -- executes background tasks
- **Celery Beat** -- schedules periodic polling and award computation

## Features

### For Users
- Sign in with Spotify, start tracking immediately
- Upload Spotify data export for full history
- Dashboard with top tracks, artists, genres by time period
- Dedicated artist pages with cover art, listening timeline, and gatekeep comparison
- Wrapped predictions for any year
- Trophy case with 12 award categories
- Head-to-head comparisons with friends
- Music discovery feed (friends' finds, trending, "you're late on...")
- Invite friends via shareable links

### For Data Integrity
- Listen source tagging (API-verified vs. self-reported export data)
- Release date validation (reject listens before a track existed)
- Retroactive validation when track metadata is backfilled
- Statistical anomaly detection (rapid-fire, bot-like spacing, single-day dumps, backdated clusters)
- Trust scores per user (0-100)

### For Scale
- Batched polling with priority ordering (least recently polled first)
- Redis distributed lock prevents overlapping poll cycles
- Inter-user delay respects Spotify rate limits
- Designed for 10k+ users

## Development

```bash
# Install dependencies
source env/bin/activate
pip install -r requirements-server.txt

# Run tests (no external services needed)
python -m pytest tests/test_app/ -v

# Run the server locally
uvicorn app.main:app --reload
# Swagger UI at http://localhost:8000/docs

# Run Celery (requires Redis)
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info
```

## License

MIT
