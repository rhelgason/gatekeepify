import spotipy
from datetime import datetime, timezone
from spotify.types import Track, User
from spotipy.oauth2 import SpotifyOAuth
from typing import Dict, Optional

CLIENT_ID = "e1ee69e65fb241a29c6a46e856a5e64e"
CLIENT_SECRET = "affb3816f14346ae8298f9284e772b02"
REDIRECT_URI = "https://github.com/rhelgason"
DEFAULT_SCOPE = "user-read-private user-read-email user-read-recently-played"
MAXIMUM_RECENT_TRACKS = 50

class SpotifyClient:
    client: spotipy.Spotify

    def __init__(self) -> None:
        self.client = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                scope=DEFAULT_SCOPE,
            )
        )

    def gen_current_user(self) -> User:
        res = self.client.current_user()
        if not res:
            raise Exception("No user found")
        return User.from_dict(res)

    def gen_most_recent_tracks(self, after: Optional[datetime] = None) -> Dict[datetime, Track]:
        after_ts = int(after.replace(tzinfo=timezone.utc).timestamp() * 1000) if after else None
        res = self.client.current_user_recently_played(limit=MAXIMUM_RECENT_TRACKS, after=after_ts)
        if not res:
            raise Exception("No recents found")

        recent_tracks = res["items"]
        if len(recent_tracks) >= MAXIMUM_RECENT_TRACKS:
            ## TODO: handle likely missing data
            pass

        return {
            datetime.strptime(
                track["played_at"],
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ): Track.from_dict(track["track"]) for track in recent_tracks
        }
