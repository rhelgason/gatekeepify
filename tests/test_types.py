import unittest
from datetime import datetime

from constants import CLIENT_DATETIME_FORMAT
from spotify.types import Album, Artist, Listen, Track, User


class TestSpotifyTypes(unittest.TestCase):
    def test_album(self) -> None:
        data = {
            "id": "123",
            "name": "test",
        }
        album = Album.from_dict(data)

        self.assertEqual(album.id, "123")
        self.assertEqual(album.name, "test")
        self.assertEqual(hash(album), hash("123"))

        self.assertEqual(album, Album("123", "test"))
        self.assertNotEqual(album, Album("1234", "test"))
        self.assertNotEqual(album, Album("123", "test2"))

        self.assertEqual(album.to_json_str(), '{"id": "123", "name": "test"}')

    def test_artist(self) -> None:
        data = {
            "id": "123",
            "name": "test",
            "genres": ["genre1", "genre2"],
        }
        artist = Artist.from_dict(data)

        self.assertEqual(artist.id, "123")
        self.assertEqual(artist.name, "test")
        self.assertEqual(artist.genres, ["genre1", "genre2"])
        self.assertEqual(hash(artist), hash("123"))

        self.assertEqual(artist, Artist("123", "test", ["genre2", "genre1"]))
        self.assertNotEqual(artist, Artist("1234", "test", ["genre1", "genre2"]))
        self.assertNotEqual(artist, Artist("123", "test2", ["genre1", "genre2"]))
        self.assertNotEqual(artist, Artist("123", "test", ["genre2", "genre3"]))

        self.assertEqual(
            artist.to_json_str(),
            '{"id": "123", "name": "test", "genres": ["genre1", "genre2"]}',
        )

    def test_user(self) -> None:
        data = {
            "id": "123",
            "display_name": "test",
        }
        user = User.from_dict(data)

        self.assertEqual(user.id, "123")
        self.assertEqual(user.name, "test")
        self.assertEqual(hash(user), hash("123"))

        self.assertEqual(user, User("123", "test"))
        self.assertNotEqual(user, User("1234", "test"))
        self.assertNotEqual(user, User("123", "test2"))

        self.assertEqual(user.to_json_str(), '{"id": "123", "name": "test"}')

    def test_track(self) -> None:
        test_album = Album("456", "test_album")
        test_artist_1 = Artist("789", "test_artist", ["test_genre"])
        test_artist_2 = Artist("234", "test_artist_2", ["test_genre", "test_genre_2"])
        data = {
            "id": "123",
            "name": "test",
            "album": test_album._to_json(),
            "artists": [test_artist_1._to_json(), test_artist_2._to_json()],
            "is_local": False,
        }
        track = Track.from_dict(data)

        self.assertEqual(track.id, "123")
        self.assertEqual(track.name, "test")
        self.assertEqual(hash(track), hash("123"))
        self.assertEqual(track.album, test_album)
        self.assertEqual(track.artists, [test_artist_1, test_artist_2])
        self.assertEqual(track.is_local, False)

        ## tracks should be equal despite order of artists
        self.assertEqual(
            track,
            Track("123", "test", test_album, [test_artist_1, test_artist_2], False),
        )
        self.assertEqual(
            track,
            Track("123", "test", test_album, [test_artist_2, test_artist_1], False),
        )

        self.assertNotEqual(
            track,
            Track("1234", "test", test_album, [test_artist_1, test_artist_2], False),
        )
        self.assertNotEqual(
            track,
            Track("123", "test2", test_album, [test_artist_1, test_artist_2], False),
        )
        self.assertNotEqual(
            track,
            Track(
                "123",
                "test",
                Album("567", "test_album"),
                [test_artist_1, test_artist_2],
                False,
            ),
        )
        self.assertNotEqual(
            track, Track("123", "test", test_album, [test_artist_1], False)
        )
        self.assertNotEqual(
            track,
            Track("123", "test2", test_album, [test_artist_1, test_artist_2], True),
        )
        self.assertNotEqual(
            track,
            Track(
                "123",
                "test2",
                test_album,
                [Artist("789", "test_artist", ["test_genre_2"]), test_artist_2],
                True,
            ),
        )

        self.assertEqual(
            track.to_json_str(),
            '{"id": "123", "name": "test", "album": {"id": "456", '
            '"name": "test_album"}, "artists": [{"id": "789", '
            '"name": "test_artist", "genres": ["test_genre"]}, '
            '{"id": "234", "name": "test_artist_2", "genres": '
            '["test_genre", "test_genre_2"]}], "is_local": false}',
        )

    def test_listen(self) -> None:
        test_user = User("12345", "test user")
        test_track = Track(
            "123",
            "test track",
            Album("234", "test album"),
            [
                Artist("345", "test artist", ["test genre"]),
                Artist("678", "test artist 2", ["test genre 2"]),
            ],
            False,
        )
        data = {
            "track": test_track._to_json(),
            "played_at": "2024-12-27T22:30:04.214000Z",
            "user": test_user._to_json(),
        }
        listen = Listen.from_dict(data, test_user)

        self.assertEqual(listen.track, test_track)
        self.assertEqual(listen.user, test_user)
        self.assertEqual(
            listen.ts,
            datetime.strptime("2024-12-27T22:30:04.214000Z", CLIENT_DATETIME_FORMAT),
        )

        self.assertEqual(
            listen,
            Listen(
                test_user,
                test_track,
                datetime.strptime(
                    "2024-12-27T22:30:04.214000Z", CLIENT_DATETIME_FORMAT
                ),
            ),
        )

        self.assertNotEqual(
            listen,
            Listen(
                User("6789", "test user 2"),
                test_track,
                datetime.strptime(
                    "2024-12-27T22:30:04.214000Z", CLIENT_DATETIME_FORMAT
                ),
            ),
        )
        self.assertNotEqual(
            listen,
            Listen(
                test_user,
                Track(
                    "123",
                    "test track",
                    Album("234", "test album"),
                    [
                        Artist("345", "test artist", ["test genre"]),
                        Artist("678", "test artist 3", ["test genre 2"]),
                    ],
                    False,
                ),
                datetime.strptime(
                    "2024-12-27T22:30:04.214000Z", CLIENT_DATETIME_FORMAT
                ),
            ),
        )
        self.assertNotEqual(
            listen,
            Listen(
                test_user,
                Track(
                    "123",
                    "test track",
                    Album("234", "test album"),
                    [
                        Artist("345", "test artist", ["test genre 2"]),
                        Artist("678", "test artist 2", ["test genre 2"]),
                    ],
                    False,
                ),
                datetime.strptime(
                    "2024-12-27T22:30:04.214000Z", CLIENT_DATETIME_FORMAT
                ),
            ),
        )
        self.assertNotEqual(
            listen,
            Listen(
                test_user,
                test_track,
                datetime.strptime(
                    "2024-11-28T16:33:29.214000Z", CLIENT_DATETIME_FORMAT
                ),
            ),
        )

        self.assertEqual(
            listen.to_json_str(),
            '{"track": {"id": "123", "name": "test track", "album": {"id": "234", '
            '"name": "test album"}, "artists": [{"id": "345", "name": "test artist", '
            '"genres": ["test genre"]}, {"id": "678", "name": "test artist 2", '
            '"genres": ["test genre 2"]}], "is_local": false}, "ts": "2024-12-27 '
            '22:30:04.214000", "user": {"id": "12345", "name": "test user"}}',
        )
