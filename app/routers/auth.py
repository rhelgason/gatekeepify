from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import AuthResponse, AuthUrlResponse, UserResponse
from app.services.audit import log_action
from app.services.spotify import SpotifyService, encrypt_token

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=settings.jwt_expiration_hours),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/login", response_model=AuthUrlResponse)
def login():
    service = SpotifyService()
    return AuthUrlResponse(auth_url=service.get_auth_url())


@router.get("/callback", response_model=AuthResponse)
def callback(code: str = Query(...), db: Session = Depends(get_db)):
    service = SpotifyService()

    try:
        token_info = service.exchange_code(code)
        access_token = token_info["access_token"]
        refresh_token = token_info.get("refresh_token", "")
        spotify_user = service.get_current_user(access_token)
        user_id = spotify_user["id"]
    except KeyError as e:
        log_action(db, "auth.callback", status="error", details={"error": f"Missing field: {e}"})
        raise HTTPException(status_code=502, detail="Unexpected response from Spotify")
    except Exception as e:
        log_action(db, "auth.callback", status="error", details={"error": str(e)})
        raise HTTPException(status_code=400, detail="Failed to exchange auth code")

    display_name = spotify_user.get("display_name", "")
    email = spotify_user.get("email")

    is_new = False
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        user.user_name = display_name
        user.email = email
        if refresh_token:
            user.spotify_refresh_token = encrypt_token(refresh_token)
    else:
        is_new = True
        user = User(
            user_id=user_id,
            user_name=display_name,
            email=email,
            spotify_refresh_token=encrypt_token(refresh_token),
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
    db.commit()
    db.refresh(user)

    log_action(
        db,
        "auth.callback",
        user_id=user_id,
        details={"is_new_user": is_new, "display_name": display_name},
    )

    token = create_jwt(user_id)

    if settings.frontend_url:
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/callback?token={token}"
        )

    return AuthResponse(
        access_token=token,
        user=UserResponse(
            user_id=user.user_id,
            user_name=user.user_name,
            email=user.email,
            created_at=user.created_at,
        ),
    )


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        user_id=user.user_id,
        user_name=user.user_name,
        email=user.email,
        created_at=user.created_at,
    )
