import unittest

from spotify.types import Album, Artist, User


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
        }
        artist = Artist.from_dict(data)
        self.assertEqual(artist.id, "123")
        self.assertEqual(artist.name, "test")
        self.assertEqual(hash(artist), hash("123"))
        self.assertEqual(artist, Artist("123", "test"))
        self.assertNotEqual(artist, Artist("1234", "test"))
        self.assertNotEqual(artist, Artist("123", "test2"))
        self.assertEqual(artist.to_json_str(), '{"id": "123", "name": "test"}')

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
