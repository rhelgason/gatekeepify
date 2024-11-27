from spotify.Album import Album
from spotify.Artist import Artist

class Track:
    id: str
    name: str
    album: Album
    artists: list[Artist]

    def __init__(self, id, name, album_name, artists) -> None:
        self.id = id
        self.name = name
        self.album_name = album_name
        self.artists = artists
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            data['id'],
            data['name'],
            Album.from_dict(data['album']),
            [Artist.from_dict(artist) for artist in data['artists']]
        )
