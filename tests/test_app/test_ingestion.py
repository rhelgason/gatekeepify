from datetime import datetime

import pytest

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
from app.services.ingestion import get_tracks_missing_metadata


class TestGetTracksMissingMetadata:
    def test_finds_tracks_with_null_duration(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Track(track_id="trk_1", track_name="No Duration", duration_ms=None))
        db.add(Track(track_id="trk_2", track_name="Has Duration", duration_ms=200000, album_id="alb_1"))
        db.add(Album(album_id="alb_1", album_name="Album"))
        db.add(Listen(ts=datetime(2024, 1, 1), user_id="usr_1", track_id="trk_1", source="api"))
        db.add(Listen(ts=datetime(2024, 1, 2), user_id="usr_1", track_id="trk_1", source="api"))
        db.add(Listen(ts=datetime(2024, 1, 3), user_id="usr_1", track_id="trk_2", source="api"))
        db.commit()

        missing = get_tracks_missing_metadata(db)
        assert "trk_1" in missing
        assert "trk_2" not in missing

    def test_finds_tracks_with_null_album(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Track(track_id="trk_1", track_name="No Album", duration_ms=200000, album_id=None))
        db.add(Listen(ts=datetime(2024, 1, 1), user_id="usr_1", track_id="trk_1", source="api"))
        db.commit()

        missing = get_tracks_missing_metadata(db)
        assert "trk_1" in missing

    def test_orders_by_listen_count(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Track(track_id="trk_a", track_name="A", duration_ms=None))
        db.add(Track(track_id="trk_b", track_name="B", duration_ms=None))
        db.add(Listen(ts=datetime(2024, 1, 1), user_id="usr_1", track_id="trk_a", source="api"))
        db.add(Listen(ts=datetime(2024, 1, 2), user_id="usr_1", track_id="trk_b", source="api"))
        db.add(Listen(ts=datetime(2024, 1, 3), user_id="usr_1", track_id="trk_b", source="api"))
        db.add(Listen(ts=datetime(2024, 1, 4), user_id="usr_1", track_id="trk_b", source="api"))
        db.commit()

        missing = list(get_tracks_missing_metadata(db, limit=1))
        assert missing == ["trk_b"]

    def test_respects_limit(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        for i in range(5):
            db.add(Track(track_id=f"trk_{i}", track_name=f"Track {i}", duration_ms=None))
            db.add(Listen(ts=datetime(2024, 1, i + 1), user_id="usr_1", track_id=f"trk_{i}", source="api"))
        db.commit()

        missing = get_tracks_missing_metadata(db, limit=3)
        assert len(missing) == 3

    def test_empty_when_all_enriched(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Album(album_id="alb_1", album_name="Album"))
        db.add(Track(track_id="trk_1", track_name="Full", duration_ms=200000, album_id="alb_1"))
        db.add(Listen(ts=datetime(2024, 1, 1), user_id="usr_1", track_id="trk_1", source="api"))
        db.commit()

        missing = get_tracks_missing_metadata(db)
        assert len(missing) == 0
