import os
import pathlib as pl
import unittest
from datetime import datetime
from unittest.mock import patch

from constants import CLIENT_DATETIME_FORMAT, HOST_CONSTANTS_TEST_PATH
from spotify.types import Album, Artist, Track, User
from spotify_client import SpotifyClient

CLIENT_ID = "test_id"
CLIENT_SECRET = "test_secret"


@patch("builtins.input", side_effect=[CLIENT_ID])
@patch("getpass.getpass", return_value=CLIENT_SECRET)
class TestSpotifyClient(unittest.TestCase):
    path: str

    def setUp(self) -> None:
        self.path = ".".join((HOST_CONSTANTS_TEST_PATH, "py"))

        # delete test constants, if exists
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_get_host_client(self, mock_getpass, mock_input) -> None:
        self.assertEqual(pl.Path(self.path).resolve().is_file(), False)
        SpotifyClient(is_test=True)
        mock_input.assert_called_once()
        mock_getpass.assert_called_once()
        self.assertEqual(pl.Path(self.path).resolve().is_file(), True)
        host_constants_spec = __import__(
            HOST_CONSTANTS_TEST_PATH.split("/")[-1].removesuffix(".py"),
            globals(),
            locals(),
            ["CLIENT_ID", "CLIENT_SECRET"],
            0,
        )
        self.assertEqual(host_constants_spec.CLIENT_ID, CLIENT_ID)
        self.assertEqual(host_constants_spec.CLIENT_SECRET, CLIENT_SECRET)

    @patch("spotipy.Spotify.current_user_recently_played")
    def test_gen_most_recent_listens(
        self, mock_recently_played, mock_getpass, mock_input
    ) -> None:
        played_at_1 = "2024-12-27T22:30:04.214000Z"
        played_at_2 = "2024-12-26T16:48:12.712392Z"
        played_at_datetime_1 = datetime.strptime(played_at_1, CLIENT_DATETIME_FORMAT)
        played_at_datetime_2 = datetime.strptime(played_at_2, CLIENT_DATETIME_FORMAT)
        user_1 = User("12345", "test user")
        mock_recently_played.return_value = {
            "items": [
                {
                    "track": {
                        "id": "123",
                        "name": "test track name",
                        "album": {
                            "id": "234",
                            "name": "test album name",
                        },
                        "artists": [
                            {
                                "id": "345",
                                "name": "test artist name",
                            },
                            {
                                "id": "678",
                                "name": "test artist name 2",
                            },
                        ],
                        "is_local": False,
                    },
                    "played_at": played_at_1,
                },
                {
                    "track": {
                        "id": "456",
                        "name": "test track name 2",
                        "album": {
                            "id": "567",
                            "name": "test album name 2",
                        },
                        "artists": [
                            {
                                "id": "678",
                                "name": "test artist name 2",
                            },
                            {
                                "id": "912",
                                "name": "test artist name 3",
                            },
                        ],
                        "is_local": True,
                    },
                    "played_at": played_at_2,
                },
            ]
        }

        client = SpotifyClient(is_test=True)
        mock_input.assert_called_once()
        mock_getpass.assert_called_once()
        recent_listens = client.gen_most_recent_listens(user_1)
        sorted_listens = sorted(recent_listens)

        self.assertEqual(len(recent_listens), 2)
        self.assertEqual(
            [listen.ts for listen in sorted_listens],
            [played_at_datetime_2, played_at_datetime_1],
        )
        self.assertEqual(
            sorted_listens[0].track,
            Track(
                "456",
                "test track name 2",
                Album("567", "test album name 2"),
                [
                    Artist("678", "test artist name 2"),
                    Artist("912", "test artist name 3"),
                ],
                True,
            ),
        )
        self.assertEqual(
            sorted_listens[1].track,
            Track(
                "123",
                "test track name",
                Album("234", "test album name"),
                [
                    Artist("345", "test artist name"),
                    Artist("678", "test artist name 2"),
                ],
                False,
            ),
        )

    def tearDown(self) -> None:
        os.remove(self.path)
