import os
import unittest
from datetime import datetime
from unittest.mock import patch

from constants import CLIENT_DATETIME_FORMAT, HOST_CONSTANTS_TEST_PATH
from db.constants import DB_DIRECTORY, DB_TEST_NAME
from db.Database import Database
from prettytable import PrettyTable
from spotify.stat_viewer import StatViewer
from spotify.types import Album, Artist, Listen, Track, User

CLIENT_ID = "test_id"
CLIENT_SECRET = "test_secret"


@patch(
    "spotify_client.SpotifyClient.gen_current_user",
    return_value=User("12345", "test user"),
)
class TestStatViewer(unittest.TestCase):
    path: str

    def setUp(self) -> None:
        # write test constants file
        self.path = ".".join((HOST_CONSTANTS_TEST_PATH, "py"))
        with open(self.path, "w") as f:
            f.write(
                f"""
CLIENT_ID = "{CLIENT_ID}"
CLIENT_SECRET = "{CLIENT_SECRET}"
"""
            )

        # upsert db test data
        db = Database(db_name=DB_TEST_NAME)
        listen_1 = Listen(
            User("12345", "test user"),
            Track(
                "123",
                "test track",
                Album("234", "test album"),
                [Artist("345", "test artist", ["test genre", "test genre 2"]), Artist("678", "test artist 2", ["test genre 2", "test genre 3"])],
                False,
            ),
            datetime.strptime("2024-12-26T22:30:04.214000Z", CLIENT_DATETIME_FORMAT),
        )
        listen_2 = Listen(
            User("12345", "test user 2"),
            Track(
                "456",
                "test track 2",
                Album("567", "test album 2"),
                [Artist("678", "test artist 2", ["test genre 2", "test genre 3"]), Artist("912", "test artist 3952", ["test genre", "test genre 3"])],
                True,
            ),
            datetime.strptime("2024-12-27T16:48:12.712392Z", CLIENT_DATETIME_FORMAT),
        )
        listen_3 = Listen(
            User("12345", "test user"),
            Track(
                "123",
                "test track",
                Album("234", "test album"),
                [Artist("345", "test artist", ["test genre", "test genre 2"]), Artist("678", "test artist 2", ["test genre 2", "test genre 3"])],
                False,
            ),
            datetime.strptime("2024-12-28T22:30:04.214000Z", CLIENT_DATETIME_FORMAT),
        )
        listen_4 = Listen(
            User("12345", "test user"),
            Track(
                "123",
                "test track",
                Album("234", "test album"),
                [Artist("345", "test artist", ["test genre", "test genre 3"]), Artist("678", "test artist 2", ["test genre 2", "test genre 3"])],
                False,
            ),
            datetime.strptime("2024-12-31T22:30:04.214000Z", CLIENT_DATETIME_FORMAT),
        )
        listen_5 = Listen(
            User("6789", "test user 2"),
            Track(
                "456",
                "test track 2",
                Album("567", "test album 2"),
                [Artist("678", "test artist 2",["test genre 2", "test genre 3"] ), Artist("912", "test artist 3952", ["test genre", "test genre 3"])],
                True,
            ),
            datetime.strptime("2024-12-27T16:48:12.712392Z", CLIENT_DATETIME_FORMAT),
        )
        listen_6 = Listen(
            User("6789", "test user 2"),
            Track(
                "456",
                "test track 2",
                Album("567", "test album 2"),
                [Artist("678", "test artist 2", ["test genre 2", "test genre 3"]), Artist("912", "test artist 3952", ["test genre", "test genre 3"])],
                True,
            ),
            datetime.strptime("2024-12-28T16:48:12.712392Z", CLIENT_DATETIME_FORMAT),
        )
        base_upsert_data = [listen_1, listen_2, listen_3, listen_4, listen_5, listen_6]
        db.upsert_cron_backfill(base_upsert_data)

    def test_trim_str(self, mock_current_user) -> None:
        stat_viewer = StatViewer(None, True)
        mock_current_user.assert_called_once()
        self.assertEqual(stat_viewer.trim_str("Test input string"), "Test input string")
        self.assertEqual(
            stat_viewer.trim_str("Test input string that is too long"),
            "Test input string that is t...",
        )

    def test_get_top_tracks_table_all_time(self, mock_current_user) -> None:
        stat_viewer = StatViewer(None, True)
        mock_current_user.assert_called_once()
        top_tracks_table = PrettyTable(["Rank", "Title", "Artists", "Listens"])
        top_tracks_table.add_rows(
            [
                [
                    1,
                    "test track",
                    "test artist, test artist 2",
                    3,
                ],
                [
                    2,
                    "test track 2",
                    "test artist 2, test artist ...",
                    1,
                ],
            ]
        )
        self.assertEqual(
            stat_viewer.get_top_tracks_table().__str__(), top_tracks_table.__str__()
        )

    def test_get_top_tracks_table_with_ds(self, mock_current_user) -> None:
        stat_viewer = StatViewer(datetime.strptime("2024-12-27", "%Y-%m-%d"), True)
        mock_current_user.assert_called_once()
        top_tracks_table = PrettyTable(["Rank", "Title", "Artists", "Listens"])
        top_tracks_table.add_rows(
            [
                [
                    1,
                    "test track",
                    "test artist, test artist 2",
                    2,
                ],
                [
                    2,
                    "test track 2",
                    "test artist 2, test artist ...",
                    1,
                ],
            ]
        )
        self.assertEqual(
            stat_viewer.get_top_tracks_table().__str__(), top_tracks_table.__str__()
        )

    def test_get_top_artists_table_all_time(self, mock_current_user) -> None:
        stat_viewer = StatViewer(None, True)
        mock_current_user.assert_called_once()
        top_artists_table = PrettyTable(["Rank", "Artist", "Listens"])
        top_artists_table.add_rows(
            [
                [
                    1,
                    "test artist 2",
                    4,
                ],
                [
                    2,
                    "test artist",
                    3,
                ],
                [
                    3,
                    "test artist 3952",
                    1,
                ],
            ]
        )
        self.assertEqual(
            stat_viewer.get_top_artists_table().__str__(), top_artists_table.__str__()
        )

    def test_get_top_artists_table_with_ds(self, mock_current_user) -> None:
        stat_viewer = StatViewer(datetime.strptime("2024-12-27", "%Y-%m-%d"), True)
        mock_current_user.assert_called_once()
        top_artists_table = PrettyTable(["Rank", "Artist", "Listens"])
        top_artists_table.add_rows(
            [
                [
                    1,
                    "test artist 2",
                    3,
                ],
                [
                    2,
                    "test artist",
                    2,
                ],
                [
                    3,
                    "test artist 3952",
                    1,
                ],
            ]
        )
        self.assertEqual(
            stat_viewer.get_top_artists_table().__str__(), top_artists_table.__str__()
        )

    def tearDown(self) -> None:
        os.remove(self.path)
        os.remove(os.path.join(DB_DIRECTORY, DB_TEST_NAME))
