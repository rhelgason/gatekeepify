from datetime import datetime, timezone

from jose import jwt

from app.config import settings
from app.models import FriendInvite, Friendship, User


def _make_token(user_id):
    return jwt.encode(
        {"sub": user_id, "exp": datetime(2099, 1, 1, tzinfo=timezone.utc)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


class TestCreateInvite:
    def test_creates_invite(self, client, seeded_db, test_user_token):
        resp = client.post("/friends/invite", params={"token": test_user_token})
        assert resp.status_code == 200
        data = resp.json()
        assert "invite_code" in data
        assert len(data["invite_code"]) > 10

    def test_creates_unique_codes(self, client, seeded_db, test_user_token):
        r1 = client.post("/friends/invite", params={"token": test_user_token})
        r2 = client.post("/friends/invite", params={"token": test_user_token})
        assert r1.json()["invite_code"] != r2.json()["invite_code"]


class TestAcceptInvite:
    def test_accept_creates_bidirectional_friendship(self, client, seeded_db, test_user_token):
        user2 = User(user_id="user_2", user_name="User Two")
        seeded_db.add(user2)
        seeded_db.commit()
        token2 = _make_token("user_2")

        resp = client.post("/friends/invite", params={"token": test_user_token})
        code = resp.json()["invite_code"]

        resp = client.post(f"/friends/accept/{code}", params={"token": token2})
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

    def test_cannot_accept_own_invite(self, client, seeded_db, test_user_token):
        resp = client.post("/friends/invite", params={"token": test_user_token})
        code = resp.json()["invite_code"]

        resp = client.post(f"/friends/accept/{code}", params={"token": test_user_token})
        assert resp.status_code == 400
        assert "own invite" in resp.json()["detail"]

    def test_cannot_accept_used_invite(self, client, seeded_db, test_user_token):
        seeded_db.add(User(user_id="user_2", user_name="User Two"))
        seeded_db.add(User(user_id="user_3", user_name="User Three"))
        seeded_db.commit()

        resp = client.post("/friends/invite", params={"token": test_user_token})
        code = resp.json()["invite_code"]

        client.post(f"/friends/accept/{code}", params={"token": _make_token("user_2")})

        resp = client.post(f"/friends/accept/{code}", params={"token": _make_token("user_3")})
        assert resp.status_code == 400
        assert "already used" in resp.json()["detail"].lower()

    def test_cannot_accept_nonexistent_invite(self, client, seeded_db, test_user_token):
        resp = client.post("/friends/accept/fake_code", params={"token": test_user_token})
        assert resp.status_code == 404

    def test_already_friends(self, client, seeded_db, test_user_token):
        seeded_db.add(User(user_id="user_2", user_name="User Two"))
        now = datetime.now(timezone.utc)
        seeded_db.add(Friendship(user_id_1="test_user_1", user_id_2="user_2", created_at=now))
        seeded_db.add(Friendship(user_id_1="user_2", user_id_2="test_user_1", created_at=now))
        seeded_db.commit()

        resp = client.post("/friends/invite", params={"token": test_user_token})
        code = resp.json()["invite_code"]

        resp = client.post(f"/friends/accept/{code}", params={"token": _make_token("user_2")})
        assert resp.status_code == 400
        assert "Already friends" in resp.json()["detail"]


class TestListFriends:
    def test_list_friends(self, client, seeded_db, test_user_token):
        seeded_db.add(User(user_id="user_2", user_name="User Two"))
        seeded_db.add(User(user_id="user_3", user_name="User Three"))
        now = datetime.now(timezone.utc)
        seeded_db.add(Friendship(user_id_1="test_user_1", user_id_2="user_2", created_at=now))
        seeded_db.add(Friendship(user_id_1="test_user_1", user_id_2="user_3", created_at=now))
        seeded_db.commit()

        resp = client.get("/friends", params={"token": test_user_token})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        friend_ids = {f["user_id"] for f in data}
        assert friend_ids == {"user_2", "user_3"}

    def test_list_friends_empty(self, client, seeded_db, test_user_token):
        resp = client.get("/friends", params={"token": test_user_token})
        assert resp.status_code == 200
        assert resp.json() == []
