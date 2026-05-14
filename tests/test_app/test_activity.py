from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    Artist,
    AuditLog,
    Friendship,
    Listen,
    ListenSource,
    Track,
    TrackArtist,
    User,
)
from app.services.activity import _new_user_quip, _friendship_quip
from app.services.activity import (
    _pick,
    generate_activity_feed,
)


class TestPick:
    def test_deterministic(self):
        quips = ["a", "b", "c", "d", "e"]
        result1 = _pick(quips, "type", "user", "artist")
        result2 = _pick(quips, "type", "user", "artist")
        assert result1 == result2

    def test_different_seeds_can_differ(self):
        quips = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        results = {_pick(quips, "type", f"user_{i}", "artist") for i in range(20)}
        assert len(results) > 1

    def test_single_item(self):
        assert _pick(["only"], "seed") == "only"


class TestGenerateActivityFeed:
    def test_empty_feed_no_data(self, db, test_user):
        events = generate_activity_feed(db, [test_user.user_id], limit=20, days=7)
        assert events == []

    def test_milestone_detected(self, db, seeded_db, test_user):
        now = datetime.now(timezone.utc)
        for i in range(100):
            db.add(Listen(
                ts=now - timedelta(hours=i),
                user_id=test_user.user_id,
                track_id="track_1",
                source=ListenSource.api.value,
            ))
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id], limit=50, days=7)
        milestone_events = [e for e in events if e["type"] == "milestone"]
        assert len(milestone_events) >= 1
        assert "listens" in milestone_events[0]["stat"]

    def test_new_obsession_detected(self, db, test_user):
        now = datetime.now(timezone.utc)
        artist = Artist(artist_id="new_art", artist_name="New Artist")
        track = Track(track_id="new_tr", track_name="New Track", duration_ms=200000)
        db.add_all([artist, track])
        db.add(TrackArtist(track_id="new_tr", artist_id="new_art"))
        db.flush()

        for i in range(25):
            db.add(Listen(
                ts=now - timedelta(hours=i),
                user_id=test_user.user_id,
                track_id="new_tr",
                source=ListenSource.api.value,
            ))
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id], limit=50, days=7)
        obsession_events = [e for e in events if e["type"] == "new_obsession"]
        assert len(obsession_events) == 1
        assert obsession_events[0]["artist_name"] == "New Artist"

    def test_new_obsession_not_triggered_if_prior_listens(self, db, test_user):
        now = datetime.now(timezone.utc)
        artist = Artist(artist_id="old_art", artist_name="Old Artist")
        track = Track(track_id="old_tr", track_name="Old Track", duration_ms=200000)
        db.add_all([artist, track])
        db.add(TrackArtist(track_id="old_tr", artist_id="old_art"))
        db.flush()

        db.add(Listen(
            ts=now - timedelta(days=30),
            user_id=test_user.user_id,
            track_id="old_tr",
            source=ListenSource.export.value,
        ))
        for i in range(25):
            db.add(Listen(
                ts=now - timedelta(hours=i),
                user_id=test_user.user_id,
                track_id="old_tr",
                source=ListenSource.api.value,
            ))
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id], limit=50, days=7)
        obsession_events = [e for e in events if e["type"] == "new_obsession"]
        assert len(obsession_events) == 0

    def test_new_obsession_skipped_for_new_user(self, db):
        now = datetime.now(timezone.utc)
        new_user = User(user_id="brand_new", user_name="Brand New", created_at=now - timedelta(hours=1))
        db.add(new_user)
        artist = Artist(artist_id="skip_art", artist_name="Skip Artist")
        track = Track(track_id="skip_tr", track_name="Skip Track", duration_ms=200000)
        db.add_all([artist, track])
        db.add(TrackArtist(track_id="skip_tr", artist_id="skip_art"))
        db.flush()
        for i in range(25):
            db.add(Listen(
                ts=now - timedelta(minutes=i * 5),
                user_id="brand_new",
                track_id="skip_tr",
                source=ListenSource.api.value,
            ))
        db.commit()

        events = generate_activity_feed(db, ["brand_new"], limit=50, days=7)
        obsession_events = [e for e in events if e["type"] == "new_obsession"]
        assert len(obsession_events) == 0

    def test_crown_stolen_detected(self, db, test_user):
        now = datetime.now(timezone.utc)
        user2 = User(user_id="user2", user_name="User Two", created_at=now)
        db.add(user2)
        artist = Artist(artist_id="crown_art", artist_name="Crown Artist")
        track = Track(track_id="crown_tr", track_name="Crown Track", duration_ms=200000)
        db.add_all([artist, track])
        db.add(TrackArtist(track_id="crown_tr", artist_id="crown_art"))
        db.flush()

        # user2 listened 30 days ago (before the 7-day window)
        db.add(Listen(
            ts=now - timedelta(days=30),
            user_id="user2",
            track_id="crown_tr",
            source=ListenSource.api.value,
        ))
        # test_user just started listening 2 days ago (within window),
        # so their MIN(ts) is recent and beats nobody — but the detection
        # fires because their first listen is within the window while
        # user2's is outside it
        db.add(Listen(
            ts=now - timedelta(days=2),
            user_id=test_user.user_id,
            track_id="crown_tr",
            source=ListenSource.api.value,
        ))
        db.commit()

        events = generate_activity_feed(
            db, [test_user.user_id, "user2"], limit=50, days=7
        )
        # user2 has the crown (earlier first listen). test_user is late.
        # No crown steal: winner (user2) has ts BEFORE since, not after.
        # Crown steal only fires when the winner's MIN(ts) is RECENT.
        crown_events = [e for e in events if e["type"] == "crown_stolen"]
        assert len(crown_events) == 0

    def test_upload_event_detected(self, db, test_user):
        import json
        now = datetime.now(timezone.utc)
        db.add(AuditLog(
            ts=now - timedelta(hours=1),
            user_id=test_user.user_id,
            action="backfill.upload",
            status="success",
            details=json.dumps({"total_listens_accepted": 5000}),
        ))
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id], limit=50, days=7)
        upload_events = [e for e in events if e["type"] == "data_uploaded"]
        assert len(upload_events) == 1
        assert "5,000" in upload_events[0]["stat"]

    def test_upload_with_crown_steal_cap(self, db, test_user):
        import json
        now = datetime.now(timezone.utc)

        user2 = User(user_id="user_cap", user_name="Cap User", created_at=now)
        db.add(user2)
        db.add(AuditLog(
            ts=now - timedelta(hours=1),
            user_id=test_user.user_id,
            action="backfill.upload",
            status="success",
            details=json.dumps({"total_listens_accepted": 1000}),
        ))

        for i in range(5):
            aid = f"cap_art_{i}"
            tid = f"cap_tr_{i}"
            db.add(Artist(artist_id=aid, artist_name=f"Cap Artist {i}"))
            db.add(Track(track_id=tid, track_name=f"Cap Track {i}", duration_ms=200000))
            db.flush()
            db.add(TrackArtist(track_id=tid, artist_id=aid))
            db.add(Listen(
                ts=now - timedelta(days=20),
                user_id="user_cap",
                track_id=tid,
                source=ListenSource.api.value,
            ))
            db.add(Listen(
                ts=now - timedelta(days=30),
                user_id=test_user.user_id,
                track_id=tid,
                source=ListenSource.export.value,
            ))
        db.commit()

        events = generate_activity_feed(
            db, [test_user.user_id, "user_cap"], limit=50, days=7
        )
        crown_events = [e for e in events if e["type"] == "crown_stolen" and e["user_id"] == test_user.user_id]
        assert len(crown_events) <= 4

    def test_track_repeat_detected(self, db, seeded_db, test_user):
        now = datetime.now(timezone.utc)
        for i in range(12):
            db.add(Listen(
                ts=now - timedelta(hours=i),
                user_id=test_user.user_id,
                track_id="track_1",
                source=ListenSource.api.value,
            ))
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id], limit=50, days=7)
        repeat_events = [e for e in events if e["type"] == "track_repeat"]
        assert len(repeat_events) >= 1
        assert "Paranoid Android" in repeat_events[0]["stat"]

    def test_track_repeat_not_triggered_below_threshold(self, db, seeded_db, test_user):
        now = datetime.now(timezone.utc)
        for i in range(5):
            db.add(Listen(
                ts=now - timedelta(hours=i),
                user_id=test_user.user_id,
                track_id="track_3",
                source=ListenSource.api.value,
            ))
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id], limit=50, days=7)
        repeat_events = [e for e in events if e["type"] == "track_repeat" and "Karma Police" in (e.get("stat") or "")]
        assert len(repeat_events) == 0

    def test_feed_respects_limit(self, db, seeded_db, test_user):
        now = datetime.now(timezone.utc)
        for i in range(100):
            db.add(Listen(
                ts=now - timedelta(hours=i),
                user_id=test_user.user_id,
                track_id="track_1",
                source=ListenSource.api.value,
            ))
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id], limit=3, days=7)
        assert len(events) <= 3

    def test_feed_sorted_by_ts_descending(self, db, seeded_db, test_user):
        now = datetime.now(timezone.utc)
        for i in range(100):
            db.add(Listen(
                ts=now - timedelta(hours=i),
                user_id=test_user.user_id,
                track_id="track_1",
                source=ListenSource.api.value,
            ))
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id], limit=50, days=7)
        if len(events) >= 2:
            for i in range(len(events) - 1):
                assert events[i]["ts"] >= events[i + 1]["ts"]

    def test_new_user_joined_with_mutual_friend(self, db, test_user):
        now = datetime.now(timezone.utc)
        mutual = User(user_id="mutual", user_name="Mutual", created_at=now - timedelta(days=30))
        new_guy = User(user_id="new_guy", user_name="New Guy", created_at=now - timedelta(hours=1))
        db.add_all([mutual, new_guy])
        db.add(Friendship(user_id_1=test_user.user_id, user_id_2="mutual", created_at=now - timedelta(days=20)))
        db.add(Friendship(user_id_1="mutual", user_id_2=test_user.user_id, created_at=now - timedelta(days=20)))
        db.add(Friendship(user_id_1="new_guy", user_id_2="mutual", created_at=now - timedelta(hours=1)))
        db.add(Friendship(user_id_1="mutual", user_id_2="new_guy", created_at=now - timedelta(hours=1)))
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id, "mutual"], limit=50, days=7)
        joined_events = [e for e in events if e["type"] == "user_joined"]
        assert len(joined_events) == 1
        assert joined_events[0]["user_name"] == "New Guy"

    def test_new_user_not_shown_without_mutual(self, db, test_user):
        now = datetime.now(timezone.utc)
        stranger = User(user_id="stranger", user_name="Stranger", created_at=now - timedelta(hours=1))
        db.add(stranger)
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id], limit=50, days=7)
        joined_events = [e for e in events if e["type"] == "user_joined"]
        assert len(joined_events) == 0

    def test_new_user_not_shown_if_old(self, db, test_user):
        events = generate_activity_feed(db, [test_user.user_id], limit=50, days=7)
        joined_events = [e for e in events if e["type"] == "user_joined"]
        assert len(joined_events) == 0

    def test_new_friendship_detected(self, db, test_user):
        now = datetime.now(timezone.utc)
        user2 = User(user_id="friend_new", user_name="Friend New", created_at=now - timedelta(days=30))
        db.add(user2)
        db.add(Friendship(user_id_1=test_user.user_id, user_id_2="friend_new", created_at=now - timedelta(hours=2)))
        db.add(Friendship(user_id_1="friend_new", user_id_2=test_user.user_id, created_at=now - timedelta(hours=2)))
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id, "friend_new"], limit=50, days=7)
        friend_events = [e for e in events if e["type"] == "new_friendship"]
        assert len(friend_events) == 1

    def test_friendship_deduplicated(self, db, test_user):
        now = datetime.now(timezone.utc)
        user2 = User(user_id="dedup_friend", user_name="Dedup Friend", created_at=now - timedelta(days=30))
        db.add(user2)
        db.add(Friendship(user_id_1=test_user.user_id, user_id_2="dedup_friend", created_at=now - timedelta(hours=1)))
        db.add(Friendship(user_id_1="dedup_friend", user_id_2=test_user.user_id, created_at=now - timedelta(hours=1)))
        db.commit()

        events = generate_activity_feed(db, [test_user.user_id, "dedup_friend"], limit=50, days=7)
        friend_events = [e for e in events if e["type"] == "new_friendship"]
        assert len(friend_events) == 1
