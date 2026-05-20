import logging
import time
from typing import Optional

import requests

from app.config import settings

logger = logging.getLogger("gatekeepify.lastfm")

BASE_URL = "https://ws.audioscrobbler.com/2.0/"

# In-memory cache for Last.fm responses (TTL: 1 hour)
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 3600  # seconds


def _lastfm_get(method: str, params: dict) -> Optional[dict]:
    params.update(
        {
            "method": method,
            "api_key": settings.lastfm_api_key,
            "format": "json",
        }
    )
    resp = requests.get(BASE_URL, params=params, timeout=10)
    if resp.status_code != 200:
        logger.warning(f"Last.fm {method} returned {resp.status_code}: {resp.text[:200]}")
        return None
    data = resp.json()
    if "error" in data:
        logger.warning(f"Last.fm {method} error: {data.get('message')}")
        return None
    return data


def get_artist_global_stats(artist_name: str) -> Optional[dict]:
    if not settings.lastfm_api_key:
        logger.warning("LASTFM_API_KEY is not set")
        return None

    # Check cache
    cache_key = artist_name.lower().strip()
    if cache_key in _cache:
        cached_time, cached_data = _cache[cache_key]
        if time.time() - cached_time < _CACHE_TTL:
            return cached_data

    logger.info(f"Fetching Last.fm data for '{artist_name}'")

    try:
        info = _lastfm_get("artist.getInfo", {"artist": artist_name})
        if not info:
            return None

        artist = info.get("artist", {})
        stats = artist.get("stats", {})
        total_listeners = int(stats.get("listeners", 0))
        total_playcount = int(stats.get("playcount", 0))

        tags = [t.get("name") for t in artist.get("tags", {}).get("tag", []) if t.get("name")]

        similar_artists = []
        similar = artist.get("similar", {}).get("artist", [])
        for s in similar[:5]:
            similar_artists.append(s.get("name", ""))

        result: dict = {
            "total_listeners": total_listeners,
            "total_playcount": total_playcount,
            "tags": tags,
            "similar_artists": similar_artists,
        }

        top_tracks = _lastfm_get("artist.getTopTracks", {"artist": artist_name, "limit": "10"})
        if top_tracks:
            tracks = top_tracks.get("toptracks", {}).get("track", [])
            result["top_tracks"] = [
                {
                    "name": t.get("name", ""),
                    "playcount": int(t.get("playcount", 0)),
                }
                for t in tracks[:10]
            ]

        top_albums = _lastfm_get("artist.getTopAlbums", {"artist": artist_name, "limit": "5"})
        if top_albums:
            albums = top_albums.get("topalbums", {}).get("album", [])
            result["top_albums"] = [
                {
                    "name": a.get("name", ""),
                    "playcount": int(a.get("playcount", 0)),
                }
                for a in albums[:5]
            ]

        logger.info(f"Last.fm data for '{artist_name}': {total_listeners} listeners, {total_playcount} plays")
        _cache[cache_key] = (time.time(), result)
        return result

    except Exception as e:
        logger.error(f"Last.fm API error for '{artist_name}': {type(e).__name__}: {e}")
        return None
