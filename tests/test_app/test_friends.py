from datetime import datetime, timezone

from jose import jwt

from app.config import settings
from sqlalchemy import update

from app.models import FriendInvite, Friendship, User


def _auth(user_id):
    token = jwt.encode(
        {"sub": user_id, "exp": datetime(2099, 1, 1, tzinfo=timezone.utc)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


class TestCreateInvite:
    def test_creates_invite(self, client, seeded_db, auth_headers):
        resp = client.post("/friends/invite", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "invite_code" in data
        assert len(data["invite_code"]) > 10

    def test_creates_unique_codes(self, client, seeded_db, auth_headers):
        r1 = client.post("/friends/invite", headers=auth_headers)
        r2 = client.post("/friends/invite", headers=auth_headers)
        assert r1.json()["invite_code"] != r2.json()["invite_code"]


class TestAcceptInvite:
    def test_accept_creates_bidirectional_friendship(self, client, seeded_db, auth_headers):
        user2 = User(user_id="user_2", user_name="User Two")
        seeded_db.add(user2)
        seeded_db.commit()

        resp = client.post("/friends/invite", headers=auth_headers)
        code = resp.json()["invite_code"]

        resp = client.post(f"/friends/accept/{code}", headers=_auth("user_2"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["friend"]["user_id"] == "test_user_1"

        f1 = seeded_db.query(Friendship).filter(
            Friendship.user_id_1 == "test_user_1",
            Friendship.user_id_2 == "user_2",
        ).first()
        f2 = seeded_db.query(Friendship).filter(
            Friendship.user_id_1 == "user_2",
            Friendship.user_id_2 == "test_user_1",
        ).first()
        assert f1 is not None
        assert f2 is not None

    def test_cannot_accept_own_invite(self, client, seeded_db, auth_headers):
        resp = client.post("/friends/invite", headers=auth_headers)
        code = resp.json()["invite_code"]

        resp = client.post(f"/friends/accept/{code}", headers=auth_headers)
        assert resp.status_code == 400
        assert "own invite" in resp.json()["detail"]

    def test_cannot_accept_used_invite(self, client, seeded_db, auth_headers):
        seeded_db.add(User(user_id="user_2", user_name="User Two"))
        seeded_db.add(User(user_id="user_3", user_name="User Three"))
        seeded_db.commit()

        resp = client.post("/friends/invite", headers=auth_headers)
        code = resp.json()["invite_code"]

        client.post(f"/friends/accept/{code}", headers=_auth("user_2"))

        resp = client.post(f"/friends/accept/{code}", headers=_auth("user_3"))
        assert resp.status_code == 400
        assert "already used" in resp.json()["detail"].lower()

    def test_cannot_accept_nonexistent_invite(self, client, seeded_db, auth_headers):
        resp = client.post("/friends/accept/fake_code", headers=auth_headers)
        assert resp.status_code == 404

    def test_atomic_claim_prevents_race(self, client, seeded_db, auth_headers):
        """Simulate a race: another user claims the invite between SELECT and UPDATE."""
        seeded_db.add(User(user_id="user_2", user_name="User Two"))
        seeded_db.add(User(user_id="user_3", user_name="User Three"))
        seeded_db.commit()

        resp = client.post("/friends/invite", headers=auth_headers)
        code = resp.json()["invite_code"]

        # Simulate user_3 claiming the invite directly in the DB (as if a
        # concurrent request completed between user_2's SELECT and UPDATE)
        seeded_db.execute(
            update(FriendInvite)
            .where(FriendInvite.invite_code == code)
            .values(
                accepted_by_user_id="user_3",
                accepted_at=datetime.now(timezone.utc),
            )
        )
        seeded_db.commit()

        # user_2's request should fail even though the initial SELECT would
        # have seen accepted_by_user_id as NULL before the concurrent update
        resp = client.post(f"/friends/accept/{code}", headers=_auth("user_2"))
        assert resp.status_code == 400
        assert "already used" in resp.json()["detail"].lower()

        # No friendship should have been created for user_2
        f = seeded_db.query(Friendship).filter(
            Friendship.user_id_1 == "user_2"
        ).first()
        assert f is None

    def test_already_friends(self, client, seeded_db, auth_headers):
        seeded_db.add(User(user_id="user_2", user_name="User Two"))
        now = datetime.now(timezone.utc)
        seeded_db.add(Friendship(user_id_1="test_user_1", user_id_2="user_2", created_at=now))
        seeded_db.add(Friendship(user_id_1="user_2", user_id_2="test_user_1", created_at=now))
        seeded_db.commit()

        resp = client.post("/friends/invite", headers=auth_headers)
        code = resp.json()["invite_code"]

        resp = client.post(f"/friends/accept/{code}", headers=_auth("user_2"))
        assert resp.status_code == 400
        assert "Already friends" in resp.json()["detail"]


class TestListFriends:
    def test_list_friends(self, client, seeded_db, auth_headers):
        seeded_db.add(User(user_id="user_2", user_name="User Two"))
        seeded_db.add(User(user_id="user_3", user_name="User Three"))
        now = datetime.now(timezone.utc)
        seeded_db.add(Friendship(user_id_1="test_user_1", user_id_2="user_2", created_at=now))
        seeded_db.add(Friendship(user_id_1="test_user_1", user_id_2="user_3", created_at=now))
        seeded_db.commit()

        resp = client.get("/friends", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        friend_ids = {f["user_id"] for f in data}
        assert friend_ids == {"user_2", "user_3"}

    def test_list_friends_with_pagination(self, client, seeded_db, auth_headers):
        for i in range(5):
            seeded_db.add(User(user_id=f"friend_{i}", user_name=f"Friend {i}"))
            seeded_db.add(Friendship(
                user_id_1="test_user_1",
                user_id_2=f"friend_{i}",
                created_at=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
            ))
        seeded_db.commit()

        resp = client.get("/friends", params={"limit": 2, "offset": 0}, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

        resp = client.get("/friends", params={"limit": 2, "offset": 2}, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

        resp = client.get("/friends", params={"limit": 2, "offset": 4}, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_friends_empty(self, client, seeded_db, auth_headers):
        resp = client.get("/friends", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []
