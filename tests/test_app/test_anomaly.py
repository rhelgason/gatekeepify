from datetime import datetime, timedelta

from app.models import Listen, ListenSource, Track, User
from app.services.anomaly import analyze_user_export


class TestAnomalyDetection:
    def test_clean_export_scores_100(self, db):
        db.add(User(user_id="clean", user_name="Clean"))
        db.add(Track(track_id="t1", track_name="Track"))
        # Normal export listens spread across days
        for i in range(10):
            db.add(Listen(
                ts=datetime(2024, 1, i + 1, 10, 0),
                user_id="clean", track_id="t1",
                source=ListenSource.export.value,
            ))
        db.commit()

        result = analyze_user_export(db, "clean")
        assert result["score"] == 100
        assert result["flags"] == []
        assert result["export_count"] == 10

    def test_no_export_scores_100(self, db):
        db.add(User(user_id="api_only", user_name="API Only"))
        db.add(Track(track_id="t1", track_name="Track"))
        db.add(Listen(
            ts=datetime(2024, 1, 1, 10, 0),
            user_id="api_only", track_id="t1",
            source=ListenSource.api.value,
        ))
        db.commit()

        result = analyze_user_export(db, "api_only")
        assert result["score"] == 100
        assert result["export_count"] == 0

    def test_rapid_fire_detection(self, db):
        db.add(User(user_id="rapid", user_name="Rapid"))
        db.add(Track(track_id="t1", track_name="Track"))
        base = datetime(2024, 1, 1, 10, 0)
        for i in range(30):
            db.add(Listen(
                ts=base + timedelta(seconds=i * 10),
                user_id="rapid", track_id="t1",
                source=ListenSource.export.value,
            ))
        db.commit()

        result = analyze_user_export(db, "rapid")
        flag_types = [f["type"] for f in result["flags"]]
        assert "rapid_fire" in flag_types
        assert result["score"] < 100

    def test_even_spacing_detection(self, db):
        db.add(User(user_id="bot", user_name="Bot"))
        db.add(Track(track_id="t1", track_name="Track"))
        base = datetime(2024, 1, 1, 10, 0)
        for i in range(50):
            db.add(Listen(
                ts=base + timedelta(seconds=i * 180),
                user_id="bot", track_id="t1",
                source=ListenSource.export.value,
            ))
        db.commit()

        result = analyze_user_export(db, "bot")
        flag_types = [f["type"] for f in result["flags"]]
        assert "even_spacing" in flag_types

    def test_single_day_dump_detection(self, db):
        db.add(User(user_id="dumper", user_name="Dumper"))
        db.add(Track(track_id="t1", track_name="Track"))
        base = datetime(2024, 1, 1, 0, 0)
        for i in range(250):
            db.add(Listen(
                ts=base + timedelta(minutes=i * 5),
                user_id="dumper", track_id="t1",
                source=ListenSource.export.value,
            ))
        db.commit()

        result = analyze_user_export(db, "dumper")
        flag_types = [f["type"] for f in result["flags"]]
        assert "single_day_dump" in flag_types

    def test_backdated_cluster_detection(self, db):
        db.add(User(user_id="faker", user_name="Faker"))
        for i in range(60):
            db.add(Track(track_id=f"fake_t{i}", track_name=f"Fake Track {i}"))
            db.add(Listen(
                ts=datetime(2024, 1, 1, 10, i),
                user_id="faker", track_id=f"fake_t{i}",
                source=ListenSource.export.value,
            ))
        db.commit()

        result = analyze_user_export(db, "faker")
        flag_types = [f["type"] for f in result["flags"]]
        assert "backdated_cluster" in flag_types

    def test_score_decreases_with_severity(self, db):
        db.add(User(user_id="suspect", user_name="Suspect"))
        db.add(Track(track_id="t1", track_name="Track"))
        base = datetime(2024, 1, 1, 10, 0)
        # Rapid fire + even spacing = high severity
        for i in range(50):
            db.add(Listen(
                ts=base + timedelta(seconds=i * 10),
                user_id="suspect", track_id="t1",
                source=ListenSource.export.value,
            ))
        db.commit()

        result = analyze_user_export(db, "suspect")
        assert result["score"] < 75
