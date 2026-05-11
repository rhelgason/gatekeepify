from datetime import date, datetime

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


class TestAlbumModel:
    def test_create_album(self, db):
        album = Album(album_id="abc123", album_name="Test Album")
        db.add(album)
        db.commit()

        result = db.query(Album).filter(Album.album_id == "abc123").first()
        assert result is not None
        assert result.album_name == "Test Album"
        assert result.release_date is None

    def test_album_with_release_date(self, db):
        album = Album(
            album_id="abc456",
            album_name="Dated Album",
            release_date=date(2020, 6, 15),
        )
        db.add(album)
        db.commit()

        result = db.query(Album).filter(Album.album_id == "abc456").first()
        assert result.release_date == date(2020, 6, 15)

    def test_upsert_album(self, db):
        db.add(Album(album_id="abc123", album_name="Original"))
        db.commit()

        db.merge(Album(album_id="abc123", album_name="Updated"))
        db.commit()

        result = db.query(Album).filter(Album.album_id == "abc123").first()
        assert result.album_name == "Updated"
        assert db.query(Album).count() == 1


class TestTrackModel:
    def test_create_track_with_album(self, db):
        db.add(Album(album_id="alb1", album_name="Test Album"))
        db.commit()

        track = Track(
            track_id="trk1",
            track_name="Test Track",
            album_id="alb1",
            duration_ms=240000,
            is_local=False,
        )
        db.add(track)
        db.commit()

        result = db.query(Track).filter(Track.track_id == "trk1").first()
        assert result.track_name == "Test Track"
        assert result.album_id == "alb1"
        assert result.duration_ms == 240000
        assert result.is_local is False
        assert result.album.album_name == "Test Album"

    def test_track_nullable_fields(self, db):
        track = Track(track_id="trk_null", track_name=None)
        db.add(track)
        db.commit()

        result = db.query(Track).filter(Track.track_id == "trk_null").first()
        assert result.track_name is None
        assert result.album_id is None
        assert result.duration_ms is None


class TestArtistModel:
    def test_create_artist_with_genres(self, db):
        artist = Artist(artist_id="art1", artist_name="Test Artist")
        db.add(artist)
        db.add(ArtistGenre(artist_id="art1", genre="rock"))
        db.add(ArtistGenre(artist_id="art1", genre="indie"))
        db.commit()

        result = db.query(Artist).filter(Artist.artist_id == "art1").first()
        assert result.artist_name == "Test Artist"
        genre_names = [g.genre for g in result.genres]
        assert sorted(genre_names) == ["indie", "rock"]


class TestTrackArtistModel:
    def test_many_to_many(self, db):
        db.add(Album(album_id="alb1", album_name="Album"))
        db.add(Track(track_id="trk1", track_name="Track", album_id="alb1"))
        db.add(Artist(artist_id="art1", artist_name="Artist 1"))
        db.add(Artist(artist_id="art2", artist_name="Artist 2"))
        db.add(TrackArtist(track_id="trk1", artist_id="art1"))
        db.add(TrackArtist(track_id="trk1", artist_id="art2"))
        db.commit()

        track = db.query(Track).filter(Track.track_id == "trk1").first()
        assert len(track.artists) == 2
        artist_names = sorted([a.artist_name for a in track.artists])
        assert artist_names == ["Artist 1", "Artist 2"]


class TestUserModel:
    def test_create_user(self, db):
        user = User(
            user_id="usr1",
            user_name="Test User",
            email="test@test.com",
            spotify_refresh_token="encrypted_token_here",
            created_at=datetime(2024, 1, 1),
        )
        db.add(user)
        db.commit()

        result = db.query(User).filter(User.user_id == "usr1").first()
        assert result.user_name == "Test User"
        assert result.email == "test@test.com"
        assert result.spotify_refresh_token == "encrypted_token_here"
        assert result.last_poll_at is None


class TestListenModel:
    def test_create_listen_with_source(self, db):
        db.add(User(user_id="usr1", user_name="User"))
        db.add(Track(track_id="trk1", track_name="Track"))
        db.commit()

        listen = Listen(
            ts=datetime(2024, 3, 15, 10, 30, 0),
            user_id="usr1",
            track_id="trk1",
            source=ListenSource.api.value,
        )
        db.add(listen)
        db.commit()

        result = (
            db.query(Listen)
            .filter(Listen.user_id == "usr1", Listen.track_id == "trk1")
            .first()
        )
        assert result.source == "api"
        assert result.export_metadata is None

    def test_export_listen_with_metadata(self, db):
        db.add(User(user_id="usr1", user_name="User"))
        db.add(Track(track_id="trk1", track_name="Track"))
        db.commit()

        import json

        meta = json.dumps({"platform": "iOS", "shuffle": True})
        listen = Listen(
            ts=datetime(2024, 3, 15, 10, 30, 0),
            user_id="usr1",
            track_id="trk1",
            source=ListenSource.export.value,
            export_metadata=meta,
        )
        db.add(listen)
        db.commit()

        result = db.query(Listen).filter(Listen.user_id == "usr1").first()
        assert result.source == "export"
        parsed = json.loads(result.export_metadata)
        assert parsed["platform"] == "iOS"

    def test_composite_primary_key_prevents_duplicates(self, db):
        db.add(User(user_id="usr1", user_name="User"))
        db.add(Track(track_id="trk1", track_name="Track"))
        db.commit()

        ts = datetime(2024, 3, 15, 10, 30, 0)
        db.add(Listen(ts=ts, user_id="usr1", track_id="trk1", source="api"))
        db.commit()

        db.merge(Listen(ts=ts, user_id="usr1", track_id="trk1", source="api"))
        db.commit()
        count = db.query(Listen).filter(Listen.user_id == "usr1").count()
        assert count == 1


class TestJobRunModel:
    def test_create_job_run(self, db):
        db.add(User(user_id="usr1", user_name="User"))
        db.commit()

        job = JobRun(
            job_name="poll_recent_listens",
            user_id="usr1",
            started_at=datetime(2024, 3, 15, 10, 0, 0),
            completed_at=datetime(2024, 3, 15, 10, 0, 5),
            status="success",
            record_count=42,
        )
        db.add(job)
        db.commit()

        result = db.query(JobRun).first()
        assert result.job_name == "poll_recent_listens"
        assert result.record_count == 42
        assert result.id is not None
