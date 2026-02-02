import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

def _normalize_db_url(url: str) -> str:
    """
    Render often gives DATABASE_URL as:
      postgres://user:pass@host:5432/db
    SQLAlchemy + psycopg wants:
      postgresql+psycopg://user:pass@host:5432/db
    """
    if not url:
        return ""

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)

    # If someone already provided postgresql://, upgrade to psycopg driver explicitly
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url


DATABASE_URL = _normalize_db_url(os.getenv("DATABASE_URL") or os.getenv("INTERNAL_DATABASE_URL") or "")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Add it in Render Environment Variables.")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
