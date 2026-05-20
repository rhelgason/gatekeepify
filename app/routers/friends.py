import secrets
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FriendInvite, Friendship, User
from app.models import User as UserModel
from app.routers.auth import get_current_user
from sqlalchemy import func

from app.schemas import FriendResponse, InviteAcceptResponse, InviteResponse
from app.services.audit import log_action

router = APIRouter(prefix="/friends", tags=["friends"])


def _escape_like(q: str) -> str:
    return q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_friend_ids(db: Session, user_id: str) -> List[str]:
    rows = db.execute(select(Friendship.user_id_2).where(Friendship.user_id_1 == user_id)).all()
    return [row[0] for row in rows]


MAX_LIMIT = 100


@router.get("", response_model=List[FriendResponse])
def list_friends(
    user: UserModel = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    clamped = max(1, min(limit, MAX_LIMIT))
    stmt = (
        select(Friendship.user_id_2, User.user_name, User.image_url, Friendship.created_at)
        .join(User, Friendship.user_id_2 == User.user_id)
        .where(Friendship.user_id_1 == user.user_id)
        .order_by(Friendship.created_at.desc())
        .limit(clamped)
        .offset(offset)
    )
    rows = db.execute(stmt).all()
    log_action(db, "friends.list_viewed", user_id=user.user_id, details={"count": len(rows)})
    return [
        FriendResponse(
            user_id=row[0],
            user_name=row[1],
            image_url=row[2],
            friends_since=row[3],
        )
        for row in rows
    ]


@router.post("/invite", response_model=InviteResponse)
def create_invite(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    code = secrets.token_urlsafe(16)
    invite = FriendInvite(
        from_user_id=user.user_id,
        invite_code=code,
        created_at=datetime.now(timezone.utc),
    )
    db.add(invite)
    db.commit()

    log_action(
        db,
        "friends.invite_created",
        user_id=user.user_id,
        entity_type="invite",
        entity_id=code,
    )
    return InviteResponse(invite_code=code)


@router.post("/accept/{invite_code}", response_model=InviteAcceptResponse)
def accept_invite(
    invite_code: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invite = db.query(FriendInvite).filter(FriendInvite.invite_code == invite_code).first()
    if not invite:
        log_action(
            db,
            "friends.invite_accepted",
            user_id=user.user_id,
            entity_type="invite",
            entity_id=invite_code,
            status="error",
            details={"reason": "not_found"},
        )
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.accepted_by_user_id is not None:
        log_action(
            db,
            "friends.invite_accepted",
            user_id=user.user_id,
            entity_type="invite",
            entity_id=invite_code,
            status="denied",
            details={"reason": "already_used"},
        )
        raise HTTPException(status_code=400, detail="Invite already used")

    if invite.from_user_id == user.user_id:
        log_action(
            db,
            "friends.invite_accepted",
            user_id=user.user_id,
            entity_type="invite",
            entity_id=invite_code,
            status="denied",
            details={"reason": "self_accept"},
        )
        raise HTTPException(status_code=400, detail="Cannot accept your own invite")

    existing = db.execute(
        select(Friendship).where(
            Friendship.user_id_1 == user.user_id,
            Friendship.user_id_2 == invite.from_user_id,
        )
    ).first()
    if existing:
        log_action(
            db,
            "friends.invite_accepted",
            user_id=user.user_id,
            entity_type="invite",
            entity_id=invite_code,
            status="denied",
            details={"reason": "already_friends", "friend_id": invite.from_user_id},
        )
        raise HTTPException(status_code=400, detail="Already friends")

    now = datetime.now(timezone.utc)

    result = db.execute(
        update(FriendInvite)
        .where(
            FriendInvite.id == invite.id,
            FriendInvite.accepted_by_user_id.is_(None),
        )
        .values(accepted_by_user_id=user.user_id, accepted_at=now)
    )
    if result.rowcount == 0:
        log_action(
            db,
            "friends.invite_accepted",
            user_id=user.user_id,
            entity_type="invite",
            entity_id=invite_code,
            status="denied",
            details={"reason": "race_condition"},
        )
        raise HTTPException(status_code=400, detail="Invite already used")

    db.add(Friendship(user_id_1=user.user_id, user_id_2=invite.from_user_id, created_at=now))
    db.add(Friendship(user_id_1=invite.from_user_id, user_id_2=user.user_id, created_at=now))
    db.commit()

    log_action(
        db,
        "friends.invite_accepted",
        user_id=user.user_id,
        entity_type="invite",
        entity_id=invite_code,
        details={"friend_id": invite.from_user_id},
    )

    sender = db.query(User).filter(User.user_id == invite.from_user_id).first()
    if not sender:
        raise HTTPException(status_code=500, detail="Invite sender no longer exists")
    return InviteAcceptResponse(
        friend=FriendResponse(
            user_id=sender.user_id,
            user_name=sender.user_name,
            friends_since=now,
        )
    )


@router.get("/search-users")
def search_users(
    q: str = Query(..., min_length=1),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_friend_ids = set(get_friend_ids(db, user.user_id))
    words = q.strip().split()
    word_filters = [User.user_name.ilike(f"%{_escape_like(w)}%") for w in words]

    users = db.execute(
        select(User.user_id, User.user_name, User.image_url)
        .where(
            *word_filters,
            User.user_id != user.user_id,
        )
        .limit(10)
    ).all()

    log_action(db, "friends.search_users", user_id=user.user_id, details={"query": q, "results": len(users)})
    return [
        {
            "user_id": u.user_id,
            "user_name": u.user_name,
            "is_friend": u.user_id in existing_friend_ids,
        }
        for u in users
    ]


@router.post("/request")
def send_friend_request(
    to_user_id: str = Query(...),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if to_user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Cannot send request to yourself")

    target = db.query(User).filter(User.user_id == to_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.execute(
        select(Friendship).where(
            Friendship.user_id_1 == user.user_id,
            Friendship.user_id_2 == to_user_id,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already friends")

    pending = db.execute(
        select(FriendInvite).where(
            FriendInvite.from_user_id == user.user_id,
            FriendInvite.to_user_id == to_user_id,
            FriendInvite.accepted_by_user_id.is_(None),
        )
    ).first()
    if pending:
        raise HTTPException(status_code=400, detail="Request already sent")

    code = secrets.token_urlsafe(16)
    db.add(
        FriendInvite(
            from_user_id=user.user_id,
            to_user_id=to_user_id,
            invite_code=code,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    log_action(db, "friends.request_sent", user_id=user.user_id, entity_type="user", entity_id=to_user_id)

    return {"status": "sent", "to_user_id": to_user_id}


@router.get("/requests")
def get_pending_requests(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    incoming = db.execute(
        select(FriendInvite.id, FriendInvite.from_user_id, User.user_name, FriendInvite.created_at)
        .join(User, FriendInvite.from_user_id == User.user_id)
        .where(
            FriendInvite.to_user_id == user.user_id,
            FriendInvite.accepted_by_user_id.is_(None),
        )
        .order_by(FriendInvite.created_at.desc())
    ).all()

    log_action(db, "friends.requests_viewed", user_id=user.user_id, details={"pending_count": len(incoming)})
    return [
        {
            "id": r.id,
            "from_user_id": r.from_user_id,
            "from_user_name": r.user_name,
            "created_at": r.created_at,
        }
        for r in incoming
    ]


@router.post("/requests/{request_id}/accept")
def accept_friend_request(
    request_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invite = (
        db.query(FriendInvite)
        .filter(
            FriendInvite.id == request_id,
            FriendInvite.to_user_id == user.user_id,
            FriendInvite.accepted_by_user_id.is_(None),
        )
        .first()
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Request not found")

    existing = db.execute(
        select(Friendship).where(
            Friendship.user_id_1 == user.user_id,
            Friendship.user_id_2 == invite.from_user_id,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already friends")

    now = datetime.now(timezone.utc)
    invite.accepted_by_user_id = user.user_id
    invite.accepted_at = now
    db.add(Friendship(user_id_1=user.user_id, user_id_2=invite.from_user_id, created_at=now))
    db.add(Friendship(user_id_1=invite.from_user_id, user_id_2=user.user_id, created_at=now))
    db.commit()

    log_action(db, "friends.request_accepted", user_id=user.user_id, entity_type="user", entity_id=invite.from_user_id)

    return {"status": "accepted", "friend_id": invite.from_user_id}


@router.post("/requests/{request_id}/decline")
def decline_friend_request(
    request_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invite = (
        db.query(FriendInvite)
        .filter(
            FriendInvite.id == request_id,
            FriendInvite.to_user_id == user.user_id,
            FriendInvite.accepted_by_user_id.is_(None),
        )
        .first()
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Request not found")

    db.delete(invite)
    db.commit()

    log_action(db, "friends.request_declined", user_id=user.user_id, entity_type="user", entity_id=invite.from_user_id)

    return {"status": "declined"}


@router.get("/compatibility/{friend_id}")
def get_compatibility(
    friend_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend_ids = get_friend_ids(db, user.user_id)
    if friend_id not in friend_ids:
        raise HTTPException(status_code=403, detail="Not friends with this user")

    from app.services.compatibility import compute_compatibility

    result = compute_compatibility(db, user.user_id, friend_id)

    log_action(
        db,
        "friends.compatibility_viewed",
        user_id=user.user_id,
        entity_type="user",
        entity_id=friend_id,
        details={"score": result["score"]},
    )

    return result
