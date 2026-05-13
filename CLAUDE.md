# Gatekeepify

## What This Is

A music gatekeeping app. Users track their Spotify listening history and competitively prove they listened to an artist before their friends did. The core value proposition is *comparative timestamp data* -- "I listened to Radiohead 847 times since 2017. You started in 2021. Sit down."

The product is intentionally performative and annoying. That's the point.

## Architecture Overview

- **`app/`** -- FastAPI backend (SQLAlchemy ORM, Celery tasks, JWT auth)
- **`frontend/`** -- Next.js 14 frontend (TypeScript, Tailwind CSS)
- **Deployed:** Railway (backend + PostgreSQL + Redis), Vercel (frontend)

### Key Files
- `app/main.py` -- FastAPI entry point, middleware, exception handlers, admin endpoints
- `app/models.py` -- ORM models: 8 data tables + 2 social + audit_log + award_snapshots + job_runs
- `app/schemas.py` -- Pydantic request/response models
- `app/config.py` -- Settings from environment variables
- `app/routers/auth.py` -- Spotify OAuth + JWT + `get_current_user` dependency
- `app/routers/stats.py` -- Top tracks/artists/genres/wrapped/timeline (SQL aggregation, paginated, target_user_id support)
- `app/routers/backfill.py` -- ZIP upload with fraud validation + immediate enrichment
- `app/routers/friends.py` -- Invite links, direct friend requests, user search, accept/decline
- `app/routers/gatekeep.py` -- Artist/track comparison, leaderboard, challenge cards
- `app/routers/search.py` -- Search artists/tracks, detail endpoints, resolve-artist (Spotify fallthrough), Spotify search
- `app/routers/awards.py` -- Trophy case, head-to-head comparison
- `app/routers/discover.py` -- Friends' fresh finds, you're late on, rising artists
- `app/services/spotify.py` -- Multi-user Spotify API client + token encryption
- `app/services/ingestion.py` -- Data upsert logic + retroactive release-date validation
- `app/services/awards.py` -- 12 award computation functions
- `app/services/anomaly.py` -- Statistical anomaly detection (trust scores)
- `app/services/lastfm.py` -- Last.fm API integration
- `app/services/audit.py` -- `log_action()` writes to audit_log table + stdout
- `app/celery_app.py` -- Celery config + beat schedule (3 periodic tasks)
- `app/tasks.py` -- Batched polling, metadata backfill, award snapshots
- `frontend/src/lib/api.ts` -- API client with 30s cache, Bearer token injection
- `frontend/src/lib/track.ts` -- Frontend event tracking (fire-and-forget to /track-event)
- `frontend/src/components/Navbar.tsx` -- Responsive nav with hamburger + friend request badge
- `frontend/src/components/BackfillBanner.tsx` -- Persistent nudge until user uploads data export

### Database Schema
8 data tables + 2 social + 3 operational:
- `dim_all_albums` (album_id PK, album_name, release_date, image_url)
- `dim_all_tracks` (track_id PK, track_name, album_id FK, duration_ms, is_local, image_url)
- `dim_all_artists` (artist_id PK, artist_name, image_url)
- `track_to_artist` (composite PK, M:N junction)
- `artist_to_genre` (composite PK, M:N junction)
- `dim_all_users` (user_id PK, user_name, email, spotify_refresh_token, created_at, last_poll_at)
- `dim_all_listens` (composite PK: ts+user_id+track_id, source, export_metadata)
- `friendships` (composite PK: user_id_1+user_id_2, created_at) -- both directions stored
- `friend_invites` (id PK, from_user_id, to_user_id, invite_code UNIQUE, accepted_by_user_id, accepted_at)
- `award_snapshots` (id PK, user_id, friend_group_hash, award_id, rank, stat_value, stat_detail, computed_at)
- `audit_log` (id PK, ts, user_id, action, entity_type, entity_id, details JSON, status)
- `job_runs` (id PK, job_name, user_id, started_at, completed_at, status, record_count)

### Test Suite
199 tests, no external services needed:
```bash
source env/bin/activate
python -m pytest tests/test_app/ -v
```

## Development Setup

```bash
# Server
source env/bin/activate
uvicorn app.main:app --reload
# Swagger UI at http://localhost:8000/docs

# Celery (requires Redis)
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info

# Frontend (requires Node.js)
cd frontend && npm install && npm run dev
```

### Environment variables
Copy `.env.example` to `.env`:
- `DATABASE_URL` -- `sqlite:///db/gatekeepify.db` for local, PostgreSQL URL for production
- `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` -- from Spotify Developer Dashboard
- `SPOTIFY_REDIRECT_URI` -- `http://localhost:8000/auth/callback` locally
- `JWT_SECRET` -- random string
- `REDIS_URL` -- `redis://localhost:6379/0`
- `FRONTEND_URL` -- `https://gatekeepify.vercel.app` (production Vercel domain)
- `ENCRYPTION_KEY` -- Fernet key for encrypting stored Spotify refresh tokens
- `LASTFM_API_KEY` -- free key from last.fm/api

## Deployment

**Railway** (backend): auto-deploys from `main`. Dockerfile + supervisord runs web + worker + beat.
**Vercel** (frontend): auto-deploys from `main`. Root directory set to `frontend`.
**CI**: GitHub Actions runs 199 tests on every push to `main`.

### Celery Beat Schedule
- `poll_recent_listens` -- every 15 min, batches up to 500 users per cycle
- `backfill_track_metadata` -- every 2 min, fills in missing track/album/artist data
- `compute_award_snapshots` -- every 6 hours, computes cached awards for all friend groups

### Admin Endpoints
- `POST /admin/trigger-poll` -- manually trigger listen polling
- `POST /admin/trigger-backfill` -- manually trigger metadata backfill
- `POST /admin/trigger-awards` -- manually trigger award computation
- `GET /admin/trust-score?target_user_id=X` -- check anomaly detection results

## Gamification System

12 awards across 4 tiers:
- **Discovery:** Crown, Archaeologist, Trendsetter, Patient Zero
- **Devotion:** Obsessive, Completionist, Night Owl
- **Taste:** Genre Snob, Time Traveler, The Basic (anti-award)
- **Dynamic:** Streak, Hypebeast

Simple awards (Crown, Obsessive, Night Owl, Basic, Trendsetter) computed on-the-fly.
Complex awards cached in `award_snapshots` via Celery task every 6 hours.

## Data Integrity

6 validation layers:
1. **Release date check** -- reject listens before track release date
2. **Source tagging** -- every listen marked `api` (verified) or `export` (self-reported)
3. **API cross-referencing** -- detect contradictions between export and API data
4. **Export format validation** -- check for Spotify export metadata fields
5. **Retroactive validation** -- remove invalid export listens after metadata backfill discovers release dates
6. **Statistical anomaly detection** -- trust score (0-100) based on rapid-fire, even spacing, single-day dumps, backdated clusters, pre-release, low API ratio

## Frontend Pages

- `/` -- Landing page with Spotify sign-in
- `/dashboard` -- Top tracks/artists/genres with period selector
- `/wrapped` -- Predicted Wrapped with year selector
- `/discover` -- Friends' fresh finds, you're late on, rising artists
- `/gatekeep` -- Search artists (DB + Spotify fallthrough)
- `/artist/[id]` -- Artist detail: hero, SVG line chart timeline (personal/friends/global), Last.fm stats, gatekeep comparison, challenge
- `/trophies` -- Trophy case with 12 awards, mini-leaderboards, head-to-head CTA
- `/trophies/head-to-head?friend=X` -- Side-by-side comparison with visual bars
- `/friends` -- User search, direct requests, invite link generation, pending requests
- `/profile/[userId]` -- View a friend's stats
- `/upload` -- Drag-and-drop ZIP upload with progress
- `/invite/[code]` -- Auto-accept invite (stores code through OAuth redirect via localStorage)
- `/auth/callback` -- OAuth callback, checks for pending invite

## Spotify API Constraints
- `GET /v1/me/player/recently-played` -- max 50 tracks
- No friends list, no webhooks, polling only
- Rate limits: ~100 req/30s per app
- Album `release_date` can be `"2020-06-15"`, `"2020-06"`, or `"2020"`

## Scaling Design
- Batched polling: 500 users/cycle, ordered by `last_poll_at`, 1s inter-user delay
- Redis lock prevents overlapping poll cycles
- At 10k users: each user polled every ~5 hours (Spotify returns last 50 tracks regardless)
- ZIP upload enrichment capped at 500 tracks immediate, rest via 2-min backfill cron
- Award snapshots cached every 6 hours to avoid expensive CTE queries on page load

## Edge Cases
- Spotify `played_at` format differs from data export format -- both handled
- Tracks can exist in listens with no track record (from backfill) -- metadata cron fills these
- SQLAlchemy `db.flush()` between entity and relation merges to prevent FK violations on PostgreSQL
- `SUM(CASE WHEN...)` instead of `COUNT(*) FILTER(WHERE...)` for SQLite compatibility
- Friendships stored bidirectionally (two rows per friendship)
- Leaderboard only counts "contested" artists (2+ listeners in friend group)
- Invite acceptance uses atomic `UPDATE ... WHERE accepted_by_user_id IS NULL`
- Revoked Spotify tokens cleared automatically, user must re-auth
- Timeline uses Python-side month grouping (not `strftime`) for PostgreSQL compatibility
- CORS allows all origins (safe with Bearer token auth, needed for Vercel preview deployments)
- OAuth `state` parameter carries frontend origin for preview deployment support

## Logging
- Every backend endpoint writes to `audit_log` table
- Frontend `PageTracker` component logs every page view
- `trackEvent()` utility logs button clicks, searches, uploads, period changes, etc.
- All frontend events prefixed with `frontend.` in the audit log
- HTTP request middleware logs method, path, status, duration to stdout
- Query all activity: `SELECT * FROM audit_log WHERE user_id = ? ORDER BY ts DESC`
