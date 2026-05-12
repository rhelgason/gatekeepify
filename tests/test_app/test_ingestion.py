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
    get_active_users,
    get_tracks_missing_metadata,
    parse_release_date,
    retroactively_validate_export_listens,
    upsert_from_recent_listens,
    upsert_track_metadata,
)


def _make_spotify_listen_item(
    track_id="trk_1",
    track_name="Test Track",
    album_id="alb_1",
    album_name="Test Album",
    release_date="2020-06-15",
    duration_ms=240000,
    is_local=False,
    artists=None,
    played_at="2024-06-15T10:30:04.214000Z",
):
    if artists is None:
        artists = [
            {"id": "art_1", "name": "Test Artist", "genres": ["rock", "indie"]}
        ]
    return {
        "track": {
            "id": track_id,
            "name": track_name,
            "album": {
                "id": album_id,
                "name": album_name,
                "release_date": release_date,
            },
            "artists": artists,
            "duration_ms": duration_ms,
            "is_local": is_local,
        },
        "played_at": played_at,
    }


class TestParseReleaseDate:
    def test_full_date(self):
        assert parse_release_date("2020-06-15") == date(2020, 6, 15)

    def test_year_month(self):
        assert parse_release_date("2020-06") == date(2020, 6, 1)

    def test_year_only(self):
        assert parse_release_date("2020") == date(2020, 1, 1)

    def test_none(self):
        assert parse_release_date(None) is None

    def test_empty(self):
        assert parse_release_date("") is None

    def test_invalid(self):
        assert parse_release_date("not-a-date") is None


class TestUpsertFromRecentListens:
    def test_inserts_listen_with_full_data(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.commit()

        items = [_make_spotify_listen_item()]
        count = upsert_from_recent_listens(db, items, "usr_1")

        assert count == 1

        listen = db.query(Listen).first()
        assert listen.user_id == "usr_1"
        assert listen.track_id == "trk_1"
        assert listen.source == ListenSource.api.value

        track = db.query(Track).filter(Track.track_id == "trk_1").first()
        assert track.track_name == "Test Track"
        assert track.duration_ms == 240000

        album = db.query(Album).filter(Album.album_id == "alb_1").first()
        assert album.album_name == "Test Album"
        assert album.release_date == date(2020, 6, 15)

        artist = db.query(Artist).filter(Artist.artist_id == "art_1").first()
        assert artist.artist_name == "Test Artist"

        ta = db.query(TrackArtist).first()
        assert ta.track_id == "trk_1"
        assert ta.artist_id == "art_1"

        genres = db.query(ArtistGenre).filter(ArtistGenre.artist_id == "art_1").all()
        genre_names = sorted([g.genre for g in genres])
        assert genre_names == ["indie", "rock"]

    def test_deduplicates_listens(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.commit()

        items = [_make_spotify_listen_item()]
        upsert_from_recent_listens(db, items, "usr_1")
        count = upsert_from_recent_listens(db, items, "usr_1")

        assert count == 0
        assert db.query(Listen).count() == 1

    def test_multiple_listens_different_tracks(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.commit()

        items = [
            _make_spotify_listen_item(
                track_id="trk_1", played_at="2024-06-15T10:00:00.000000Z"
            ),
            _make_spotify_listen_item(
                track_id="trk_2",
                track_name="Track 2",
                album_id="alb_2",
                album_name="Album 2",
                played_at="2024-06-15T11:00:00.000000Z",
            ),
        ]
        count = upsert_from_recent_listens(db, items, "usr_1")
        assert count == 2
        assert db.query(Listen).count() == 2

    def test_multiple_artists_on_track(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.commit()

        artists = [
            {"id": "art_1", "name": "Artist 1", "genres": ["rock"]},
            {"id": "art_2", "name": "Artist 2", "genres": ["pop"]},
        ]
        items = [_make_spotify_listen_item(artists=artists)]
        upsert_from_recent_listens(db, items, "usr_1")

        track_artists = db.query(TrackArtist).filter(
            TrackArtist.track_id == "trk_1"
        ).all()
        assert len(track_artists) == 2

    def test_skips_item_with_no_track_id(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.commit()

        items = [{"track": {"name": "No ID"}, "played_at": "2024-06-15T10:00:00.000000Z"}]
        count = upsert_from_recent_listens(db, items, "usr_1")
        assert count == 0

    def test_skips_item_with_bad_timestamp(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.commit()

        items = [_make_spotify_listen_item(played_at="not-a-date")]
        count = upsert_from_recent_listens(db, items, "usr_1")
        assert count == 0


class TestUpsertTrackMetadata:
    def test_fills_in_track_metadata(self, db):
        db.add(Track(track_id="trk_1", track_name=None))
        db.commit()

        items = [
            {
                "track": {
                    "id": "trk_1",
                    "name": "Now Named",
                    "album": {
                        "id": "alb_1",
                        "name": "Album",
                        "release_date": "2023-01-01",
                    },
                    "artists": [
                        {"id": "art_1", "name": "Artist", "genres": ["jazz"]}
                    ],
                    "duration_ms": 180000,
                    "is_local": False,
                }
            }
        ]
        count = upsert_track_metadata(db, items)
        assert count == 1

        track = db.query(Track).filter(Track.track_id == "trk_1").first()
        assert track.track_name == "Now Named"
        assert track.duration_ms == 180000
        assert track.album_id == "alb_1"

        album = db.query(Album).first()
        assert album.release_date == date(2023, 1, 1)

    def test_updates_existing_track_name(self, db):
        db.add(Album(album_id="alb_1", album_name="Old Album"))
        db.add(
            Track(
                track_id="trk_1",
                track_name="Old Name",
                album_id="alb_1",
                duration_ms=100000,
            )
        )
        db.commit()

        items = [
            {
                "track": {
                    "id": "trk_1",
                    "name": "New Name",
                    "album": {"id": "alb_1", "name": "New Album", "release_date": "2024-01-01"},
                    "artists": [],
                    "duration_ms": 200000,
                    "is_local": False,
                }
            }
        ]
        upsert_track_metadata(db, items)

        track = db.query(Track).filter(Track.track_id == "trk_1").first()
        assert track.track_name == "New Name"
        assert track.duration_ms == 200000


class TestGetTracksMissingMetadata:
    def test_finds_tracks_with_null_name(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Track(track_id="trk_1", track_name=None))
        db.add(Track(track_id="trk_2", track_name="Has Name"))
        db.add(Listen(ts=datetime(2024, 1, 1), user_id="usr_1", track_id="trk_1", source="api"))
        db.add(Listen(ts=datetime(2024, 1, 2), user_id="usr_1", track_id="trk_1", source="api"))
        db.add(Listen(ts=datetime(2024, 1, 3), user_id="usr_1", track_id="trk_2", source="api"))
        db.commit()

        missing = get_tracks_missing_metadata(db)
        assert missing == {"trk_1"}

    def test_finds_listens_with_no_track_record(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Listen(ts=datetime(2024, 1, 1), user_id="usr_1", track_id="orphan_trk", source="export"))
        db.commit()

        missing = get_tracks_missing_metadata(db)
        assert "orphan_trk" in missing

    def test_orders_by_listen_count(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Track(track_id="trk_a", track_name=None))
        db.add(Track(track_id="trk_b", track_name=None))
        db.add(Listen(ts=datetime(2024, 1, 1), user_id="usr_1", track_id="trk_a", source="api"))
        db.add(Listen(ts=datetime(2024, 1, 2), user_id="usr_1", track_id="trk_b", source="api"))
        db.add(Listen(ts=datetime(2024, 1, 3), user_id="usr_1", track_id="trk_b", source="api"))
        db.add(Listen(ts=datetime(2024, 1, 4), user_id="usr_1", track_id="trk_b", source="api"))
        db.commit()

        missing = get_tracks_missing_metadata(db, limit=1)
        assert missing == {"trk_b"}

    def test_respects_limit(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        for i in range(5):
            db.add(Track(track_id=f"trk_{i}", track_name=None))
            db.add(Listen(ts=datetime(2024, 1, i + 1), user_id="usr_1", track_id=f"trk_{i}", source="api"))
        db.commit()

        missing = get_tracks_missing_metadata(db, limit=3)
        assert len(missing) == 3

    def test_returns_empty_when_all_tracks_have_names(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Track(track_id="trk_1", track_name="Named"))
        db.add(Listen(ts=datetime(2024, 1, 1), user_id="usr_1", track_id="trk_1", source="api"))
        db.commit()

        missing = get_tracks_missing_metadata(db)
        assert len(missing) == 0


class TestRetroactiveValidation:
    def test_removes_export_listen_before_release_date(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Album(album_id="alb_1", album_name="Album", release_date=date(2022, 6, 1)))
        db.add(Track(track_id="trk_1", track_name="Track", album_id="alb_1"))
        db.add(Listen(
            ts=datetime(2020, 1, 1), user_id="usr_1", track_id="trk_1",
            source=ListenSource.export.value,
        ))
        db.commit()

        removed = retroactively_validate_export_listens(db, {"trk_1"})
        assert removed == 1
        assert db.query(Listen).count() == 0

    def test_keeps_export_listen_after_release_date(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Album(album_id="alb_1", album_name="Album", release_date=date(2020, 1, 1)))
        db.add(Track(track_id="trk_1", track_name="Track", album_id="alb_1"))
        db.add(Listen(
            ts=datetime(2022, 6, 1), user_id="usr_1", track_id="trk_1",
            source=ListenSource.export.value,
        ))
        db.commit()

        removed = retroactively_validate_export_listens(db, {"trk_1"})
        assert removed == 0
        assert db.query(Listen).count() == 1

    def test_does_not_remove_api_sourced_listens(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Album(album_id="alb_1", album_name="Album", release_date=date(2022, 6, 1)))
        db.add(Track(track_id="trk_1", track_name="Track", album_id="alb_1"))
        db.add(Listen(
            ts=datetime(2020, 1, 1), user_id="usr_1", track_id="trk_1",
            source=ListenSource.api.value,
        ))
        db.commit()

        removed = retroactively_validate_export_listens(db, {"trk_1"})
        assert removed == 0
        assert db.query(Listen).count() == 1

    def test_skips_tracks_without_release_date(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Album(album_id="alb_1", album_name="Album", release_date=None))
        db.add(Track(track_id="trk_1", track_name="Track", album_id="alb_1"))
        db.add(Listen(
            ts=datetime(2020, 1, 1), user_id="usr_1", track_id="trk_1",
            source=ListenSource.export.value,
        ))
        db.commit()

        removed = retroactively_validate_export_listens(db, {"trk_1"})
        assert removed == 0
        assert db.query(Listen).count() == 1

    def test_handles_empty_track_ids(self, db):
        removed = retroactively_validate_export_listens(db, set())
        assert removed == 0

    def test_removes_only_invalid_from_mixed_batch(self, db):
        db.add(User(user_id="usr_1", user_name="User"))
        db.add(Album(album_id="alb_1", album_name="Album 1", release_date=date(2022, 1, 1)))
        db.add(Album(album_id="alb_2", album_name="Album 2", release_date=date(2020, 1, 1)))
        db.add(Track(track_id="trk_1", track_name="Track 1", album_id="alb_1"))
        db.add(Track(track_id="trk_2", track_name="Track 2", album_id="alb_2"))
        # trk_1 listen is before release (invalid)
        db.add(Listen(
            ts=datetime(2021, 6, 1), user_id="usr_1", track_id="trk_1",
            source=ListenSource.export.value,
        ))
        # trk_2 listen is after release (valid)
        db.add(Listen(
            ts=datetime(2023, 6, 1), user_id="usr_1", track_id="trk_2",
            source=ListenSource.export.value,
        ))
        db.commit()

        removed = retroactively_validate_export_listens(db, {"trk_1", "trk_2"})
        assert removed == 1
        remaining = db.query(Listen).all()
        assert len(remaining) == 1
        assert remaining[0].track_id == "trk_2"


class TestGetActiveUsers:
    def test_returns_users_with_refresh_tokens(self, db):
        db.add(User(user_id="usr_1", user_name="Active", spotify_refresh_token="token_1"))
        db.add(User(user_id="usr_2", user_name="No Token", spotify_refresh_token=None))
        db.add(User(user_id="usr_3", user_name="Empty Token", spotify_refresh_token=""))
        db.add(User(user_id="usr_4", user_name="Also Active", spotify_refresh_token="token_4"))
        db.commit()

        active = get_active_users(db)
        ids = {u.user_id for u in active}
        assert ids == {"usr_1", "usr_4"}
