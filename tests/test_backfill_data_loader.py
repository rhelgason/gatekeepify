import os
import unittest
from unittest.mock import patch

from db.constants import DB_DIRECTORY, DB_TEST_NAME
from db.Database import Database
from spotify.backfill_data_loader import BackfillDataLoader, FILE_PREFIX

TEST_DIRECTORY = "tests/test_data"
TEST_FILE_1 = FILE_PREFIX + "_test_file_1.json"
TEST_FILE_2 = FILE_PREFIX + "_test_file_2.json"
TEST_FILE_3 = "test_file_3.json"


@patch("builtins.input", return_value=os.path.join(os.getcwd(), TEST_DIRECTORY))
class TestBackfillDataLoader(unittest.TestCase):
    db: Database
    data_loader: BackfillDataLoader

    def setUp(self) -> None:
        self.db = Database(db_name=DB_TEST_NAME)
        os.mkdir(TEST_DIRECTORY)
        with open(os.path.join(TEST_DIRECTORY, TEST_FILE_1), "w") as f:
            f.write(
                """
                [
                    {
                        "ts": "2024-12-26T22:30:04.214000Z",
                        "ms_played": 51555,
                        "master_metadata_track_name": "test track",
                        "spotify_track_uri": "spotify:track:1234"
                    },
                    {
                        "ts": "2024-12-28T22:30:05.214000Z",
                        "ms_played": 35000,
                        "master_metadata_track_name": "test track 2",
                        "spotify_track_uri": "spotify:track:5678"
                    }
                ]
                """
            )
        with open(os.path.join(TEST_DIRECTORY, TEST_FILE_2), "w") as f:
            f.write(
                """
                [
                    {
                        "ts": "2024-12-12T22:30:04.214000Z",
                        "ms_played": 51555,
                        "master_metadata_track_name": "test track",
                        "spotify_track_uri": "spotify:track:1234"
                    },
                    {
                        "ts": "2024-12-19T22:30:05.214000Z",
                        "ms_played": 3000,
                        "master_metadata_track_name": "test track 2",
                        "spotify_track_uri": "spotify:track:5678"
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
                        "spotify_track_uri": "spotify:track:1234",
                    },
                ]
                """
            )

    def tearDown(self) -> None:
        os.remove(os.path.join(TEST_DIRECTORY, TEST_FILE_1))
        os.remove(os.path.join(TEST_DIRECTORY, TEST_FILE_2))
        os.remove(os.path.join(TEST_DIRECTORY, TEST_FILE_3))
        os.rmdir(TEST_DIRECTORY)

        if self.db.conn:
            self.db.conn.close()
        os.remove(os.path.join(DB_DIRECTORY, DB_TEST_NAME))

    def test_read_json_files(self, mock_input) -> None:
        self.data_loader = BackfillDataLoader(is_test=True)
        self.assertEqual(len(self.data_loader.listens_json), 4)
        self.assertListEqual(
            self.data_loader.listens_json,
            [
                {
                    "ts": "2024-12-12T22:30:04.214000Z",
                    "ms_played": 51555,
                    "master_metadata_track_name": "test track",
                    "spotify_track_uri": "spotify:track:1234",
                },
                {
                    "ts": "2024-12-19T22:30:05.214000Z",
                    "ms_played": 3000,
                    "master_metadata_track_name": "test track 2",
                    "spotify_track_uri": "spotify:track:5678",
                },
                {
                    "ts": "2024-12-26T22:30:04.214000Z",
                    "ms_played": 51555,
                    "master_metadata_track_name": "test track",
                    "spotify_track_uri": "spotify:track:1234",
                },
                {
                    "ts": "2024-12-28T22:30:05.214000Z",
                    "ms_played": 35000,
                    "master_metadata_track_name": "test track 2",
                    "spotify_track_uri": "spotify:track:5678",
                },
            ],
        )
