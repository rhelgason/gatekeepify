import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional

CLIENT_ID = "e1ee69e65fb241a29c6a46e856a5e64e"
CLIENT_SECRET = "affb3816f14346ae8298f9284e772b02"
REDIRECT_URI = "https://github.com/rhelgason"
DEFAULT_SCOPE = "user-read-recently-played"
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

    def gen_upsert_most_recent_tracks(self, after: Optional[int] = None):
        res = self.client.current_user_recently_played(limit=MAXIMUM_RECENT_TRACKS, after=after)
        if not res:
            raise Exception("No recents found")

        recents = res["items"]
        if len(recents) >= MAXIMUM_RECENT_TRACKS:
            ## TODO: handle likely missing data
            pass

        for recent in recents:
            print(recent["track"]["name"])
