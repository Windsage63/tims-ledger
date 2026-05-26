from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import ensure_sqlite_parent_dir

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

ensure_sqlite_parent_dir(settings.database_url)

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session]:
    with SessionLocal() as session:
        yield session
