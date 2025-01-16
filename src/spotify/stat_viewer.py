import os
import time
from datetime import datetime
from typing import Optional, Set

from constants import APP_TITLE

from menu_listener.spinner import Spinner
from spotify.types import Listen
from spotify_client import SpotifyClient


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

    def display(self) -> None:
        os.system("clear")
        print(f"{APP_TITLE}\n")
        print("TODO: display your stats.")
        print("\nPress Enter to return to the previous menu.")
        input()
