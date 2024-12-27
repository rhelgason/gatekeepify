import os
import pathlib as pl
import unittest

from constants import HOST_CONSTANTS_TEST_PATH
from getpass import getpass
from SpotifyClient import SpotifyClient
from unittest.mock import patch

CLIENT_ID = "test_id"
CLIENT_SECRET = "test_secret"

class TestSpotifyClient(unittest.TestCase):
    @patch("builtins.input", side_effect=[CLIENT_ID, CLIENT_SECRET])
    def test_get_host_client(self, mock_input) -> None:
        # delete test constants, if exists
        path = ".".join((HOST_CONSTANTS_TEST_PATH, "py"))
        try:
            os.remove(path)
        except OSError:
            pass
        self.assertEqual(pl.Path(path).resolve().is_file(), False)
        
        SpotifyClient(is_test=True)
        self.assertEqual(mock_input.call_count, 2)
        self.assertEqual(pl.Path(path).resolve().is_file(), True)
        host_constants_spec = __import__(
            HOST_CONSTANTS_TEST_PATH.split("/")[-1].removesuffix(".py"),
            globals(),
            locals(),
            ["CLIENT_ID", "CLIENT_SECRET"],
            0,
        )
        self.assertEqual(host_constants_spec.CLIENT_ID, CLIENT_ID)
        self.assertEqual(host_constants_spec.CLIENT_SECRET, CLIENT_SECRET)
        os.remove(path)
