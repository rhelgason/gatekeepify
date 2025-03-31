import json
import os
from datetime import datetime
from time import time
from typing import Any, Dict, List, Set

from db.constants import DB_NAME, DB_TEST_NAME
from db.Database import Database
from menu_listener.progress_bar import (
    MAX_PERCENTAGE,
    should_update_progress_bar,
    use_progress_bar,
)
from spotify.types import Listen, Track, User
from spotify_client import SpotifyClient
from utils import clear_terminal

BACKFILL_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
FILE_PREFIX = "Streaming_History_Audio"
FILE_SUFFIX = ".json"
MIN_PLAY_TIME_MS = 30000  # 30 seconds
TRACK_URI_PREFIX = "spotify:track:"
TEST_DIRECTORY = "tests/test_data"


class BackfillDataLoader:
    client: SpotifyClient
    db: Database
    user: User
    directory_path: str
    listens: Set[Listen]
    listens_json: List[Dict[str, Any]]

    def __init__(self, is_test: bool = False) -> None:
        self.client = SpotifyClient(
            is_test=is_test
        )
        self.user = self.client.gen_current_user()
        self.db = Database(user=self.user, db_name=DB_TEST_NAME if is_test else DB_NAME)
        self.listens = set()

        if is_test:
            self.directory_path = TEST_DIRECTORY
        else:
            clear_terminal()
            self.directory_path = input(
                "Enter absolute path to Spotify data directory: "
            )
        if not os.path.exists(self.directory_path):
            raise ValueError(f"Directory {self.directory_path} does not exist.")

        self._load_listens()

    def _load_listens(self) -> None:
        print(
            "Loading data from local files..."
        )
        self.listens_json = []
        for file in os.listdir(self.directory_path):
            if file.startswith(FILE_PREFIX) and file.endswith(FILE_SUFFIX):
                with open(os.path.join(self.directory_path, file), "r") as f:
                    json_arr = json.load(f)
                    self.listens_json.extend(json_arr)
        self.listens_json = list(
            filter(
                lambda listen_json: listen_json["ms_played"] >= MIN_PLAY_TIME_MS
                and listen_json["spotify_track_uri"] is not None,
                self.listens_json,
            )
        )

        # map json to dict of track id to list of timestamps
        start = time()
        num_listens = len(self.listens_json)
        track_to_timestamps: Dict[Track, List[datetime]] = {}
        for i, listen_json in enumerate(self.listens_json):
            track_id = str(
                listen_json["spotify_track_uri"].removeprefix(TRACK_URI_PREFIX)
            )
            track_name = str(listen_json["master_metadata_track_name"])
            if not track_id or not track_name:
                continue
            track = Track(
                id=track_id,
                name=track_name,
            )

            if track not in track_to_timestamps:
                track_to_timestamps[track] = []
            track_to_timestamps[track].append(
                datetime.strptime(listen_json["ts"], BACKFILL_DATETIME_FORMAT)
            )
            if should_update_progress_bar():
                progress = int((i / num_listens) * MAX_PERCENTAGE)
                use_progress_bar(progress, start, time())
        end = time()
        use_progress_bar(MAX_PERCENTAGE, start, end)

        print("\n\nMapping JSON data to object type...")
        start = time()
        num_tracks = len(track_to_timestamps)
        self.listens = set()
        for i, (track, timestamps) in enumerate(track_to_timestamps.items()):
            for ts in timestamps:
                self.listens.add(
                    Listen(
                        user=self.user,
                        track=track,
                        ts=ts,
                    )
                )
            if should_update_progress_bar():
                progress = int((i / num_tracks) * MAX_PERCENTAGE)
                use_progress_bar(progress, start, time())
        end = time()
        use_progress_bar(MAX_PERCENTAGE, start, end)

    def validate_listens(self) -> None:
        pass

    def write_listens(self) -> None:
        pass
