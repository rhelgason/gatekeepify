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
from app.schemas import FriendResponse, InviteAcceptResponse, InviteResponse
from app.services.audit import log_action

router = APIRouter(prefix="/friends", tags=["friends"])


def get_friend_ids(db: Session, user_id: str) -> List[str]:
    rows = db.execute(
        select(Friendship.user_id_2).where(Friendship.user_id_1 == user_id)
    ).all()
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
        select(Friendship.user_id_2, User.user_name, Friendship.created_at)
        .join(User, Friendship.user_id_2 == User.user_id)
        .where(Friendship.user_id_1 == user.user_id)
        .order_by(Friendship.created_at.desc())
        .limit(clamped)
        .offset(offset)
    )
    rows = db.execute(stmt).all()
    return [
        FriendResponse(
            user_id=row[0],
            user_name=row[1],
            friends_since=row[2],
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
        db, "friends.invite_created",
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

    invite = (
        db.query(FriendInvite)
        .filter(FriendInvite.invite_code == invite_code)
        .first()
    )
    if not invite:
        log_action(
            db, "friends.invite_accepted",
            user_id=user.user_id,
            entity_type="invite",
            entity_id=invite_code,
            status="error",
            details={"reason": "not_found"},
        )
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.accepted_by_user_id is not None:
        log_action(
            db, "friends.invite_accepted",
            user_id=user.user_id,
            entity_type="invite",
            entity_id=invite_code,
            status="denied",
            details={"reason": "already_used"},
        )
        raise HTTPException(status_code=400, detail="Invite already used")

    if invite.from_user_id == user.user_id:
        log_action(
            db, "friends.invite_accepted",
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
            db, "friends.invite_accepted",
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
            db, "friends.invite_accepted",
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
        db, "friends.invite_accepted",
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
