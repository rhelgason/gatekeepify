import math
import os
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, TypeVar

from constants import APP_TITLE

from menu_listener.spinner import Spinner
from prettytable import PrettyTable
from spotify.types import Listen
from spotify_client import SpotifyClient

NUM_DISPLAY_ITEMS = 10
MAX_ENTRY_LENGTH = 30

T = TypeVar("T")


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

    def _trim_str(self, s: str) -> str:
        if len(s) > MAX_ENTRY_LENGTH:
            return s[: MAX_ENTRY_LENGTH - 3] + "..."
        return s

    def _get_minutes_from_ms(self, ms: int) -> int:
        return math.floor(ms / 1000 / 60)

    # Custom sorting function for each table prior to output. Assumes the invariant
    # that each key in the counter has an ID that is also in the minutes dict.
    # Currently sorts by the number of listens first, then by the number of minutes.
    def _sort_counter(
        self, counter: Counter[T], minutes: Dict[str, int]
    ) -> List[Tuple[T, int]]:
        return sorted(
            counter.most_common(NUM_DISPLAY_ITEMS),
            key=lambda x: (
                -x[1],
                -minutes[x[0] if isinstance(x[0], str) else getattr(x[0], "id", "")],
            ),
        )

    def _get_top_tracks_table(self) -> PrettyTable:
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
                    self._trim_str(track.name),
                    self._trim_str(
                        ", ".join([artist.name for artist in track.artists])
                    ),
                    count,
                    self._get_minutes_from_ms(top_track_minutes[track.id]),
                ]
                for i, (track, count) in enumerate(
                    self._sort_counter(top_tracks, top_track_minutes)
                )
            ]
        )
        return top_tracks_table

    def _get_top_artists_table(self) -> PrettyTable:
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
                    self._trim_str(artist.name),
                    self._trim_str(", ".join(artist.genres or [])),
                    count,
                    self._get_minutes_from_ms(top_artist_minutes[artist.id]),
                ]
                for i, (artist, count) in enumerate(
                    self._sort_counter(top_artists, top_artist_minutes)
                )
            ]
        )
        return top_artists_table

    def _get_top_genres_table(self) -> PrettyTable:
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
                    self._trim_str(genre),
                    count,
                    self._get_minutes_from_ms(top_genre_minutes[genre]),
                ]
                for i, (genre, count) in enumerate(
                    self._sort_counter(top_genres, top_genre_minutes)
                )
            ]
        )
        return top_genres_table

    def all_stats(self) -> None:
        os.system("clear")
        print(f"{APP_TITLE}\n")
        print("\nPress Enter to return to the previous menu.")
        input()

    def top_tracks(self) -> None:
        os.system("clear")
        print(f"{APP_TITLE}\n")
        top_tracks_table = self._get_top_tracks_table()
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

    def top_artists(self) -> None:
        os.system("clear")
        print(f"{APP_TITLE}\n")
        top_artists_table = self._get_top_artists_table()
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

    def top_genres(self) -> None:
        os.system("clear")
        print(f"{APP_TITLE}\n")
        top_genres_table = self._get_top_genres_table()
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
