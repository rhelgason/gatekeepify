import json
from typing import Any, Dict, List


class Artifact:
    id: str
    name: str

    def __init__(self, id, name) -> None:
        self.id = id
        self.name = name

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["id"],
            data["name"],
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        return self.id == other.id and self.name == other.name

    def __lt__(self, other):
        return self.id < other.id

    def _to_json(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
        }

    def to_json_str(self) -> str:
        return json.dumps(self._to_json())


class Album(Artifact):
    pass


class Artist(Artifact):
    pass


class User(Artifact):
    @classmethod
    def from_dict(cls, data):
        return cls(
            data["id"],
            data["display_name"],
        )


class Track(Artifact):
    album: Album
    artists: List[Artist]

    def __init__(self, id, name, album, artists) -> None:
        self.id = id
        self.name = name
        self.album = album
        self.artists = artists

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["id"],
            data["name"],
            Album.from_dict(data["album"]),
            [Artist.from_dict(artist) for artist in data["artists"]],
        )
    
    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        return self.id == other.id and self.name == other.name and self.album == other.album and sorted(self.artists) == sorted(other.artists)

    def _to_json(self) -> Dict[str, Any]:
        json = super()._to_json()
        json["album"] = self.album._to_json()
        json["artists"] = [artist._to_json() for artist in self.artists]
        return json
