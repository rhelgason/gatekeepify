import json
import os
from collections.abc import Callable
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
        self.client = SpotifyClient()
        self.user = self.client.gen_current_user()
        self.db = Database(db_name=DB_TEST_NAME if is_test else DB_NAME)
        self.listens = set()

        if is_test:
            self.directory_path = TEST_DIRECTORY
        else:
            clear_terminal()
            self.directory_path = input(
                "Enter absolute path to Spotify data directory: "
            )

        # check if directory exists
        if not os.path.exists(self.directory_path):
            raise ValueError(f"Directory {self.directory_path} does not exist.")

        self._load_listens()

    def _load_listens(self) -> None:
        clear_terminal()
        print("Loading files from directory...")
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
        track_id_to_timestamps: Dict[str, List[datetime]] = {}
        for i, listen_json in enumerate(self.listens_json):
            track_id = str(
                listen_json["spotify_track_uri"].removeprefix(TRACK_URI_PREFIX)
            )
            if track_id not in track_id_to_timestamps:
                track_id_to_timestamps[track_id] = []
            track_id_to_timestamps[track_id].append(
                datetime.strptime(listen_json["ts"], BACKFILL_DATETIME_FORMAT)
            )
            if should_update_progress_bar():
                progress = int((i / num_listens) * MAX_PERCENTAGE)
                use_progress_bar(progress, start, time())
        end = time()
        use_progress_bar(MAX_PERCENTAGE, start, end)

        start = time()

        def update_progress_bar(num_complete: int) -> None:
            progress = int((num_complete / num_listens) * MAX_PERCENTAGE)
            use_progress_bar(progress, start, time())

        # populate all listens for recognized tracks in batches
        print("\n\nLoading all recognized track information from Spotify...")
        known_tracks = self.db.get_all_tracks_batched(
            track_ids=list(track_id_to_timestamps.keys())
        )
        num_complete = self._populate_listens_from_tracks(
            known_tracks, track_id_to_timestamps, update_progress_bar, 0
        )

        # fetch information for unrecognized tracks
        print("\n\nLoading all unrecognized track information from Spotify...")
        unknown_tracks = self.client.gen_tracks_batched(
            track_ids=list(track_id_to_timestamps.keys()),
        )
        self._populate_listens_from_tracks(
            unknown_tracks, track_id_to_timestamps, update_progress_bar, num_complete
        )
        end = time()
        use_progress_bar(MAX_PERCENTAGE, start, end)

        # throw error if there are still unrecognized tracks
        if len(track_id_to_timestamps) > 0:
            raise ValueError(
                f"Unrecognized track IDs: {', '.join(track_id_to_timestamps.keys())}"
            )

    # iterates through a set of tracks to populate listens
    # returns the number of listens completed so far
    def _populate_listens_from_tracks(
        self,
        tracks: Set[Track],
        track_id_to_timestamps: Dict[str, List[datetime]],
        update_progress_bar: Callable[[int], None],
        num_complete: int,
    ) -> int:
        for track in tracks:
            for ts in track_id_to_timestamps[track.id]:
                self.listens.add(
                    Listen(
                        user=self.user,
                        track=track,
                        ts=ts,
                    )
                )
                num_complete += 1
                if should_update_progress_bar():
                    update_progress_bar(num_complete)
            track_id_to_timestamps.pop(track.id, None)
        return num_complete

    def validate_listens(self) -> None:
        pass

    def write_listens(self) -> None:
        pass
