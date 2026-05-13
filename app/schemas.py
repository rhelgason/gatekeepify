import enum
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str


class TimePeriod(str, enum.Enum):
    today = "today"
    month = "month"
    year = "year"
    all = "all"


class AlbumResponse(BaseModel):
    album_id: str
    album_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ArtistResponse(BaseModel):
    artist_id: str
    artist_name: Optional[str] = None
    genres: List[str] = []

    model_config = {"from_attributes": True}


class TrackResponse(BaseModel):
    track_id: str
    track_name: Optional[str] = None
    album: Optional[AlbumResponse] = None
    duration_ms: Optional[int] = None
    is_local: Optional[bool] = None

    model_config = {"from_attributes": True}


class TopTrackEntry(BaseModel):
    rank: int
    track_id: str
    track_name: Optional[str] = None
    album_name: Optional[str] = None
    listen_count: int
    total_minutes: int


class TopArtistEntry(BaseModel):
    rank: int
    artist_id: str
    artist_name: Optional[str] = None
    genres: List[str] = []
    listen_count: int
    total_minutes: int


class TopGenreEntry(BaseModel):
    rank: int
    genre: str
    listen_count: int
    total_minutes: int


class StatsResponse(BaseModel):
    items: list
    period: str
    total_listens: int
    total_minutes: int


class WrappedResponse(BaseModel):
    top_artists: List[TopArtistEntry]
    top_tracks: List[TopTrackEntry]
    top_genre: Optional[str] = None
    total_minutes: int
    year: Optional[int] = None


class UserResponse(BaseModel):
    user_id: str
    user_name: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AuthUrlResponse(BaseModel):
    auth_url: str


class BackfillUploadResponse(BaseModel):
    total_listens_processed: int
    total_listens_accepted: int
    total_listens_rejected: int
    rejection_reasons: dict


class BackfillStatusResponse(BaseModel):
    tracks_missing_metadata: int
    total_listens: int
    total_tracks: int


# --- Social / Friends ---


class FriendResponse(BaseModel):
    user_id: str
    user_name: Optional[str] = None
    friends_since: datetime


class InviteResponse(BaseModel):
    invite_code: str


class InviteAcceptResponse(BaseModel):
    friend: FriendResponse


# --- Gatekeeping ---


class GatekeepEntry(BaseModel):
    user_id: str
    user_name: Optional[str] = None
    first_listen: datetime
    first_listen_source: str
    total_listens: int
    verified_listens: int
    total_minutes: int
    is_winner: bool


class GatekeepArtistResponse(BaseModel):
    artist_id: str
    artist_name: Optional[str] = None
    entries: List[GatekeepEntry]


class GatekeepTrackResponse(BaseModel):
    track_id: str
    track_name: Optional[str] = None
    entries: List[GatekeepEntry]


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    user_name: Optional[str] = None
    crown_count: int


class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
    total_artists_contested: int


# --- Search ---


class ArtistSearchResult(BaseModel):
    artist_id: str
    artist_name: Optional[str] = None
    genres: List[str] = []
    image_url: Optional[str] = None
    your_listen_count: int


class TrackSearchResult(BaseModel):
    track_id: str
    track_name: Optional[str] = None
    album_name: Optional[str] = None
    image_url: Optional[str] = None
    artist_names: List[str] = []
    your_listen_count: int


class ArtistDetailResponse(BaseModel):
    artist_id: str
    artist_name: Optional[str] = None
    image_url: Optional[str] = None
    genres: List[str] = []
    total_listens: int
    total_minutes: int
    first_listen: Optional[datetime] = None


class TrackDetailResponse(BaseModel):
    track_id: str
    track_name: Optional[str] = None
    album_name: Optional[str] = None
    image_url: Optional[str] = None
    artist_names: List[str] = []
    duration_ms: Optional[int] = None
    total_listens: int
    total_minutes: int
    first_listen: Optional[datetime] = None


class ChallengeResponse(BaseModel):
    challenge_text: str
    invite_code: str
    artist_id: str
    artist_name: Optional[str] = None
    your_first_listen: datetime
    your_total_listens: int
