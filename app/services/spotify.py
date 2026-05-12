from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from app.config import settings

MAXIMUM_RECENT_TRACKS = 50
MAX_TRACKS_REQUEST = 50


class SpotifyService:
    def __init__(self) -> None:
        self._oauth = SpotifyOAuth(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            redirect_uri=settings.spotify_redirect_uri,
            scope=settings.spotify_scopes,
        )

    def get_auth_url(self) -> str:
        return self._oauth.get_authorize_url()

    def exchange_code(self, code: str) -> dict:
        return self._oauth.get_access_token(code, as_dict=True)

    def refresh_access_token(self, refresh_token: str) -> dict:
        return self._oauth.refresh_access_token(refresh_token)

    def get_client(self, access_token: str) -> spotipy.Spotify:
        return spotipy.Spotify(auth=access_token, backoff_factor=0.3)

    def get_current_user(self, access_token: str) -> dict:
        client = self.get_client(access_token)
        result = client.current_user()
        if not result:
            raise ValueError("Failed to fetch current user from Spotify")
        return result

    def get_recent_listens(
        self, access_token: str, after: Optional[datetime] = None
    ) -> List[dict]:
        client = self.get_client(access_token)
        after_ts = None
        if after:
            after_ts = int(after.replace(tzinfo=timezone.utc).timestamp() * 1000)
        result = client.current_user_recently_played(
            limit=MAXIMUM_RECENT_TRACKS, after=after_ts
        )
        if not result or not result.get("items"):
            return []
        items = result["items"]
        self._enrich_with_genres(client, items)
        return items

    def get_tracks(self, access_token: str, track_ids: List[str]) -> List[dict]:
        if not track_ids:
            return []
        client = self.get_client(access_token)
        batches = [
            track_ids[i : i + MAX_TRACKS_REQUEST]
            for i in range(0, len(track_ids), MAX_TRACKS_REQUEST)
        ]
        all_tracks = []
        for batch in batches:
            result = client.tracks(batch)
            if result and result.get("tracks"):
                items = [{"track": t} for t in result["tracks"] if t]
                self._enrich_with_genres(client, items)
                all_tracks.extend(items)
        return all_tracks

    def get_top_items(
        self, access_token: str, item_type: str, time_range: str = "long_term"
    ) -> List[dict]:
        client = self.get_client(access_token)
        result = client._get(
            f"me/top/{item_type}", limit=50, time_range=time_range
        )
        if not result or not result.get("items"):
            return []
        return result["items"]

    def _enrich_with_genres(
        self, client: spotipy.Spotify, track_items: List[dict]
    ) -> None:
        all_artist_ids: Set[str] = set()
        for item in track_items:
            track = item.get("track", {})
            for artist in track.get("artists", []):
                if artist.get("id"):
                    all_artist_ids.add(artist["id"])
        if not all_artist_ids:
            return
        genre_map: Dict[str, list] = {}
        artist_id_list = list(all_artist_ids)
        for i in range(0, len(artist_id_list), MAX_TRACKS_REQUEST):
            batch = artist_id_list[i : i + MAX_TRACKS_REQUEST]
            artists_result = client.artists(batch)
            if artists_result and artists_result.get("artists"):
                for a in artists_result["artists"]:
                    if a:
                        genre_map[a["id"]] = a.get("genres", [])
        for item in track_items:
            track = item.get("track", {})
            for artist in track.get("artists", []):
                artist["genres"] = genre_map.get(artist.get("id"), [])


def encrypt_token(token: str) -> str:
    if not settings.encryption_key:
        return token
    from cryptography.fernet import Fernet

    f = Fernet(settings.encryption_key.encode())
    return f.encrypt(token.encode()).decode()


def decrypt_token(token: str) -> str:
    if not settings.encryption_key:
        return token
    from cryptography.fernet import Fernet

    f = Fernet(settings.encryption_key.encode())
    return f.decrypt(token.encode()).decode()
