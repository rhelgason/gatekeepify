from datetime import date, datetime

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
from app.services.ingestion import (
    get_tracks_missing_metadata,
    retroactively_validate_export_listens,
)


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


class TestRetroactiveValidation:
    def _seed(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Album(album_id="alb_1", album_name="Album", release_date=date(2020, 1, 1)))
        db.add(Album(album_id="alb_2", album_name="Album 2", release_date=date(2018, 6, 1)))
        db.add(Track(track_id="trk_1", track_name="T1", album_id="alb_1", duration_ms=200000))
        db.add(Track(track_id="trk_2", track_name="T2", album_id="alb_2", duration_ms=200000))
        # Backdated export listens (before release) — should be removed.
        db.add(Listen(ts=datetime(2019, 5, 1), user_id="usr_1", track_id="trk_1", source="export"))
        db.add(Listen(ts=datetime(2017, 1, 1), user_id="usr_1", track_id="trk_2", source="export"))
        # Valid export listen (after release) — should stay.
        db.add(Listen(ts=datetime(2021, 1, 1), user_id="usr_1", track_id="trk_1", source="export"))
        # Backdated but API-sourced — must NOT be touched (only export is validated).
        db.add(Listen(ts=datetime(2019, 1, 1), user_id="usr_1", track_id="trk_1", source="api"))
        db.commit()

    def test_removes_only_backdated_export_listens(self, db):
        self._seed(db)
        removed = retroactively_validate_export_listens(db, {"trk_1", "trk_2"})
        assert removed == 2
        remaining = {(r.track_id, r.source) for r in db.query(Listen).all()}
        assert ("trk_1", "export") in remaining  # the valid 2021 export listen
        assert ("trk_1", "api") in remaining  # API listen untouched
        assert ("trk_2", "export") not in remaining  # removed

    def test_no_track_ids_is_noop(self, db):
        self._seed(db)
        assert retroactively_validate_export_listens(db, set()) == 0

    def test_no_release_dates_is_noop(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Album(album_id="alb_x", album_name="No Date", release_date=None))
        db.add(Track(track_id="trk_x", track_name="X", album_id="alb_x", duration_ms=1000))
        db.add(Listen(ts=datetime(2000, 1, 1), user_id="usr_1", track_id="trk_x", source="export"))
        db.commit()
        assert retroactively_validate_export_listens(db, {"trk_x"}) == 0
        assert db.query(Listen).count() == 1
