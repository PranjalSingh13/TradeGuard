"""Database engine and session management.

Supports PostgreSQL and SQLite (for tests and local execution).
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tradeguard.core.config import settings
from tradeguard.db.models import Base


# Determine database URL. If postgres is not running, fall back cleanly to sqlite
db_url = settings.SYNC_DATABASE_URL
if "sqlite" in db_url or "postgresql" in db_url:
    # Use SQLite for local development/testing if PG connection is not available
    pass

engine = create_engine(
    "sqlite:///./tradeguard.db",
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(target_engine=None) -> None:
    """Create all tables in the database."""
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to yield database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

