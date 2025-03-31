import os
import unittest
from copy import deepcopy
from datetime import datetime
from typing import List

from constants import CLIENT_DATETIME_FORMAT
from db.constants import DB_DIRECTORY, DB_TEST_NAME, LoggerAction

from db.Database import Database
from spotify.types import Album, Artist, Listen, Track, User


class TestDatabase(unittest.TestCase):
    db: Database
    artist_1: Artist
    artist_2: Artist
    artist_3: Artist
    track_1: Track
    track_2: Track
    listen_1: Listen
    listen_2: Listen
    base_upsert_data: List[Listen]

    def setUp(self) -> None:
        self.user = User(
            id="123456789",
            name="test user"
        )
        self.db = Database(user=self.user, db_name=DB_TEST_NAME)
        self.artist_1 = Artist("345", "test artist", ["test genre", "test genre 2"])
        self.artist_2 = Artist("678", "test artist 2", ["test genre 2", "test genre 3"])
        self.artist_3 = Artist("912", "test artist 3", ["test genre", "test genre 3"])
        self.track_1 = Track(
            "123",
            "test track",
            Album("234", "test album"),
            [
                self.artist_1,
                self.artist_2,
            ],
            240000,
            False,
        )
        self.track_2 = Track(
            "456",
            "test track 2",
            Album("567", "test album 2"),
            [
                self.artist_2,
                self.artist_3,
            ],
            240000,
            True,
        )
        self.listen_1 = Listen(
            User("12345", "test user"),
            self.track_1,
            datetime.strptime("2024-12-26T22:30:04.214000Z", CLIENT_DATETIME_FORMAT),
        )
        self.listen_2 = Listen(
            User("6789", "test user 2"),
            self.track_2,
            datetime.strptime("2024-12-27T16:48:12.712392Z", CLIENT_DATETIME_FORMAT),
        )
        self.base_upsert_data = [self.listen_1, self.listen_2]

        self.db.upsert_cron_backfill(self.base_upsert_data)

    def assertLogsWrittenToDb(self, action: LoggerAction, count: int) -> None:
        query = """
        SELECT COUNT(*) FROM dim_all_logs WHERE action = ?
        """
        self.db.cursor.execute(query, (action.value,))
        results = self.db.cursor.fetchall()
        self.assertEqual(results[0][0], count)

    def test_upsert_dim_all_albums(self) -> None:
        # base upsert case
        all_albums = self.db.get_all_albums()
        self.assertEqual(len(all_albums), 2)
        self.assertEqual(
            sorted(list(all_albums)),
            [Album("234", "test album"), Album("567", "test album 2")],
        )

        # overwrite existing album with new name
        self.listen_1.track.album = Album("234", "test album new name")
        self.db.upsert_cron_backfill(self.base_upsert_data)
        all_albums = self.db.get_all_albums()
        self.assertEqual(len(all_albums), 2)
        self.assertEqual(
            sorted(list(all_albums)),
            [Album("234", "test album new name"), Album("567", "test album 2")],
        )

        self.assertLogsWrittenToDb(LoggerAction.UPSERT_DIM_ALL_ALBUMS, 2)

    def test_upsert_dim_all_tracks(self) -> None:
        # base upsert case
        all_tracks = self.db.get_all_tracks()
        self.assertEqual(len(all_tracks), 2)
        self.assertEqual(
            sorted(list(all_tracks)),
            [self.listen_1.track, self.listen_2.track],
        )

        # overwrite existing track with new name, artist, duration, and is_local flag
        self.track_1.name = "test track new name"
        self.track_1.artists = [
            self.artist_2,
            Artist("6789", "test artist 4", ["test genre 3"]),
        ]
        self.track_1.duration_ms = 300000
        self.track_1.is_local = True
        self.track_2.album = Album("567", "test album 2 new name")
        self.listen_1.track = self.track_1
        self.listen_2.track = self.track_2
        self.db.upsert_cron_backfill(self.base_upsert_data)
        all_tracks = self.db.get_all_tracks()
        self.assertEqual(len(all_tracks), 2)
        self.assertEqual(
            sorted(list(all_tracks)),
            [self.listen_1.track, self.listen_2.track],
        )

        self.assertLogsWrittenToDb(LoggerAction.UPSERT_DIM_ALL_TRACKS, 2)

    def test_upsert_dim_all_artists(self) -> None:
        # base upsert case
        all_artists = self.db.get_all_artists()
        self.assertEqual(len(all_artists), 3)
        self.assertEqual(
            sorted(list(all_artists)),
            [
                self.artist_1,
                self.artist_2,
                self.artist_3,
            ],
        )

        # overwrite existing artist with new name and genres
        self.artist_1 = Artist(
            "345", "test artist new name", ["test genre 2", "test genre 3"]
        )
        self.listen_1.track.artists = [
            self.artist_1,
            self.artist_2,
        ]
        self.db.upsert_cron_backfill(self.base_upsert_data)
        all_artists = self.db.get_all_artists()
        self.assertEqual(len(all_artists), 3)
        self.assertEqual(
            sorted(list(all_artists)),
            [
                self.artist_1,
                self.artist_2,
                self.artist_3,
            ],
        )

        self.assertLogsWrittenToDb(LoggerAction.UPSERT_DIM_ALL_ARTISTS, 2)

    def test_upsert_track_to_artist(self) -> None:
        # base upsert case
        query = """
        SELECT track_id, artist_id FROM track_to_artist
        WHERE track_id = '123'
        """
        self.db.cursor.execute(query)
        results = self.db.cursor.fetchall()
        self.assertEqual(len(results), 2)
        self.assertEqual(
            sorted(list(results)),
            [(self.track_1.id, "345"), (self.track_1.id, "678")],
        )

        # overwrite existing track with new artist
        self.track_1.artists = [
            self.artist_2,
            self.artist_3,
        ]
        self.listen_1.track = self.track_1
        self.db.upsert_cron_backfill(self.base_upsert_data)
        self.db.cursor.execute(query)
        results = self.db.cursor.fetchall()
        self.assertEqual(len(results), 2)
        self.assertEqual(
            sorted(list(results)),
            [(self.track_1.id, "678"), (self.track_1.id, "912")],
        )

        self.assertLogsWrittenToDb(LoggerAction.UPSERT_TRACK_TO_ARTIST, 2)

    def test_upsert_artist_to_genre(self) -> None:
        # base upsert case
        query = """
        SELECT artist_id, genre FROM artist_to_genre
        WHERE artist_id = '345'
        """
        self.db.cursor.execute(query)
        results = self.db.cursor.fetchall()
        self.assertEqual(len(results), 2)
        self.assertEqual(
            sorted(list(results)),
            [
                (self.artist_1.id, "test genre"),
                (self.artist_1.id, "test genre 2"),
            ],
        )

        # overwrite existing artist with new genres
        self.artist_1 = Artist("345", "test artist", ["test genre 3", "test genre 2"])
        self.listen_1.track.artists = [
            self.artist_1,
            self.artist_2,
        ]
        self.db.upsert_cron_backfill(self.base_upsert_data)
        self.db.cursor.execute(query)
        results = self.db.cursor.fetchall()
        self.assertEqual(len(results), 2)
        self.assertEqual(
            sorted(list(results)),
            [
                (self.artist_1.id, "test genre 2"),
                (self.artist_1.id, "test genre 3"),
            ],
        )

        self.assertLogsWrittenToDb(LoggerAction.UPSERT_ARTIST_TO_GENRE, 2)

    def test_upsert_dim_all_users(self) -> None:
        # base upsert case
        all_users = self.db.get_all_users()
        self.assertEqual(len(all_users), 2)
        self.assertEqual(
            sorted(list(all_users)),
            [self.listen_1.user, self.listen_2.user],
        )

        # overwrite existing user with new name
        self.listen_1.user.name = "test user new name"
        self.db.upsert_cron_backfill(self.base_upsert_data)
        all_users = self.db.get_all_users()
        self.assertEqual(len(all_users), 2)
        self.assertEqual(
            sorted(list(all_users)),
            [self.listen_1.user, self.listen_2.user],
        )

        self.assertLogsWrittenToDb(LoggerAction.UPSERT_DIM_ALL_USERS, 2)

    def test_upsert_dim_all_listens(self) -> None:
        # base upsert case
        all_listens = self.db.get_all_listens()
        self.assertEqual(len(all_listens), 2)
        self.assertEqual(
            sorted(list(all_listens)),
            [self.listen_1, self.listen_2],
        )

        # add equivalent listen with different user
        listen_3 = deepcopy(self.listen_2)
        listen_3.user = User("12345", "test user")
        self.base_upsert_data.append(listen_3)
        self.db.upsert_cron_backfill(self.base_upsert_data)
        all_listens = self.db.get_all_listens()
        self.assertEqual(len(all_listens), 3)
        self.assertEqual(
            sorted(list(all_listens)),
            [self.listen_1, listen_3, self.listen_2],
        )

        self.assertLogsWrittenToDb(LoggerAction.UPSERT_DIM_ALL_LISTENS, 2)

    def test_get_all_listens(self) -> None:
        listen_3 = deepcopy(self.listen_2)
        listen_3.user = User("12345", "test user")
        self.base_upsert_data.append(listen_3)
        self.db.upsert_cron_backfill(self.base_upsert_data)

        # query by user only
        all_listens = self.db.get_all_listens(User("12345", "test user"))
        self.assertEqual(len(all_listens), 2)
        self.assertEqual(
            sorted(list(all_listens)),
            [self.listen_1, listen_3],
        )

        # query by timestamp only
        all_listens = self.db.get_all_listens(
            None,
            datetime.strptime("2024-12-27T00:00:00.000000Z", CLIENT_DATETIME_FORMAT),
        )
        self.assertEqual(len(all_listens), 2)
        self.assertEqual(
            sorted(list(all_listens)),
            [listen_3, self.listen_2],
        )

        # query by user and timestamp
        all_listens = self.db.get_all_listens(
            User("12345", "test user"),
            datetime.strptime("2024-12-27T00:00:00.000000Z", CLIENT_DATETIME_FORMAT),
        )
        self.assertEqual(len(all_listens), 1)
        self.assertEqual(
            sorted(list(all_listens)),
            [listen_3],
        )

    def tearDown(self) -> None:
        if self.db.conn:
            self.db.conn.close()
        os.remove(os.path.join(DB_DIRECTORY, DB_TEST_NAME))
