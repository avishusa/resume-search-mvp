from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _ensure_sqlite_folder(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return

    database_path = database_url.replace("sqlite:///", "", 1)
    if database_path == ":memory:":
        return

    Path(database_path).parent.mkdir(parents=True, exist_ok=True)


settings = get_settings()
_ensure_sqlite_folder(settings.database_url)
engine = create_engine(
    settings.database_url,
    connect_args=_connect_args(settings.database_url),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from app.models import batch_run  # noqa: F401
    from app.models import resume  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_resume_provider_columns()


def _ensure_resume_provider_columns() -> None:
    inspector = inspect(engine)
    if "resumes" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("resumes")
    }
    columns_to_add = []
    if "provider_name" not in existing_columns:
        columns_to_add.append("provider_name VARCHAR(64)")
    if "source_id" not in existing_columns:
        columns_to_add.append("source_id VARCHAR(1024)")

    if not columns_to_add:
        return

    with engine.begin() as connection:
        for column_definition in columns_to_add:
            connection.execute(
                text(f"ALTER TABLE resumes ADD COLUMN {column_definition}")
            )
