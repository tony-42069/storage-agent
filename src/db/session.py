"""Database session management and connection handling."""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool

from src.utils.logger import get_logger
from src.models.base import Base

logger = get_logger(__name__)


def get_database_url() -> str:
    """Get database URL from environment or default."""
    return os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/storage_agent'
    )


def get_async_database_url() -> str:
    """Get async database URL for async operations."""
    url = get_database_url()
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


_sync_engine = None
_sync_session_factory = None
_async_engine = None
_async_session_factory = None


def get_sync_engine():
    """Get or create synchronous database engine."""
    global _sync_engine
    if _sync_engine is None:
        database_url = get_database_url()
        logger.info(f"Creating sync engine for: {database_url.split('@')[0]}@...")
        
        _sync_engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False,
        )
        
        @event.listens_for(_sync_engine, "connect")
        def set_session_settings(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("SET search_path TO public")
            cursor.close()
    
    return _sync_engine


def get_sync_session() -> Session:
    """Get a synchronous database session."""
    global _sync_session_factory
    if _sync_session_factory is None:
        engine = get_sync_engine()
        _sync_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return _sync_session_factory()


def get_scoped_session():
    """Get a thread-safe scoped session."""
    engine = get_sync_engine()
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return scoped_session(session_factory)


def init_database():
    """Initialize database tables."""
    engine = get_sync_engine()
    Base.metadata.create_all(engine)
    logger.info("Database tables created/verified")


def get_async_engine():
    """Get or create async database engine."""
    global _async_engine
    if _async_engine is None:
        database_url = get_async_database_url()
        logger.info(f"Creating async engine for: {database_url.split('@')[0]}@...")
        
        _async_engine = create_async_engine(
            database_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False,
        )
    
    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


class DatabaseSessionManager:
    """Context manager for synchronous database sessions."""
    
    def __init__(self):
        self.session = get_sync_session()
    
    def __enter__(self) -> Session:
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
            logger.error(f"Rolling back transaction: {exc_type.__name__}: {exc_val}")
        else:
            try:
                self.session.commit()
            except Exception as e:
                self.session.rollback()
                logger.error(f"Commit failed: {e}")
                raise
        
        self.session.close()


async def close_async_engine():
    """Close the async engine."""
    global _async_engine
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        logger.info("Async engine closed")


def close_sync_engine():
    """Close the sync engine."""
    global _sync_engine
    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None
        logger.info("Sync engine closed")
