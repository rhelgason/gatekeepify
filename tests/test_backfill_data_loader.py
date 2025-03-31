import os
import unittest
from datetime import datetime
from unittest.mock import patch

from constants import CLIENT_DATETIME_FORMAT, HOST_CONSTANTS_TEST_PATH

from db.constants import DB_DIRECTORY, DB_TEST_NAME
from db.Database import Database
from spotify.backfill_data_loader import BackfillDataLoader, FILE_PREFIX, TEST_DIRECTORY
from spotify.types import Album, Artist, Listen, Track, User

CLIENT_ID = "test_id"
CLIENT_SECRET = "test_secret"
TEST_FILE_1 = FILE_PREFIX + "_test_file_1.json"
TEST_FILE_2 = FILE_PREFIX + "_test_file_2.json"
TEST_FILE_3 = "test_file_3.json"


@patch(
    "spotipy.Spotify.current_user",
    return_value={"id": "12345", "display_name": "test user"},
)
@patch("builtins.input", side_effect=[CLIENT_ID])
@patch("getpass.getpass", return_value=CLIENT_SECRET)
class TestBackfillDataLoader(unittest.TestCase):
    db: Database
    data_loader: BackfillDataLoader
    path: str

    track_1: Track
    track_2: Track
    listen_1: Listen
    listen_2: Listen
    listen_3: Listen

    def setUp(self) -> None:
        # set up test database
        self.db = Database(db_name=DB_TEST_NAME)
        self.track_1 = Track(
            "123",
            "test track",
        )
        self.track_2 = Track(
            "456",
            "test track 2",
        )
        self.listen_1 = Listen(
            User("12345", "test user"),
            self.track_1,
            datetime.strptime("2024-12-26T22:30:04.000000Z", CLIENT_DATETIME_FORMAT),
        )
        self.listen_2 = Listen(
            User("12345", "test user"),
            self.track_2,
            datetime.strptime("2024-12-28T22:30:05.000000Z", CLIENT_DATETIME_FORMAT),
        )
        self.listen_3 = Listen(
            User("12345", "test user"),
            self.track_1,
            datetime.strptime("2024-12-12T22:30:04.000000Z", CLIENT_DATETIME_FORMAT),
        )
        self.db.upsert_cron_backfill([self.listen_1])

        # set up spotify client
        self.path = ".".join((HOST_CONSTANTS_TEST_PATH, "py"))
        try:
            os.remove(self.path)
        except OSError:
            pass

        # set up test json files
        os.mkdir(TEST_DIRECTORY)
        with open(os.path.join(TEST_DIRECTORY, TEST_FILE_1), "w") as f:
            f.write(
                """
                [
                    {
                        "ts": "2024-12-26T22:30:04Z",
                        "ms_played": 51555,
                        "master_metadata_track_name": "test track",
                        "spotify_track_uri": "spotify:track:123"
                    },
                    {
                        "ts": "2024-12-28T22:30:05Z",
                        "ms_played": 35000,
                        "master_metadata_track_name": "test track 2",
                        "spotify_track_uri": "spotify:track:456"
                    }
                ]
                """
            )
        with open(os.path.join(TEST_DIRECTORY, TEST_FILE_2), "w") as f:
            f.write(
                """
                [
                    {
                        "ts": "2024-12-12T22:30:04Z",
                        "ms_played": 51555,
                        "master_metadata_track_name": "test track",
                        "spotify_track_uri": "spotify:track:123"
                    },
                    {
                        "ts": "2024-12-19T22:30:05Z",
                        "ms_played": 3000,
                        "master_metadata_track_name": "test track 2",
                        "spotify_track_uri": "spotify:track:456"
                    }
                ]
                """
            )
        with open(os.path.join(TEST_DIRECTORY, TEST_FILE_3), "w") as f:
            f.write(
                """
                [
                    {
                        "ts": "2017-02-28T00:43:32Z",
                        "ms_played": 2275,
                        "master_metadata_track_name": "test track",
                        "master_metadata_album_artist_name": "test artist",
                        "master_metadata_album_album_name": "test album",
                        "spotify_track_uri": "spotify:track:123",
                    },
                ]
                """
            )

    def test_full_backfill(
        self, mock_getpass, mock_input, mock_current_user
    ) -> None:
        self.data_loader = BackfillDataLoader(is_test=True)
        self.assertEqual(len(self.data_loader.listens_json), 3)
        self.assertListEqual(
            self.data_loader.listens_json,
            [
                {
                    "ts": "2024-12-12T22:30:04Z",
                    "ms_played": 51555,
                    "master_metadata_track_name": "test track",
                    "spotify_track_uri": "spotify:track:123",
                },
                {
                    "ts": "2024-12-26T22:30:04Z",
                    "ms_played": 51555,
                    "master_metadata_track_name": "test track",
                    "spotify_track_uri": "spotify:track:123",
                },
                {
                    "ts": "2024-12-28T22:30:05Z",
                    "ms_played": 35000,
                    "master_metadata_track_name": "test track 2",
                    "spotify_track_uri": "spotify:track:456",
                },
            ],
        )

        self.assertEqual(len(self.data_loader.listens), 3)
        self.assertListEqual(
            sorted(self.data_loader.listens),
            sorted(
                [
                    self.listen_1,
                    self.listen_2,
                    self.listen_3,
                ]
            ),
        )

    def tearDown(self) -> None:
        os.remove(os.path.join(TEST_DIRECTORY, TEST_FILE_1))
        os.remove(os.path.join(TEST_DIRECTORY, TEST_FILE_2))
        os.remove(os.path.join(TEST_DIRECTORY, TEST_FILE_3))
        os.rmdir(TEST_DIRECTORY)

        if self.db.conn:
            self.db.conn.close()
        os.remove(os.path.join(DB_DIRECTORY, DB_TEST_NAME))
