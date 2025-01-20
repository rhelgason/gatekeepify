import os
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

    def __init__(self, ds: Optional[datetime], is_test: bool = False) -> None:
        self.client = SpotifyClient(is_test=is_test)
        self.ds = ds
        if is_test:
            self.listens = self.client.gen_all_listens(self.ds)
            return

        os.system("clear")
        print(f"{APP_TITLE}\n")
        with Spinner("Fetching listen history..."):
            self.listens = self.client.gen_all_listens(self.ds)

    def trim_str(self, s: str) -> str:
        if len(s) > MAX_ENTRY_LENGTH:
            return s[: MAX_ENTRY_LENGTH - 3] + "..."
        return s

    def get_top_tracks_table(self) -> PrettyTable:
        top_tracks = Counter([listen.track for listen in self.listens])
        top_tracks_table = PrettyTable(["Rank", "Title", "Artists", "Listens"])
        top_tracks_table.add_rows(
            [
                [
                    i + 1,
                    self.trim_str(track.name),
                    self.trim_str(", ".join([artist.name for artist in track.artists])),
                    count,
                ]
                for i, (track, count) in enumerate(
                    top_tracks.most_common(NUM_DISPLAY_ITEMS)
                )
            ]
        )
        return top_tracks_table

    def top_tracks(self) -> None:
        os.system("clear")
        print(f"{APP_TITLE}\n")
        top_tracks_table = self.get_top_tracks_table()
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

    def get_top_artists_table(self) -> PrettyTable:
        top_artists = Counter(
            [artist for listen in self.listens for artist in listen.track.artists]
        )
        top_artists_table = PrettyTable(["Rank", "Artist", "Genres", "Listens"])
        top_artists_table.add_rows(
            [
                [
                    i + 1,
                    self.trim_str(artist.name),
                    self.trim_str(", ".join(artist.genres or [])),
                    count,
                ]
                for i, (artist, count) in enumerate(
                    top_artists.most_common(NUM_DISPLAY_ITEMS)
                )
            ]
        )
        return top_artists_table

    def top_artists(self) -> None:
        os.system("clear")
        print(f"{APP_TITLE}\n")
        top_artists_table = self.get_top_artists_table()
        print(
            "Your top artists "
            + (
                "of all time"
                if self.ds is None
                else f"since {self.ds.strftime('%Y-%m-%d')}"
            )
            + ":\n"
        )
        print(top_artists_table)

        print("\nPress Enter to return to the previous menu.")
        input()

    def get_top_genres_table(self) -> PrettyTable:
        top_genres = Counter(
            [
                x
                for y in (
                    set(
                        [
                            genre
                            for artist in listen.track.artists
                            for genre in artist.genres
                        ]
                    )
                    for listen in self.listens
                )
                for x in y
            ]
        )
        top_genres_table = PrettyTable(["Rank", "Genre", "Listens"])
        top_genres_table.add_rows(
            [
                [
                    i + 1,
                    self.trim_str(genre),
                    count,
                ]
                for i, (genre, count) in enumerate(
                    top_genres.most_common(NUM_DISPLAY_ITEMS)
                )
            ]
        )
        return top_genres_table

    def top_genres(self) -> None:
        os.system("clear")
        print(f"{APP_TITLE}\n")
        top_genres_table = self.get_top_genres_table()
        print(
            "Your top artists "
            + (
                "of all time"
                if self.ds is None
                else f"since {self.ds.strftime('%Y-%m-%d')}"
            )
            + ":\n"
        )
        print(top_genres_table)

        print("\nPress Enter to return to the previous menu.")
        input()
