import os
import pathlib as pl
import unittest

from constants import HOST_CONSTANTS_TEST_PATH
from getpass import getpass
from SpotifyClient import SpotifyClient
from unittest.mock import patch

CLIENT_ID = "test_id"
CLIENT_SECRET = "test_secret"

@patch("builtins.input", side_effect=[CLIENT_ID, CLIENT_SECRET])
class TestSpotifyClient(unittest.TestCase):
    def setUp(self) -> None:
        self.path = ".".join((HOST_CONSTANTS_TEST_PATH, "py"))

    def test_get_host_client(self, mock_input) -> None:
        # delete test constants, if exists
        try:
            os.remove(self.path)
        except OSError:
            pass
        self.assertEqual(pl.Path(self.path).resolve().is_file(), False)
        
        SpotifyClient(is_test=True)
        self.assertEqual(mock_input.call_count, 2)
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

    def tearDown(self) -> None:
        os.remove(self.path)
