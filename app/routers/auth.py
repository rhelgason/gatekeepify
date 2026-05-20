from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from sqlalchemy.orm import Session

import logging

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import AuthResponse, AuthUrlResponse, UserResponse
from app.services.audit import log_action
from app.services.ingestion import upsert_from_recent_listens
from app.services.spotify import SpotifyService, encrypt_token

logger = logging.getLogger("gatekeepify.auth")

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiration_hours),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
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
    if user.token_invalidated_at:
        iat = payload.get("iat")
        if iat and datetime.fromtimestamp(iat, tz=timezone.utc) < user.token_invalidated_at.replace(
            tzinfo=timezone.utc
        ):
            raise HTTPException(status_code=401, detail="Token has been revoked")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/login", response_model=AuthUrlResponse)
def login(return_url: str = Query(None), invite_code: str = Query(None)):
    import base64
    import json as _json

    service = SpotifyService()
    auth_url = service.get_auth_url()
    if return_url or invite_code:
        state_data = {}
        if return_url:
            state_data["url"] = return_url
        if invite_code:
            state_data["invite"] = invite_code
        state = base64.urlsafe_b64encode(_json.dumps(state_data).encode()).decode()
        auth_url += f"&state={state}"
    return AuthUrlResponse(auth_url=auth_url)


@router.get("/callback", response_model=AuthResponse)
def callback(code: str = Query(...), state: str = Query(None), db: Session = Depends(get_db)):
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
    images = spotify_user.get("images", [])
    profile_image = images[0]["url"] if images else None

    is_new = False
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        user.user_name = display_name
        user.email = email
        user.image_url = profile_image
        if refresh_token:
            user.spotify_refresh_token = encrypt_token(refresh_token)
    else:
        is_new = True
        user = User(
            user_id=user_id,
            user_name=display_name,
            email=email,
            image_url=profile_image,
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

    if is_new:
        try:
            recent = service.get_recent_listens(access_token)
            if recent:
                count = upsert_from_recent_listens(db, recent, user_id)
                logger.info(f"Ingested {count} recent listens for new user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to fetch initial data for {user_id}: {e}")

    token = create_jwt(user_id)

    redirect_url = None
    invite_code = None
    if state:
        try:
            import base64
            import json as _json

            decoded = base64.urlsafe_b64decode(state.encode()).decode()
            try:
                state_data = _json.loads(decoded)
                origin = state_data.get("url", "")
                invite_code = state_data.get("invite")
            except (_json.JSONDecodeError, AttributeError):
                origin = decoded
            allowed_origins = {settings.frontend_url}
            if settings.allowed_origins:
                allowed_origins.update(o.strip() for o in settings.allowed_origins.split(",") if o.strip())
            if origin in allowed_origins:
                redirect_url = origin
            else:
                logger.warning(f"Rejected redirect to untrusted origin: {origin}")
        except Exception:
            pass
    if not redirect_url:
        redirect_url = settings.frontend_url

    if redirect_url:
        callback_url = f"{redirect_url}/auth/callback#token={token}"
        if invite_code:
            from urllib.parse import quote

            callback_url += f"&invite={quote(invite_code)}"
        return RedirectResponse(url=callback_url)

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
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log_action(db, "auth.me", user_id=user.user_id)
    return UserResponse(
        user_id=user.user_id,
        user_name=user.user_name,
        email=user.email,
        image_url=user.image_url,
        created_at=user.created_at,
    )
