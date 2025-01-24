import math
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

    def get_minutes_from_ms(self, ms: int) -> int:
        return math.floor(ms / 1000 / 60)

    def get_top_tracks_table(self) -> PrettyTable:
        top_tracks = Counter([listen.track for listen in self.listens])
        top_track_minutes = {}
        for listen in self.listens:
            top_track_minutes[listen.track.id] = (
                top_track_minutes.get(listen.track.id, 0) + listen.track.duration_ms
            )

        top_tracks_table = PrettyTable(
            ["Rank", "Title", "Artists", "Listen Count", "Minutes Listened"]
        )
        top_tracks_table.add_rows(
            [
                [
                    i + 1,
                    self.trim_str(track.name),
                    self.trim_str(", ".join([artist.name for artist in track.artists])),
                    count,
                    self.get_minutes_from_ms(top_track_minutes[track.id]),
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
        top_artist_minutes = {}
        for listen in self.listens:
            for artist in listen.track.artists:
                top_artist_minutes[artist.id] = (
                    top_artist_minutes.get(artist.id, 0) + listen.track.duration_ms
                )

        top_artists_table = PrettyTable(
            ["Rank", "Artist", "Genres", "Listen Count", "Minutes Listened"]
        )
        top_artists_table.add_rows(
            [
                [
                    i + 1,
                    self.trim_str(artist.name),
                    self.trim_str(", ".join(artist.genres or [])),
                    count,
                    self.get_minutes_from_ms(top_artist_minutes[artist.id]),
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
        top_genres = Counter()
        top_genre_minutes = {}
        for listen in self.listens:
            track_genres = set()
            for artist in listen.track.artists:
                for genre in artist.genres:
                    track_genres.add(genre)
            top_genres.update(track_genres)
            for genre in track_genres:
                top_genre_minutes[genre] = (
                    top_genre_minutes.get(genre, 0) + listen.track.duration_ms
                )

        top_genres_table = PrettyTable(
            ["Rank", "Genre", "Listen Count", "Minutes Listened"]
        )
        top_genres_table.add_rows(
            [
                [
                    i + 1,
                    self.trim_str(genre),
                    count,
                    self.get_minutes_from_ms(top_genre_minutes[genre]),
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
