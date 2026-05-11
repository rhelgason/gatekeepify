from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import (
    Album,
    Artist,
    ArtistGenre,
    JobRun,
    Listen,
    ListenSource,
    Track,
    TrackArtist,
    User,
)
from app.tasks import _poll_single_user, backfill_track_metadata, poll_recent_listens


def _make_test_db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False), engine


def _spotify_listen_item(track_id, played_at):
    return {
        "track": {
            "id": track_id,
            "name": f"Track {track_id}",
            "album": {
                "id": f"album_{track_id}",
                "name": f"Album {track_id}",
                "release_date": "2020-01-01",
            },
            "artists": [
                {"id": f"artist_{track_id}", "name": f"Artist {track_id}", "genres": ["rock"]}
            ],
            "duration_ms": 200000,
            "is_local": False,
        },
        "played_at": played_at,
    }


class TestPollSingleUser:
    def test_polls_and_inserts_listens(self, db):
        user = User(
            user_id="usr_1",
            user_name="Test",
            spotify_refresh_token="fake_refresh",
        )
        db.add(user)
        db.commit()

        mock_service = MagicMock()
        mock_service.refresh_access_token.return_value = {
            "access_token": "fake_access",
            "refresh_token": "fake_refresh",
        }
        mock_service.get_recent_listens.return_value = [
            _spotify_listen_item("t1", "2024-06-15T10:00:00.000000Z"),
            _spotify_listen_item("t2", "2024-06-15T11:00:00.000000Z"),
        ]

        _poll_single_user(db, mock_service, user)

        assert db.query(Listen).count() == 2
        assert db.query(Track).count() == 2
        assert db.query(Album).count() == 2
        assert db.query(Artist).count() == 2

        listens = db.query(Listen).all()
        for listen in listens:
            assert listen.source == ListenSource.api.value
            assert listen.user_id == "usr_1"

        assert user.last_poll_at is not None

        job = db.query(JobRun).filter(JobRun.job_name == "poll_recent_listens").first()
        assert job is not None
        assert job.status == "success"
        assert job.record_count == 2

    def test_passes_last_listen_timestamp_to_spotify(self, db):
        user = User(
            user_id="usr_1",
            user_name="Test",
            spotify_refresh_token="fake_refresh",
        )
        db.add(user)
        db.add(Track(track_id="old_t", track_name="Old Track"))
        existing_ts = datetime(2024, 3, 15, 10, 0, 0)
        db.add(
            Listen(
                ts=existing_ts,
                user_id="usr_1",
                track_id="old_t",
                source=ListenSource.api.value,
            )
        )
        db.commit()

        mock_service = MagicMock()
        mock_service.refresh_access_token.return_value = {
            "access_token": "fake_access",
            "refresh_token": "fake_refresh",
        }
        mock_service.get_recent_listens.return_value = []

        _poll_single_user(db, mock_service, user)

        mock_service.get_recent_listens.assert_called_once_with(
            "fake_access", after=existing_ts
        )

    def test_updates_refresh_token_if_changed(self, db):
        user = User(
            user_id="usr_1",
            user_name="Test",
            spotify_refresh_token="old_refresh",
        )
        db.add(user)
        db.commit()

        mock_service = MagicMock()
        mock_service.refresh_access_token.return_value = {
            "access_token": "fake_access",
            "refresh_token": "new_refresh",
        }
        mock_service.get_recent_listens.return_value = []

        _poll_single_user(db, mock_service, user)

        db.refresh(user)
        assert user.spotify_refresh_token == "new_refresh"

    def test_handles_no_new_listens(self, db):
        user = User(
            user_id="usr_1",
            user_name="Test",
            spotify_refresh_token="fake_refresh",
        )
        db.add(user)
        db.commit()

        mock_service = MagicMock()
        mock_service.refresh_access_token.return_value = {
            "access_token": "fake_access",
            "refresh_token": "fake_refresh",
        }
        mock_service.get_recent_listens.return_value = []

        _poll_single_user(db, mock_service, user)

        assert db.query(Listen).count() == 0
        job = db.query(JobRun).first()
        assert job.status == "success"
        assert job.record_count == 0


class TestPollRecentListensTask:
    @patch("app.tasks.SessionLocal")
    @patch("app.tasks.SpotifyService")
    def test_polls_all_active_users(self, MockSpotifyService, MockSessionLocal):
        Session, engine = _make_test_db()
        db = Session()

        db.add(User(user_id="u1", user_name="User 1", spotify_refresh_token="tok1"))
        db.add(User(user_id="u2", user_name="User 2", spotify_refresh_token="tok2"))
        db.add(User(user_id="u3", user_name="No Token", spotify_refresh_token=None))
        db.commit()

        MockSessionLocal.return_value = db
        mock_service = MagicMock()
        MockSpotifyService.return_value = mock_service
        mock_service.refresh_access_token.return_value = {
            "access_token": "acc",
            "refresh_token": "ref",
        }
        mock_service.get_recent_listens.return_value = [
            _spotify_listen_item("t1", "2024-06-15T10:00:00.000000Z"),
        ]

        poll_recent_listens()

        assert mock_service.get_recent_listens.call_count == 2
        assert db.query(Listen).count() == 2

        db.close()
        Base.metadata.drop_all(bind=engine)

    @patch("app.tasks.SessionLocal")
    @patch("app.tasks.SpotifyService")
    def test_continues_on_user_error(self, MockSpotifyService, MockSessionLocal):
        Session, engine = _make_test_db()
        db = Session()

        db.add(User(user_id="u1", user_name="User 1", spotify_refresh_token="tok1"))
        db.add(User(user_id="u2", user_name="User 2", spotify_refresh_token="tok2"))
        db.commit()

        MockSessionLocal.return_value = db
        mock_service = MagicMock()
        MockSpotifyService.return_value = mock_service

        call_count = [0]

        def side_effect(refresh_token):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Token expired")
            return {"access_token": "acc", "refresh_token": "ref"}

        mock_service.refresh_access_token.side_effect = side_effect
        mock_service.get_recent_listens.return_value = [
            _spotify_listen_item("t1", "2024-06-15T10:00:00.000000Z"),
        ]

        poll_recent_listens()

        assert db.query(Listen).count() == 1

        db.close()
        Base.metadata.drop_all(bind=engine)


class TestBackfillTrackMetadataTask:
    @patch("app.tasks.SessionLocal")
    @patch("app.tasks.SpotifyService")
    def test_backfills_missing_tracks(self, MockSpotifyService, MockSessionLocal):
        Session, engine = _make_test_db()
        db = Session()

        db.add(User(user_id="u1", user_name="User 1", spotify_refresh_token="tok1"))
        db.add(Track(track_id="trk_missing", track_name=None))
        db.add(
            Listen(
                ts=datetime(2024, 1, 1),
                user_id="u1",
                track_id="trk_missing",
                source="export",
            )
        )
        db.commit()

        MockSessionLocal.return_value = db
        mock_service = MagicMock()
        MockSpotifyService.return_value = mock_service
        mock_service.refresh_access_token.return_value = {
            "access_token": "acc",
            "refresh_token": "ref",
        }
        mock_service.get_tracks.return_value = [
            {
                "track": {
                    "id": "trk_missing",
                    "name": "Now Has Name",
                    "album": {"id": "alb1", "name": "Album", "release_date": "2023-06-01"},
                    "artists": [{"id": "art1", "name": "Artist", "genres": ["pop"]}],
                    "duration_ms": 180000,
                    "is_local": False,
                }
            }
        ]

        backfill_track_metadata()

        track = db.query(Track).filter(Track.track_id == "trk_missing").first()
        assert track.track_name == "Now Has Name"
        assert track.duration_ms == 180000

        album = db.query(Album).filter(Album.album_id == "alb1").first()
        assert album is not None
        assert album.release_date is not None

        job = db.query(JobRun).filter(
            JobRun.job_name == "backfill_track_metadata"
        ).first()
        assert job.status == "success"

        db.close()
        Base.metadata.drop_all(bind=engine)

    @patch("app.tasks.SessionLocal")
    @patch("app.tasks.SpotifyService")
    def test_skips_when_no_missing_tracks(self, MockSpotifyService, MockSessionLocal):
        Session, engine = _make_test_db()
        db = Session()

        db.add(User(user_id="u1", user_name="User", spotify_refresh_token="tok"))
        db.add(Track(track_id="trk_1", track_name="Has Name"))
        db.add(
            Listen(
                ts=datetime(2024, 1, 1),
                user_id="u1",
                track_id="trk_1",
                source="api",
            )
        )
        db.commit()

        MockSessionLocal.return_value = db
        mock_service = MagicMock()
        MockSpotifyService.return_value = mock_service

        backfill_track_metadata()

        mock_service.get_tracks.assert_not_called()

        db.close()
        Base.metadata.drop_all(bind=engine)
