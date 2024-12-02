import spotipy
from constants import CLIENT_DATETIME_FORMAT, CLIENT_ID, CLIENT_SECRET, DEFAULT_SCOPE, MAXIMUM_RECENT_TRACKS, REDIRECT_URI
from datetime import datetime, timezone
from db.Database import Database
from spotify.types import Track, User
from spotipy.oauth2 import SpotifyOAuth
from typing import Dict, Optional

class SpotifyClient:
    client: spotipy.Spotify
    db: Database

    def __init__(self) -> None:
        self.client = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                scope=DEFAULT_SCOPE,
            )
        )
        self.db = Database()

    def gen_current_user(self) -> User:
        res = self.client.current_user()
        if not res:
            raise Exception("No user found")
        return User.from_dict(res)

    def gen_most_recent_listens(self, after: Optional[datetime] = None) -> Dict[datetime, Track]:
        after_ts = int(after.replace(tzinfo=timezone.utc).timestamp() * 1000) if after else None
        res = self.client.current_user_recently_played(limit=MAXIMUM_RECENT_TRACKS, after=after_ts)
        if not res:
            raise Exception("No recents found")

        recent_tracks = res["items"]
        return {
            datetime.strptime(
                track["played_at"],
                CLIENT_DATETIME_FORMAT
            ): Track.from_dict(track["track"]) for track in recent_tracks
        }

    def gen_run_cron_backfill(self, user: User) -> None:
        after_ts = self.db.gen_most_recent_listen_time(user)
        recent_listens = self.gen_most_recent_listens(after_ts)
        self.db.upsert_cron_backfill(user, recent_listens)
