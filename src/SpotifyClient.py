import spotipy
from spotify.Track import Track
from spotipy.oauth2 import SpotifyOAuth
from typing import List, Optional

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

    def gen_most_recent_tracks(self, after: Optional[int] = None) -> List[Track]:
        res = self.client.current_user_recently_played(limit=MAXIMUM_RECENT_TRACKS, after=after)
        if not res:
            raise Exception("No recents found")

        recent_tracks = res["items"]
        if len(recent_tracks) >= MAXIMUM_RECENT_TRACKS:
            ## TODO: handle likely missing data
            pass

        return [Track.from_dict(track["track"]) for track in recent_tracks]
