from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from fraud_platform_common.config import RuntimeSettings


def build_engine(settings: RuntimeSettings) -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True)


def build_session_factory(settings: RuntimeSettings) -> sessionmaker[Session]:
    return sessionmaker(bind=build_engine(settings), autoflush=False, autocommit=False)


@contextmanager
def session_scope(settings: RuntimeSettings) -> Iterator[Session]:
    session_factory = build_session_factory(settings)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
