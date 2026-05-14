from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import (
    Album,
    Artist,
    ArtistGenre,
    Listen,
    ListenSource,
    Track,
    TrackArtist,
    User,
)

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=TEST_ENGINE, autoflush=False)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture()
def client(db):
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def test_user(db) -> User:
    user = User(
        user_id="test_user_1",
        user_name="Test User",
        email="test@example.com",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def test_user_token(test_user) -> str:
    payload = {
        "sub": test_user.user_id,
        "exp": datetime(2099, 1, 1, tzinfo=timezone.utc),
        "iat": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture()
def auth_headers(test_user_token) -> dict:
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture()
def seeded_db(db, test_user):
    """Seed the DB with albums, tracks, artists, genres, and listens."""
    albums = [
        Album(album_id="album_1", album_name="OK Computer"),
        Album(album_id="album_2", album_name="Kid A"),
    ]
    for a in albums:
        db.add(a)

    artists = [
        Artist(artist_id="artist_1", artist_name="Radiohead"),
        Artist(artist_id="artist_2", artist_name="Thom Yorke"),
    ]
    for a in artists:
        db.add(a)

    genres = [
        ArtistGenre(artist_id="artist_1", genre="alternative rock"),
        ArtistGenre(artist_id="artist_1", genre="art rock"),
        ArtistGenre(artist_id="artist_2", genre="electronic"),
    ]
    for g in genres:
        db.add(g)

    tracks = [
        Track(
            track_id="track_1",
            track_name="Paranoid Android",
            album_id="album_1",
            duration_ms=384000,
            is_local=False,
        ),
        Track(
            track_id="track_2",
            track_name="Everything In Its Right Place",
            album_id="album_2",
            duration_ms=252000,
            is_local=False,
        ),
        Track(
            track_id="track_3",
            track_name="Karma Police",
            album_id="album_1",
            duration_ms=264000,
            is_local=False,
        ),
    ]
    for t in tracks:
        db.add(t)

    track_artists = [
        TrackArtist(track_id="track_1", artist_id="artist_1"),
        TrackArtist(track_id="track_2", artist_id="artist_1"),
        TrackArtist(track_id="track_2", artist_id="artist_2"),
        TrackArtist(track_id="track_3", artist_id="artist_1"),
    ]
    for ta in track_artists:
        db.add(ta)

    listens = [
        Listen(
            ts=datetime(2024, 3, 15, 10, 0, 0),
            user_id="test_user_1",
            track_id="track_1",
            source=ListenSource.api.value,
        ),
        Listen(
            ts=datetime(2024, 3, 15, 11, 0, 0),
            user_id="test_user_1",
            track_id="track_1",
            source=ListenSource.api.value,
        ),
        Listen(
            ts=datetime(2024, 3, 15, 12, 0, 0),
            user_id="test_user_1",
            track_id="track_2",
            source=ListenSource.api.value,
        ),
        Listen(
            ts=datetime(2024, 6, 1, 14, 0, 0),
            user_id="test_user_1",
            track_id="track_1",
            source=ListenSource.api.value,
        ),
        Listen(
            ts=datetime(2024, 6, 1, 15, 0, 0),
            user_id="test_user_1",
            track_id="track_3",
            source=ListenSource.api.value,
        ),
        Listen(
            ts=datetime(2024, 12, 25, 20, 0, 0),
            user_id="test_user_1",
            track_id="track_2",
            source=ListenSource.export.value,
        ),
    ]
    for listen in listens:
        db.add(listen)

    db.commit()
    return db
