import math
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, TypeVar

from menu_listener.spinner import Spinner
from prettytable import PrettyTable
from spotify.types import Artist, Listen, Track
from spotify_client import SpotifyClient

from utils import clear_terminal

NUM_SPOTIFY_WRAPPED_ITEMS = 5
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

        clear_terminal()
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
        self, counter: Counter[T], minutes: Dict[str, int], max_values: int
    ) -> List[Tuple[T, int]]:
        return sorted(
            counter.most_common(max_values),
            key=lambda x: (
                -x[1],
                -minutes[x[0] if isinstance(x[0], str) else getattr(x[0], "id", "")],
            ),
        )

    def _get_all_stats_tables(self) -> List[PrettyTable]:
        top_artists, _ = self._get_top_artists(NUM_SPOTIFY_WRAPPED_ITEMS)
        num_artists = len(top_artists)
        top_tracks, _ = self._get_top_tracks(NUM_SPOTIFY_WRAPPED_ITEMS)
        num_tracks = len(top_tracks)
        top_items_table = PrettyTable([" ", "Top Artists", "\t", "  ", "Top Songs"])
        top_items_table.add_rows(
            [
                [
                    i + 1 if i < num_artists else "",
                    self._trim_str(top_artists[i][0].name) if i < num_artists else "",
                    "\t",
                    i + 1 if i < num_tracks else "",
                    self._trim_str(top_tracks[i][0].name) if i < num_tracks else "",
                ]
                for i in range(
                    min(NUM_SPOTIFY_WRAPPED_ITEMS, max(num_artists, num_tracks))
                )
            ]
        )

        tables = [top_items_table]
        for table in tables:
            table.border = False
            table.align = "l"
        return tables

    def _get_top_tracks(
        self, max_values: int = NUM_DISPLAY_ITEMS
    ) -> Tuple[List[Tuple[Track, int]], Dict[str, int]]:
        top_tracks = Counter([listen.track for listen in self.listens])
        top_track_minutes = {}
        for listen in self.listens:
            top_track_minutes[listen.track.id] = (
                top_track_minutes.get(listen.track.id, 0) + listen.track.duration_ms
            )
        top_tracks = self._sort_counter(top_tracks, top_track_minutes, max_values)
        return top_tracks, top_track_minutes

    def _get_top_tracks_table(self) -> PrettyTable:
        top_tracks, top_track_minutes = self._get_top_tracks()
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
                for i, (track, count) in enumerate(top_tracks)
            ]
        )
        return top_tracks_table

    def _get_top_artists(
        self, max_values: int = NUM_DISPLAY_ITEMS
    ) -> Tuple[List[Tuple[Artist, int]], Dict[str, int]]:
        top_artists = Counter(
            [artist for listen in self.listens for artist in listen.track.artists]
        )
        top_artist_minutes = {}
        for listen in self.listens:
            for artist in listen.track.artists:
                top_artist_minutes[artist.id] = (
                    top_artist_minutes.get(artist.id, 0) + listen.track.duration_ms
                )
        top_artists = self._sort_counter(top_artists, top_artist_minutes, max_values)
        return top_artists, top_artist_minutes

    def _get_top_artists_table(self) -> PrettyTable:
        top_artists, top_artist_minutes = self._get_top_artists()
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
                for i, (artist, count) in enumerate(top_artists)
            ]
        )
        return top_artists_table

    def _get_top_genres(
        self, max_values: int = NUM_DISPLAY_ITEMS
    ) -> Tuple[List[Tuple[str, int]], Dict[str, int]]:
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
        top_genres = self._sort_counter(top_genres, top_genre_minutes, max_values)
        return top_genres, top_genre_minutes

    def _get_top_genres_table(self) -> PrettyTable:
        top_genres, top_genre_minutes = self._get_top_genres()
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
                for i, (genre, count) in enumerate(top_genres)
            ]
        )
        return top_genres_table

    def all_stats(self) -> None:
        clear_terminal()
        all_stats_tables = self._get_all_stats_tables()
        current_year = str(self.ds.year) if self.ds is not None else ""
        print(f"Your predicted Spotify Wrapper for {current_year}: \n")
        for table in all_stats_tables:
            print(table, "\n")

        print("\nPress Enter to return to the previous menu.")
        input()

    def top_tracks(self) -> None:
        clear_terminal()
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
        clear_terminal()
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
        clear_terminal()
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
