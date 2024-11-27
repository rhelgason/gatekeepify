class User:
    id: str
    name: str

    def __init__(self, id, name) -> None:
        self.id = id
        self.name = name
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            data['id'],
            data['display_name'],
        )

class Album:
    id: str
    name: str

    def __init__(self, id, name) -> None:
        self.id = id
        self.name = name
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            data['id'],
            data['name'],
        )

class Artist:
    id: str
    name: str

    def __init__(self, id, name) -> None:
        self.id = id
        self.name = name

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['id'],
            data['name'],
        )

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
