import os
import unittest
from datetime import datetime
from typing import Dict

from constants import CLIENT_DATETIME_FORMAT
from db.constants import DB_DIRECTORY, DB_TEST_NAME

from db.Database import Database
from spotify.types import Album, Artist, Track, User


class TestDatabase(unittest.TestCase):
    db: Database
    user_1: User
    track_1: Track
    track_2: Track
    base_upsert_data: Dict[datetime, Track]

    def setUp(self) -> None:
        self.db = Database(db_name=DB_TEST_NAME)
        self.user_1 = User("12345", "test user")
        self.track_1 = Track(
            "123",
            "test track",
            Album("234", "test album"),
            [Artist("345", "test artist"), Artist("678", "test artist 2")],
        )
        self.track_2 = Track(
            "456",
            "test track 2",
            Album("567", "test album 2"),
            [Artist("678", "test artist 2"), Artist("912", "test artist 3")],
        )
        self.base_upsert_data = {
            datetime.strptime(
                "2024-12-27T22:30:04.214000Z", CLIENT_DATETIME_FORMAT
            ): self.track_1,
            datetime.strptime(
                "2024-12-26T16:48:12.712392Z", CLIENT_DATETIME_FORMAT
            ): self.track_2,
        }

        self.db.upsert_cron_backfill(
            self.user_1,
            self.base_upsert_data,
        )

    def test_upsert_dim_all_albums(self) -> None:
        # base upsert case
        all_albums = self.db.get_all_albums()
        self.assertEqual(len(all_albums), 2)
        self.assertEqual(
            sorted(list(all_albums)),
            [Album("234", "test album"), Album("567", "test album 2")],
        )

        # overwrite existing album with new name
        self.track_1.album = Album("234", "test album new name")
        self.db.upsert_cron_backfill(self.user_1, self.base_upsert_data)
        all_albums = self.db.get_all_albums()
        self.assertEqual(len(all_albums), 2)
        self.assertEqual(
            sorted(list(all_albums)),
            [Album("234", "test album new name"), Album("567", "test album 2")],
        )

    def test_upsert_dim_all_artists(self) -> None:
        # base upsert case
        all_artists = self.db.get_all_artists()
        self.assertEqual(len(all_artists), 3)
        self.assertEqual(
            sorted(list(all_artists)),
            [
                Artist("345", "test artist"),
                Artist("678", "test artist 2"),
                Artist("912", "test artist 3"),
            ],
        )

        # overwrite existing artist with new name
        self.track_1.artists = [
            Artist("345", "test artist new name"),
            Artist("678", "test artist 2"),
        ]
        self.db.upsert_cron_backfill(self.user_1, self.base_upsert_data)
        all_artists = self.db.get_all_artists()
        self.assertEqual(len(all_artists), 3)
        self.assertEqual(
            sorted(list(all_artists)),
            [
                Artist("345", "test artist new name"),
                Artist("678", "test artist 2"),
                Artist("912", "test artist 3"),
            ],
        )

    def tearDown(self) -> None:
        if self.db.conn:
            self.db.conn.close()
        os.remove(os.path.join(DB_DIRECTORY, DB_TEST_NAME))