from Album import Album
from Artist import Artist

class Track:
    id: str
    name: str
    albums: list[Album]
    artists: list[Artist]

    def __init__(self, id, name, album_name, artists) -> None:
        self.id = id
        self.name = name
        self.album_name = album_name
        self.artists = artists
