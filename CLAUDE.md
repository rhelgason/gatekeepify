# Gatekeepify

## What This Is

A music gatekeeping app. Users track their Spotify listening history and competitively prove they listened to an artist before their friends did. The core value proposition is *comparative timestamp data* -- "I listened to Radiohead 847 times since 2017. You started in 2021. Sit down."

The product is intentionally performative and annoying. That's the point.

## Architecture Overview

The app is mid-migration from a local CLI tool to a web service. Both exist in the repo:

- **`src/`** -- Legacy CLI app (Python, SQLite, crontab, pynput terminal menus). Still functional but not the future.
- **`app/`** -- New FastAPI web API (SQLAlchemy ORM, Celery tasks, JWT auth). This is where all new work goes.

### Backend Stack (app/)
- **FastAPI** -- web framework, serves API + Swagger docs at `/docs`
- **SQLAlchemy 2.0** -- ORM with Alembic migrations
- **Celery + Redis** -- background job scheduling (replaces macOS crontab)
- **spotipy** -- Spotify Web API wrapper
- **Database** -- SQLite for local dev, PostgreSQL for production (SQLAlchemy abstracts both)

### Key Files
- `app/main.py` -- FastAPI entry point
- `app/models.py` -- All ORM models (8 data tables + job_runs)
- `app/schemas.py` -- Pydantic request/response models
- `app/config.py` -- Settings from environment variables
- `app/database.py` -- SQLAlchemy engine/session
- `app/routers/auth.py` -- Spotify OAuth + JWT
- `app/routers/stats.py` -- Top tracks/artists/genres/wrapped (SQL aggregation)
- `app/routers/backfill.py` -- ZIP upload with 5-layer fraud validation
- `app/services/spotify.py` -- Multi-user Spotify API client + token encryption
- `app/services/ingestion.py` -- Data upsert logic for all tables
- `app/celery_app.py` -- Celery config + beat schedule
- `app/tasks.py` -- Periodic tasks: poll_recent_listens, backfill_track_metadata

### Database Schema
8 data tables + 1 job tracking table:
- `dim_all_albums` (album_id PK, album_name, **release_date**)
- `dim_all_tracks` (track_id PK, track_name, album_id FK, duration_ms, is_local)
- `dim_all_artists` (artist_id PK, artist_name)
- `track_to_artist` (composite PK, M:N junction)
- `artist_to_genre` (composite PK, M:N junction)
- `dim_all_users` (user_id PK, user_name, email, **spotify_refresh_token**, created_at, last_poll_at)
- `dim_all_listens` (composite PK: ts+user_id+track_id, **source**, **export_metadata**)
- `job_runs` (id PK, job_name, user_id, started_at, completed_at, status, record_count)

Bold columns are new additions from the architecture overhaul.

## Development Setup

### Run tests (no external services needed)
```bash
source env/bin/activate
python -m pytest tests/test_app/ -v    # New app tests (68 tests)
python -m pytest tests/ -v             # All tests including legacy (99 tests)
```

### Run the FastAPI server locally
```bash
source env/bin/activate
uvicorn app.main:app --reload
# Swagger UI at http://localhost:8000/docs
```

### Run Celery worker + beat (requires Redis)
```bash
# Terminal 1: worker
celery -A app.celery_app worker --loglevel=info
# Terminal 2: beat scheduler
celery -A app.celery_app beat --loglevel=info
```

### Environment variables
Copy `.env.example` to `.env`. Required values:
- `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` -- from Spotify Developer Dashboard
- `JWT_SECRET` -- any random string for signing tokens
- `REDIS_URL` -- `redis://localhost:6379/0` for local, Upstash URL for production
- `DATABASE_URL` -- `sqlite:///db/gatekeepify.db` for local, Neon URL for production

## External Services To Set Up

### NOT YET SET UP -- needed before deployment:

1. **Redis (local)** -- `brew install redis && brew services start redis` OR `docker run -d --name redis -p 6379:6379 redis:alpine`. Blocked on work computer by Santa security policy; do this on personal machine.

2. **Neon** (free PostgreSQL) -- sign up at neon.tech, create a database, get `DATABASE_URL`

3. **Upstash** (free Redis) -- sign up at upstash.com, create a Redis instance, get `REDIS_URL`

4. **Fly.io** (free compute) -- install `flyctl`, run `fly launch`, set secrets:
   ```
   fly secrets set DATABASE_URL="postgres://..." REDIS_URL="redis://..." \
     SPOTIFY_CLIENT_ID="..." SPOTIFY_CLIENT_SECRET="..." \
     JWT_SECRET="$(openssl rand -hex 32)" \
     SPOTIFY_REDIRECT_URI="https://gatekeepify.fly.dev/auth/callback"
   ```

5. **Spotify Developer Dashboard** -- update the app's redirect URI to match production URL (`https://gatekeepify.fly.dev/auth/callback`)

6. **Run the SQLite migration** -- after PostgreSQL is set up:
   ```bash
   DATABASE_URL="postgres://..." python -m scripts.migrate_sqlite
   ```

## Implementation Phases

### Phase 1: Database + API Foundation ✅ COMPLETE
SQLAlchemy models, Alembic migrations, FastAPI with Spotify OAuth, stats endpoints (SQL aggregation replacing in-memory Counter), ZIP upload with fraud validation.

### Phase 2: Background Jobs + Multi-User ✅ COMPLETE
Celery + Redis tasks, ingestion service, per-user token management, Dockerfile + supervisord + fly.toml for deployment.

### Phase 3: Social + Gatekeeping Core ❌ NOT STARTED
This is the actual product differentiator. Key work:
- `friendships` table (bidirectional) + `friend_invites` table (with invite codes)
- Friend invite/accept API endpoints
- **`GET /gatekeep/artist/{artist_id}`** -- the core feature: compare first-listen dates among friends, crown the earliest listener, show verified vs self-reported badges
- **`GET /gatekeep/track/{track_id}`** -- same for tracks
- **`GET /gatekeep/leaderboard`** -- who has the most "first listener" crowns
- **`POST /gatekeep/challenge`** -- generate shareable "prove me wrong" cards with embedded invite links

The core gatekeeping query includes a trust hierarchy: `first_listen_source` tells the UI whether to show a verified badge (API-sourced) or "self-reported" (export-sourced).

### Phase 4: Frontend ❌ NOT STARTED
Next.js web app. Key pages: landing (`/`), dashboard, upload, friends, `/gatekeep/[artistId]` (the product page), leaderboard. The gatekeep page needs trust indicators (verified checkmark vs self-reported marker).

## Critical Design Decisions

### Data integrity is a first-class concern
Users have incentive to fabricate listening history. Five validation layers:
1. **Release date check** -- reject listens before a track's release date (stored on `dim_all_albums.release_date`)
2. **Source tagging** -- every listen marked `api` (unforgeable) or `export` (user-submitted) via `dim_all_listens.source`
3. **API cross-referencing** -- detect contradictions between uploaded data and API-polled data
4. **Export format validation** -- real Spotify exports have metadata fields (`reason_start`, `platform`, `shuffle`, etc.) that are hard to fake; stored in `export_metadata`
5. **Statistical anomaly detection** -- future work, flag suspicious patterns

### Preemptive friend onboarding is not feasible
Spotify's API does not expose any user's listening data without their OAuth consent. No workaround exists. Instead, build social pressure: challenge cards ("I listened to X before you -- prove me wrong") with invite links.

### Analytics are SQL, not Python
The legacy `stat_viewer.py` loaded all listens into memory and used `Counter`. The new stats endpoints use SQL `GROUP BY` queries that scale to millions of rows.

## Spotify API Constraints
- `GET /v1/me/player/recently-played` -- max 50 tracks, no way around this
- `GET /v1/me/top/{type}` -- top items with time_range, no timestamps (ranking only)
- `GET /v1/users/{user_id}` -- public profile only, no listening data
- No friends list endpoint, no webhooks, polling only
- Rate limits: ~100 requests per 30-second window per app
- Album `release_date` can be `"2020-06-15"`, `"2020-06"`, or `"2020"` -- `parse_release_date()` handles all three

## Edge Cases and Known Issues
- Spotify's `played_at` format (`%Y-%m-%dT%H:%M:%S.%fZ`) differs from the data export format (`%Y-%m-%dT%H:%M:%SZ`) -- both are handled
- Tracks can exist in `dim_all_listens` with no corresponding `dim_all_tracks` row (from backfill imports). The `backfill_track_metadata` task finds these via LEFT JOIN + IS NULL
- When two tracks share the same artist, SQLAlchemy needs a `db.flush()` between merges to avoid duplicate INSERT errors (fixed in `_upsert_track_and_relations`)
- The `redis` package is in requirements.txt from the legacy app but was never used; `celery[redis]` now provides the actual Redis dependency
- `src/host_constants.py` contains real Spotify API credentials in plaintext -- these should be rotated after migrating to env vars in production
- The `.cache` files (spotipy OAuth token cache) in both root and `src/` contain live tokens and should not be committed
