import os
import pathlib as pl
import unittest

from constants import HOST_CONSTANTS_TEST_PATH
from SpotifyClient import SpotifyClient
from unittest.mock import patch


class TestSpotifyClient(unittest.TestCase):
    @patch("builtins.input")
    def test_get_host_client(self, mock_input) -> None:
        # delete test constants, if exists
        path = ".".join((HOST_CONSTANTS_TEST_PATH, "py"))
        try:
            os.remove(path)
        except OSError:
            pass
        self.assertEqual(pl.Path(path).resolve().is_file(), False)

        # mock fake client id and secret
        client_id = "test_id"
        client_secret = "test_secret"
        mock_input.side_effect = [client_id, client_secret]
        SpotifyClient(is_test=True)

        self.assertEqual(pl.Path(path).resolve().is_file(), True)
        host_constants_spec = __import__(
            HOST_CONSTANTS_TEST_PATH.split("/")[-1].removesuffix(".py"),
            globals(),
            locals(),
            ["CLIENT_ID", "CLIENT_SECRET"],
            0,
        )
        self.assertEqual(host_constants_spec.CLIENT_ID, client_id)
        self.assertEqual(host_constants_spec.CLIENT_SECRET, client_secret)
        os.remove(path)
