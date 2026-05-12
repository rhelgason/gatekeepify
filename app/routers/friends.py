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

router = APIRouter(prefix="/friends", tags=["friends"])


def get_friend_ids(db: Session, user_id: str) -> List[str]:
    rows = db.execute(
        select(Friendship.user_id_2).where(Friendship.user_id_1 == user_id)
    ).all()
    return [row[0] for row in rows]


@router.get("", response_model=List[FriendResponse])
def list_friends(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Friendship.user_id_2, User.user_name, Friendship.created_at)
        .join(User, Friendship.user_id_2 == User.user_id)
        .where(Friendship.user_id_1 == user.user_id)
        .order_by(Friendship.created_at.desc())
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
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.accepted_by_user_id is not None:
        raise HTTPException(status_code=400, detail="Invite already used")

    if invite.from_user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Cannot accept your own invite")

    existing = db.execute(
        select(Friendship).where(
            Friendship.user_id_1 == user.user_id,
            Friendship.user_id_2 == invite.from_user_id,
        )
    ).first()
    if existing:
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
        raise HTTPException(status_code=400, detail="Invite already used")

    db.add(Friendship(user_id_1=user.user_id, user_id_2=invite.from_user_id, created_at=now))
    db.add(Friendship(user_id_1=invite.from_user_id, user_id_2=user.user_id, created_at=now))
    db.commit()

    sender = db.query(User).filter(User.user_id == invite.from_user_id).first()
    return InviteAcceptResponse(
        friend=FriendResponse(
            user_id=sender.user_id,
            user_name=sender.user_name,
            friends_since=now,
        )
    )
