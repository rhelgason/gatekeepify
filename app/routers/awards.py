from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AwardSnapshot, User
from app.models import User as UserModel
from app.routers.auth import get_current_user
from app.routers.friends import get_friend_ids
from app.schemas import (
    AwardEntry,
    AwardLeaderboardEntry,
    HeadToHeadComparison,
    HeadToHeadResponse,
    TrophyCaseResponse,
)
from app.services.audit import log_action
from app.services.awards import (
    ALL_COMPUTE_FUNCTIONS,
    AWARD_DEFINITIONS,
    get_friend_group_hash,
)

router = APIRouter(prefix="/gatekeep/awards", tags=["awards"])

ON_THE_FLY_AWARDS = {"crown", "trendsetter", "obsessive", "basic"}
CACHED_AWARDS = {"archaeologist", "patient_zero", "completionist", "genre_snob", "time_traveler", "streak", "hypebeast"}


def _compute_on_the_fly(db: Session, group_ids: list) -> dict:
    results = {}
    for award_id in ON_THE_FLY_AWARDS:
        fn = ALL_COMPUTE_FUNCTIONS.get(award_id)
        if fn:
            results[award_id] = fn(db, group_ids)
    return results


def _get_cached(db: Session, group_hash: str) -> dict:
    rows = db.execute(
        select(AwardSnapshot).where(AwardSnapshot.friend_group_hash == group_hash)
    ).scalars().all()

    results: dict = {}
    for row in rows:
        if row.award_id not in results:
            results[row.award_id] = []
        results[row.award_id].append({
            "user_id": row.user_id,
            "rank": row.rank,
            "stat_value": row.stat_value,
            "stat_detail": row.stat_detail,
            "entity_id": row.entity_id,
            "entity_name": row.entity_name,
        })

    for award_id in results:
        results[award_id].sort(key=lambda r: r["rank"])

    return results


@router.get("/trophies", response_model=TrophyCaseResponse)
def get_trophies(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend_ids = get_friend_ids(db, user.user_id)
    group_ids = list(dict.fromkeys([user.user_id] + friend_ids))
    group_hash = get_friend_group_hash(group_ids)

    live = _compute_on_the_fly(db, group_ids)
    cached = _get_cached(db, group_hash)
    all_awards = {**cached, **live}

    user_names = {
        u.user_id: u.user_name
        for u in db.query(User).filter(User.user_id.in_(group_ids)).all()
    }

    user_awards = []
    leaderboards = {}
    best_title = None

    for award_id, defn in AWARD_DEFINITIONS.items():
        entries = all_awards.get(award_id, [])
        leaderboards[award_id] = [
            AwardLeaderboardEntry(
                user_id=e["user_id"],
                user_name=user_names.get(e["user_id"]),
                rank=e["rank"],
                stat_value=e.get("stat_value"),
                stat_detail=e.get("stat_detail"),
            )
            for e in entries[:5]
        ]

        user_entry = next((e for e in entries if e["user_id"] == user.user_id), None)
        held = user_entry is not None and user_entry["rank"] == 1
        user_awards.append(
            AwardEntry(
                award_id=award_id,
                award_name=defn["name"],
                description=defn["description"],
                rank=user_entry["rank"] if user_entry else 0,
                stat_value=user_entry.get("stat_value") if user_entry else None,
                stat_detail=user_entry.get("stat_detail") if user_entry else None,
                entity_id=user_entry.get("entity_id") if user_entry else None,
                entity_name=user_entry.get("entity_name") if user_entry else None,
                extra={k: v for k, v in user_entry.items() if k in ("infections_detail", "current_streak")} if user_entry else None,
                held=held,
                tier=defn["tier"],
            )
        )

        if held and (best_title is None or award_id != "trendsetter"):
            best_title = {"award_id": award_id, "display": defn["name"]}

    log_action(db, "awards.trophies_viewed", user_id=user.user_id)

    return TrophyCaseResponse(
        user_awards=user_awards,
        leaderboards={k: [e.model_dump() for e in v] for k, v in leaderboards.items()},
        title=best_title,
    )


@router.get("/head-to-head", response_model=HeadToHeadResponse)
def head_to_head(
    friend_id: str = Query(...),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend_ids = get_friend_ids(db, user.user_id)
    if friend_id not in friend_ids:
        raise HTTPException(status_code=403, detail="Not friends with this user")

    group_ids = list(dict.fromkeys([user.user_id] + friend_ids))
    group_hash = get_friend_group_hash(group_ids)

    live = _compute_on_the_fly(db, group_ids)
    cached = _get_cached(db, group_hash)
    all_awards = {**cached, **live}

    user_names = {
        u.user_id: u.user_name
        for u in db.query(User).filter(User.user_id.in_([user.user_id, friend_id])).all()
    }

    comparisons = []
    you_wins = 0
    friend_wins = 0

    for award_id, defn in AWARD_DEFINITIONS.items():
        entries = all_awards.get(award_id, [])
        you_entry = next((e for e in entries if e["user_id"] == user.user_id), None)
        friend_entry = next((e for e in entries if e["user_id"] == friend_id), None)

        you_val = you_entry.get("stat_value") if you_entry else None
        friend_val = friend_entry.get("stat_value") if friend_entry else None

        winner = None
        if you_val is not None and friend_val is not None:
            if award_id == "time_traveler":
                winner = "you" if you_val < friend_val else "friend" if friend_val < you_val else None
            elif award_id == "basic":
                winner = "you" if you_val < friend_val else "friend" if friend_val < you_val else None
            else:
                winner = "you" if you_val > friend_val else "friend" if friend_val > you_val else None

        if winner == "you":
            you_wins += 1
        elif winner == "friend":
            friend_wins += 1

        comparisons.append(HeadToHeadComparison(
            award_id=award_id,
            award_name=defn["name"],
            you=you_val,
            friend=friend_val,
            winner=winner,
            label=defn["description"],
        ))

    log_action(db, "awards.head_to_head_viewed", user_id=user.user_id,
               entity_type="user", entity_id=friend_id)

    return HeadToHeadResponse(
        you={"user_id": user.user_id, "user_name": user_names.get(user.user_id), "wins": you_wins},
        friend={"user_id": friend_id, "user_name": user_names.get(friend_id), "wins": friend_wins},
        comparisons=comparisons,
    )
