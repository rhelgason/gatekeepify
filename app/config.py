from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///db/gatekeepify.db"
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://localhost:8000/auth/callback"
    spotify_scopes: str = "user-read-private user-read-email user-read-recently-played user-top-read"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24 * 7
    encryption_key: str = ""
    redis_url: str = "redis://localhost:6379/0"
    poll_interval_seconds: int = 900
    backfill_interval_seconds: int = 120

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def validate_settings():
    import sys

    if settings.jwt_secret == "dev-secret-change-in-production":
        print(
            "WARNING: Using default JWT secret. Set JWT_SECRET env var before deploying.",
            file=sys.stderr,
        )
    if not settings.encryption_key:
        print(
            "WARNING: ENCRYPTION_KEY not set. Spotify refresh tokens will be stored unencrypted.",
            file=sys.stderr,
        )
