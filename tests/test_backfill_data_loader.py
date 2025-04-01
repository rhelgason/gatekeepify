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
    return_value={"id": "123456789", "display_name": "test user"},
)
@patch("builtins.input", side_effect=[CLIENT_ID])
@patch("getpass.getpass", return_value=CLIENT_SECRET)
class TestBackfillDataLoader(unittest.TestCase):
    db: Database
    data_loader: BackfillDataLoader
    path: str

    user: User
    album_1: Album
    artist_1: Artist
    track_1: Track
    track_2: Track
    listen_1: Listen
    listen_2: Listen
    listen_3: Listen

    def setUp(self) -> None:
        # set up test database
        self.user = User(id="123456789", name="test user")
        self.db = Database(user=self.user, db_name=DB_TEST_NAME)
        self.album_1 = Album("234", "test album")
        self.artist_1 = Artist("345", "test artist", ["test genre", "test genre 2"])
        self.track_1 = Track(
            "123",
            "test track",
            self.album_1,
            [self.artist_1],
            240000,
            False,
        )
        self.track_2 = Track(
            "456",
            "test track 2",
        )
        self.listen_1 = Listen(
            self.user,
            self.track_1,
            datetime.strptime("2024-12-26T22:30:04.000000Z", CLIENT_DATETIME_FORMAT),
        )
        self.listen_2 = Listen(
            self.user,
            self.track_2,
            datetime.strptime("2024-12-28T22:30:05.000000Z", CLIENT_DATETIME_FORMAT),
        )
        self.listen_3 = Listen(
            self.user,
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

    def test_full_backfill(self, mock_getpass, mock_input, mock_current_user) -> None:
        # assert json files are read correctly
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

        # assert listen objects are created correctly
        self.assertEqual(len(self.data_loader.listens), 3)
        track_1_unknown = Track(
            self.track_1.id,
            self.track_1.name,
        )
        self.assertListEqual(
            sorted(self.data_loader.listens),
            sorted(
                [
                    Listen(
                        self.user,
                        track_1_unknown,
                        self.listen_1.ts,
                    ),
                    self.listen_2,
                    Listen(
                        self.user,
                        track_1_unknown,
                        self.listen_3.ts,
                    ),
                ]
            ),
        )

        # assert database is updated correctly
        self.data_loader.write_listens()
        all_users = self.db.get_all_users()
        self.assertEqual(len(all_users), 1)
        self.assertEqual(
            list(all_users),
            [self.user],
        )
        all_listens = self.db.get_all_listens()
        self.assertEqual(len(all_listens), 3)
        self.assertEqual(
            sorted(list(all_listens)),
            sorted(
                [
                    self.listen_1,
                    Listen(
                        self.user,
                        Track(
                            self.track_2.id,
                            "",
                        ),
                        self.listen_2.ts,
                    ),
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
