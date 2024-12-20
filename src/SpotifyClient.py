import spotipy
from constants import CLIENT_DATETIME_FORMAT, DEFAULT_SCOPE, HOST_CONSTANTS_PATH, MAXIMUM_RECENT_TRACKS, REDIRECT_URI
from datetime import datetime, timezone
from db.Database import Database
from getpass import getpass
from spotify.types import Track, User
from spotipy.oauth2 import SpotifyOAuth
from typing import Dict, Optional, Tuple

class SpotifyClient:
    client: spotipy.Spotify
    db: Database

    def __init__(self) -> None:
        client_id, client_secret = self.get_host_constants()      
        self.client = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=REDIRECT_URI,
                scope=DEFAULT_SCOPE,
            )
        )
        self.db = Database()
    
    # get client id and secret if exists, otherwise get user input
    def get_host_constants(self) -> Tuple[str, str]:
        try:
            host_constants_spec = __import__("/".join(HOST_CONSTANTS_PATH.split("/")[1:]), globals(), locals(), ['CLIENT_ID', 'CLIENT_SECRET'], 0)
            return (host_constants_spec.CLIENT_ID, host_constants_spec.CLIENT_SECRET)
        except:
            # constants file not found, get user input
            client_id = input('Please input your Spotify API client ID: ')
            client_secret = getpass('Please input your Spotify API client secret: ')
            f = open(".".join((HOST_CONSTANTS_PATH, "py")), "w")
            f.write('CLIENT_ID = "' + client_id + '"\n')
            f.write('CLIENT_SECRET = "' + client_secret + '"')
            f.close()
            return (client_id, client_secret)

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
