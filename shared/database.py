from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from shared.models import Base
import os
from typing import Optional


def get_database_url(
    user: Optional[str] = None,
    password: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None
) -> str:
    """Construct database URL from parameters or environment variables."""
    user = user or os.getenv('POSTGRES_USER', 'bot_user')
    password = password or os.getenv('POSTGRES_PASSWORD', 'password')
    host = host or os.getenv('POSTGRES_HOST', 'localhost')
    port = port or int(os.getenv('POSTGRES_PORT', '5432'))
    database = database or os.getenv('POSTGRES_DB', 'sticker_collector')
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def create_db_engine():
    """Create and return SQLAlchemy engine."""
    database_url = get_database_url()
    engine = create_engine(
        database_url,
        pool_pre_ping=True,  # Enable connection health checks
        pool_size=10,
        max_overflow=20
    )
    return engine


def init_database(engine):
    """Initialize database by creating all tables."""
    Base.metadata.create_all(engine)


def get_session_factory(engine):
    """Create and return a session factory."""
    return sessionmaker(bind=engine)


def get_session(session_factory) -> Session:
    """Get a new database session."""
    return session_factory()
