from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _build_engine(url: str):
    connect_args = {}
    kwargs = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        # PostgreSQL connection pooling
        kwargs.update(
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=300,
        )
    return create_engine(url, connect_args=connect_args, **kwargs)


engine = _build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
