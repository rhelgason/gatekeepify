import json
from datetime import datetime
from typing import Any, Dict, List

from constants import CLIENT_DATETIME_FORMAT
from db.constants import DB_DATETIME_FORMAT


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


class User(Artifact):
    @classmethod
    def from_dict(cls, data):
        return cls(
            data["id"],
            data["display_name"],
        )


class Artist(Artifact):
    genres: List[str]

    def __init__(self, id, name, genres) -> None:
        self.id = id
        self.name = name
        if genres == [None]:
            self.genres = []
        else:
            self.genres = genres

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["id"],
            data["name"],
            data["genres"],
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        return (
            self.id == other.id
            and self.name == other.name
            and sorted(self.genres) == sorted(other.genres)
        )

    def _to_json(self) -> Dict[str, Any]:
        json = super()._to_json()
        json["genres"] = self.genres
        return json


class Track(Artifact):
    album: Album
    artists: List[Artist]
    duration_ms: int
    is_local: bool

    def __init__(self, id, name, album, artists, duration_ms, is_local) -> None:
        self.id = id
        self.name = name
        self.album = album
        self.artists = artists
        self.duration_ms = duration_ms
        self.is_local = bool(is_local)

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["id"],
            data["name"],
            Album.from_dict(data["album"]),
            [Artist.from_dict(artist) for artist in data["artists"]],
            data["duration_ms"],
            data["is_local"],
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        return (
            self.id == other.id
            and self.name == other.name
            and self.album == other.album
            and sorted(self.artists) == sorted(other.artists)
            and self.duration_ms == other.duration_ms
            and self.is_local == other.is_local
        )

    def _to_json(self) -> Dict[str, Any]:
        json = super()._to_json()
        json["album"] = self.album._to_json()
        json["artists"] = [artist._to_json() for artist in self.artists]
        json["duration_ms"] = self.duration_ms
        json["is_local"] = self.is_local
        return json


class Listen:
    track: Track
    ts: datetime
    user: User

    def __init__(self, user, track, ts) -> None:
        self.user = user
        self.track = track
        self.ts = ts

    @classmethod
    def from_dict(cls, data, user: User):
        return cls(
            user,
            Track.from_dict(data["track"]),
            datetime.strptime(data["played_at"], CLIENT_DATETIME_FORMAT),
        )

    # TODO: support user field to make hashes unique across users
    def __hash__(self) -> int:
        return hash(self.user) ^ hash(self.track) ^ hash(self.ts)

    def __eq__(self, other) -> bool:
        return (
            self.user == other.user
            and self.track == other.track
            and self.ts == other.ts
        )

    def __lt__(self, other):
        if self.ts == other.ts:
            return self.user < other.user
        return self.ts < other.ts

    def _to_json(self) -> Dict[str, Any]:
        return {
            "track": self.track._to_json(),
            "ts": self.ts.strftime(DB_DATETIME_FORMAT),
            "user": self.user._to_json(),
        }

    def to_json_str(self) -> str:
        return json.dumps(self._to_json())
