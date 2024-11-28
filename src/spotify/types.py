class Artifact:
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
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        return self.id == other.id and self.name == other.name

class User(Artifact):
    @classmethod
    def from_dict(cls, data):
        return cls(
            data['id'],
            data['display_name'],
        )

class Album(Artifact):
    pass

class Artist(Artifact):
    pass

class Track(Artifact):
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
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other) and self.album == other.album and set(self.artists) == set(other.artists)
