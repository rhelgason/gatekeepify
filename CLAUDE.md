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
- `app/main.py` -- FastAPI entry point, middleware, exception handlers
- `app/models.py` -- All ORM models (8 data tables + 2 social + audit_log + job_runs)
- `app/schemas.py` -- Pydantic request/response models
- `app/config.py` -- Settings from environment variables
- `app/database.py` -- SQLAlchemy engine/session
- `app/routers/auth.py` -- Spotify OAuth + JWT + `get_current_user` dependency
- `app/routers/stats.py` -- Top tracks/artists/genres/wrapped (SQL aggregation, paginated)
- `app/routers/backfill.py` -- ZIP upload with 5-layer fraud validation
- `app/routers/friends.py` -- Friend invites (atomic claim), acceptance, listing
- `app/routers/gatekeep.py` -- Artist/track comparison, leaderboard, challenge cards
- `app/routers/search.py` -- Search artists/tracks by name (case-insensitive, ranked by listen count)
- `app/services/spotify.py` -- Multi-user Spotify API client + token encryption
- `app/services/ingestion.py` -- Data upsert logic + retroactive release-date validation
- `app/services/audit.py` -- `log_action()` writes to `audit_log` table + stdout
- `app/celery_app.py` -- Celery config + beat schedule
- `app/tasks.py` -- Periodic tasks with token revocation handling

### Database Schema
8 data tables + 2 social tables + 2 operational tables:
- `dim_all_albums` (album_id PK, album_name, **release_date**)
- `dim_all_tracks` (track_id PK, track_name, album_id FK, duration_ms, is_local)
- `dim_all_artists` (artist_id PK, artist_name)
- `track_to_artist` (composite PK, M:N junction)
- `artist_to_genre` (composite PK, M:N junction)
- `dim_all_users` (user_id PK, user_name, email, **spotify_refresh_token**, created_at, last_poll_at)
- `dim_all_listens` (composite PK: ts+user_id+track_id, **source**, **export_metadata**)
- `friendships` (composite PK: user_id_1+user_id_2, created_at) -- both directions stored
- `friend_invites` (id PK, from_user_id, invite_code UNIQUE, created_at, accepted_by_user_id, accepted_at)
- `audit_log` (id PK, ts, user_id FK, **action** indexed, entity_type, entity_id, details JSON, status) -- indexes on (user_id, ts) and (action, ts)
- `job_runs` (id PK, job_name, user_id, started_at, completed_at, status, record_count)

### Test Suite
144 tests, no external services needed:
```bash
source env/bin/activate
python -m pytest tests/test_app/ -v
```

## Development Setup

### Run the FastAPI server locally
```bash
source env/bin/activate
uvicorn app.main:app --reload
# Swagger UI at http://localhost:8000/docs
# Health check at http://localhost:8000/health (verifies DB connectivity)
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

## Deployment (Railway -- all browser, no local tooling)

### CI/CD
- `.github/workflows/ci.yml` runs all 144 tests + verifies server startup on every push/PR to `main`
- Railway auto-deploys from `main` branch after connecting the GitHub repo

### Deployment config files
- `railway.toml` -- tells Railway to use Dockerfile, sets health check on `/health`
- `Dockerfile` -- Python 3.10, installs deps + supervisor, runs all 3 processes
- `supervisord.conf` -- manages uvicorn (web), celery worker, celery beat in one container
- `.dockerignore` -- excludes env/, tests/, db/, .git/, credentials from the image

### Setup checklist (ordered)

1. **Push repo to GitHub** (from work machine, just `git push`)

2. **Sign up for Railway** (railway.app) -- connect your GitHub account

3. **Create a PostgreSQL database in Railway** -- click "New" > "Database" > "PostgreSQL". Copy the `DATABASE_URL` from the connection panel.

4. **Create a Redis database in Railway** -- click "New" > "Database" > "Redis". Copy the `REDIS_URL`.

5. **Create the app service in Railway** -- click "New" > "GitHub Repo" > select `gatekeepify`. Railway detects the Dockerfile automatically.

6. **Set environment variables** in Railway's service settings (Variables tab):
   ```
   DATABASE_URL=<from step 3>
   REDIS_URL=<from step 4>
   SPOTIFY_CLIENT_ID=e1ee69e65fb241a29c6a46e856a5e64e
   SPOTIFY_CLIENT_SECRET=<your secret>
   SPOTIFY_REDIRECT_URI=https://<your-railway-domain>/auth/callback
   JWT_SECRET=<generate: python -c "import secrets; print(secrets.token_hex(32))">
   ENCRYPTION_KEY=<generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
   ```

7. **Get your Railway domain** -- in service settings > "Networking" > "Generate Domain". It'll be something like `gatekeepify-production.up.railway.app`.

8. **Update SPOTIFY_REDIRECT_URI** -- go back to Variables and set it to `https://<your-railway-domain>/auth/callback`.

9. **Update Spotify Developer Dashboard** -- go to developer.spotify.com/dashboard, select your app, click "Edit Settings", add `https://<your-railway-domain>/auth/callback` to the Redirect URIs list.

10. **Deploy** -- Railway auto-deploys when you push to `main`. Or click "Deploy" in the dashboard.

11. **Verify** -- visit `https://<your-railway-domain>/health`. Should return `{"status": "ok", "checks": {"database": "ok"}}`.

12. **Test OAuth** -- visit `https://<your-railway-domain>/auth/login`, click the Spotify auth URL, authorize, confirm you get a JWT back.

13. **Migrate legacy data** (optional) -- if you want your existing SQLite listening history in production, run the migration script locally with the production DATABASE_URL:
    ```bash
    DATABASE_URL="<railway postgres url>" python -m scripts.migrate_sqlite
    ```

14. **Rotate Spotify credentials** -- after confirming production works, go to the Spotify Developer Dashboard and regenerate the client secret. Update the Railway env var. Delete `src/host_constants.py`, `src/.cache`, and `.cache` from the repo.

### Post-deployment: next code work

- **Frontend (Phase 4)** -- Next.js web app. The backend API is fully ready. Key pages: landing, dashboard, upload, friends, `/gatekeep/[artistId]` (the product page), leaderboard.

## Implementation Phases

### Phase 1: Database + API Foundation ✅ COMPLETE
SQLAlchemy models, Alembic migrations, FastAPI with Spotify OAuth, stats endpoints (SQL aggregation replacing in-memory Counter), ZIP upload with fraud validation.

### Phase 2: Background Jobs + Multi-User ✅ COMPLETE
Celery + Redis tasks, ingestion service, per-user token management, Dockerfile + supervisord + fly.toml for deployment.

### Phase 3: Social + Gatekeeping Core ✅ COMPLETE
Friendships (bidirectional), friend invites (atomic claim), gatekeep artist/track comparison, leaderboard (CTE-based crown counting), challenge card generation.

### Backend Hardening ✅ COMPLETE
1. ✅ Auth tokens moved from query params to `Authorization: Bearer` headers
2. ✅ Spotify token revocation handling (deactivates user, falls through to next)
3. ✅ Deferred release-date validation (retroactively removes invalid export listens after metadata backfill)
4. ✅ Concurrent invite acceptance race condition (atomic UPDATE)
5. ✅ Pagination on all list endpoints (limit clamped to 100, offset support)
6. ✅ Search endpoints for artists and tracks by name
7. ✅ Structured error responses (consistent `{"error": type, "detail": message}` shape for all error codes)
8. ✅ OAuth callback test coverage (6 tests with mocked Spotify)
9. ✅ Health check verifies database connectivity (returns 503 if DB is down)
10. ✅ Structured audit logging across all routers (`audit_log` table + stdout middleware)

### Phase 4: Frontend ❌ NOT STARTED

## Critical Design Decisions

### Data integrity is a first-class concern
Users have incentive to fabricate listening history. Five validation layers:
1. **Release date check** -- reject listens before a track's release date (stored on `dim_all_albums.release_date`). Also runs retroactively after metadata backfill fills in release dates.
2. **Source tagging** -- every listen marked `api` (unforgeable) or `export` (user-submitted) via `dim_all_listens.source`
3. **API cross-referencing** -- detect contradictions between uploaded data and API-polled data
4. **Export format validation** -- real Spotify exports have metadata fields (`reason_start`, `platform`, `shuffle`, etc.) that are hard to fake; stored in `export_metadata`
5. **Statistical anomaly detection** -- future work, flag suspicious patterns

### Auth uses Bearer tokens, not query params
All authenticated endpoints use `Authorization: Bearer <JWT>` headers via FastAPI's `HTTPBearer` dependency. The `get_current_user` dependency in `auth.py` is reused by every router.

### Preemptive friend onboarding is not feasible
Spotify's API does not expose any user's listening data without their OAuth consent. No workaround exists. Instead, build social pressure: challenge cards ("I listened to X before you -- prove me wrong") with invite links.

### Analytics are SQL, not Python
The legacy `stat_viewer.py` loaded all listens into memory and used `Counter`. The new stats endpoints use SQL `GROUP BY` queries that scale to millions of rows.

### All errors return consistent JSON
Every error response has the shape `{"error": "<type>", "detail": "<message>"}`. Types: `validation_error` (422), `http_error` (4xx), `database_error` (503), `spotify_auth_error` / `spotify_api_error` (502), `internal_error` (500). Unhandled exceptions are logged to `audit_log` with full context.

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
- The gatekeep queries use `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` instead of `COUNT(*) FILTER (WHERE ...)` because SQLite doesn't support FILTER
- Friendships are stored bidirectionally (two rows). If you add a friendship A↔B, insert both (A,B) and (B,A) rows. This makes querying simple but requires keeping both in sync
- The leaderboard only counts "contested" artists (those with 2+ listeners in the friend group). An artist only you've listened to doesn't earn a crown
- Invite acceptance uses an atomic `UPDATE ... WHERE accepted_by_user_id IS NULL` to prevent race conditions
- If a user's Spotify refresh token is revoked, the Celery worker clears their token and skips them in future polls. The user must re-authenticate via `/auth/login`.
- The `redis` package is in requirements.txt from the legacy app but was never used; `celery[redis]` now provides the actual Redis dependency
- `src/host_constants.py` contains real Spotify API credentials in plaintext -- rotate after migrating to env vars
- The `.cache` files (spotipy OAuth token cache) in both root and `src/` contain live tokens and should not be committed

## Audit Log Actions Reference
All logged to `audit_log` table. Query with `SELECT * FROM audit_log WHERE user_id = ? ORDER BY ts DESC`.

| Action | When | Details |
|--------|------|---------|
| `auth.callback` | OAuth completes | `is_new_user`, `display_name` |
| `backfill.upload` | Data export processed | `total_processed`, `total_accepted`, `total_rejected`, `rejection_reasons` |
| `friends.invite_created` | Invite generated | entity_type=`invite`, entity_id=code |
| `friends.invite_accepted` | Invite accepted or rejected | `friend_id` on success; `reason` on denial |
| `gatekeep.artist_viewed` | Artist comparison | `artist_name`, `num_participants`, `winner` |
| `gatekeep.track_viewed` | Track comparison | `track_name`, `num_participants`, `winner` |
| `gatekeep.leaderboard_viewed` | Leaderboard accessed | `total_artists_contested`, `num_entries` |
| `gatekeep.challenge_created` | Challenge generated | `artist_name`, `total_listens`, `invite_code` |
| `stats.top_tracks_viewed` | Stats page | `period`, `limit`, `offset`, `results` |
| `stats.top_artists_viewed` | Stats page | `period`, `limit`, `offset`, `results` |
| `stats.top_genres_viewed` | Stats page | `period`, `limit`, `offset`, `results` |
| `stats.wrapped_viewed` | Wrapped summary | `year`, `total_minutes` |
| `search.artists` | Artist search | `query`, `results` |
| `search.tracks` | Track search | `query`, `results` |
| `system.database_error` | DB connectivity failure | `path`, `error` |
| `system.unhandled_error` | Unexpected exception | `path`, `method`, `error_type`, `error` |
