import getpass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import spotipy
from constants import (
    DEFAULT_SCOPE,
    HOST_CONSTANTS_PATH,
    HOST_CONSTANTS_TEST_PATH,
    MAXIMUM_RECENT_TRACKS,
    REDIRECT_URI,
)
from db.constants import DB_NAME, DB_TEST_NAME
from db.Database import Database
from spotify.types import Listen, Track, User
from spotipy.oauth2 import SpotifyOAuth

MAX_TRACKS_REQUEST = 30
MAX_RETRIES_SUBSTR = "Max Retries"


class SpotifyClient:
    client: spotipy.Spotify
    db: Database
    user: User

    def __init__(self, backoff_factor: float = 0.3, is_test: bool = False) -> None:
        client_id, client_secret = self.get_host_constants(is_test)
        self.client = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=REDIRECT_URI,
                scope=DEFAULT_SCOPE,
            ),
            backoff_factor=backoff_factor,
        )
        self.user = self.gen_current_user()

        self.db = Database(user=self.user, db_name=DB_TEST_NAME if is_test else DB_NAME)

    # get client id and secret if exists, otherwise get user input
    def get_host_constants(self, is_test: bool = False) -> Tuple[str, str]:
        host_constants_path = (
            HOST_CONSTANTS_TEST_PATH if is_test else HOST_CONSTANTS_PATH
        )
        try:
            host_constants_spec = __import__(
                "/".join(host_constants_path.split("/")[1:]),
                globals(),
                locals(),
                ["CLIENT_ID", "CLIENT_SECRET"],
                0,
            )
            return (host_constants_spec.CLIENT_ID, host_constants_spec.CLIENT_SECRET)
        except:
            # constants file not found, get user input
            client_id = input("Please input your Spotify API client ID: ")
            client_secret = getpass.getpass(
                "Please input your Spotify API client secret: "
            )
            f = open(".".join((host_constants_path, "py")), "w")
            f.write('CLIENT_ID = "' + client_id + '"\n')
            f.write('CLIENT_SECRET = "' + client_secret + '"')
            f.close()
            return (client_id, client_secret)

    def gen_current_user(self) -> User:
        res = self.client.current_user()
        if not res:
            raise Exception("No user found")
        return User.from_dict(res)

    def gen_tracks(self, track_ids: List[str]) -> Set[Track]:
        if len(track_ids) > MAX_TRACKS_REQUEST:
            raise Exception(
                f"Too many tracks requested. Max tracks per request is {MAX_TRACKS_REQUEST}"
            )

        res = self.client.tracks(track_ids)
        if not res:
            raise Exception("No tracks found")

        tracks_batch = [{"track": track} for track in res["tracks"]]
        self.load_artist_genres_for_track_dict(tracks_batch)
        return {Track.from_dict(track["track"]) for track in tracks_batch}

    def gen_most_recent_listens(
        self, user: User, after: Optional[datetime] = None
    ) -> List[Listen]:
        after_ts = (
            int(after.replace(tzinfo=timezone.utc).timestamp() * 1000)
            if after
            else None
        )
        res = self.client.current_user_recently_played(
            limit=MAXIMUM_RECENT_TRACKS, after=after_ts
        )
        if not res:
            raise Exception("No recents found")
        recent_tracks = res["items"]
        if len(recent_tracks) == 0:
            return []
        self.load_artist_genres_for_track_dict(recent_tracks)

        return [Listen.from_dict(track, user) for track in recent_tracks]

    def load_artist_genres_for_track_dict(self, tracks: List[Dict[str, Any]]) -> None:
        all_artist_ids = set(
            [artist["id"] for track in tracks for artist in track["track"]["artists"]]
        )
        artists_res = self.client.artists(all_artist_ids)
        if not artists_res:
            raise Exception("No artists found")
        artist_genres = {
            artist["id"]: artist["genres"] for artist in artists_res["artists"]
        }
        for track in tracks:
            for artist in track["track"]["artists"]:
                artist["genres"] = artist_genres[artist["id"]]

    def gen_run_cron_recent_listens(self) -> None:
        after_ts = self.db.get_most_recent_listen_time(self.user)
        recent_listens = self.gen_most_recent_listens(self.user, after_ts)
        if len(recent_listens) == 0:
            return
        self.db.upsert_cron_recent_listens(recent_listens)

    def gen_run_cron_unknown_tracks(self) -> None:
        unknown_track_ids = self.db.get_track_ids_missing_info(MAX_TRACKS_REQUEST)
        if len(unknown_track_ids) == 0:
            return
        tracks = self.gen_tracks(list(unknown_track_ids))
        self.db.upsert_cron_tracks_missing_info(tracks, unknown_track_ids)

    def gen_all_listens(self, ds: Optional[datetime]) -> Set[Listen]:
        return self.db.get_all_listens(self.user, ds)
