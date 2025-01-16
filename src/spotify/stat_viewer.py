import os
import time
from collections import Counter
from datetime import datetime
from typing import Optional, Set

from constants import APP_TITLE

from menu_listener.spinner import Spinner
from prettytable import PrettyTable
from spotify.types import Listen
from spotify_client import SpotifyClient

NUM_DISPLAY_ITEMS = 10
MAX_ENTRY_LENGTH = 30


class StatViewer:
    client: SpotifyClient
    ds: Optional[datetime]
    listens: Set[Listen]

    def __init__(self, ds: Optional[datetime]) -> None:
        self.client = SpotifyClient()
        self.ds = ds

        os.system("clear")
        print(f"{APP_TITLE}\n")
        with Spinner("Fetching listen history..."):
            time.sleep(1)
            self.listens = self.client.gen_all_listens(self.ds)

    def trim_str(self, s: str) -> str:
        if len(s) > MAX_ENTRY_LENGTH:
            return s[: MAX_ENTRY_LENGTH - 3] + "..."
        return s

    def display(self) -> None:
        os.system("clear")
        print(f"{APP_TITLE}\n")

        # get sorted top tracks
        top_tracks = Counter([listen.track for listen in self.listens])
        top_tracks_table = PrettyTable(["Rank", "Title", "Artists", "Listens"])
        top_tracks_table.add_rows(
            [
                [
                    i + 1,
                    self.trim_str(track.name),
                    ", ".join([artist.name for artist in track.artists]),
                    count,
                ]
                for i, (track, count) in enumerate(
                    top_tracks.most_common(NUM_DISPLAY_ITEMS)
                )
            ]
        )
        print(
            "Your top tracks "
            + (
                "of all time"
                if self.ds is None
                else f"since {self.ds.strftime('%Y-%m-%d')}"
            )
            + ":\n"
        )
        print(top_tracks_table)

        print("\nPress Enter to return to the previous menu.")
        input()
