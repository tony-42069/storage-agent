from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Create declarative base
Base = declarative_base()

def get_database_url() -> str:
    """Get database URL from environment or default to SQLite for development"""
    return os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/storage_agent'
    )

def init_database(database_url: str = None):
    """
    Initialize database connection
    
    Args:
        database_url: Optional database URL, defaults to environment variable
    """
    if database_url is None:
        database_url = get_database_url()
    
    logger.info(f"Initializing database connection to {database_url}")
    
    # Create engine
    engine = create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800  # Recycle connections after 30 minutes
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    session_factory = sessionmaker(bind=engine)
    
    # Create thread-safe session registry
    Session = scoped_session(session_factory)
    
    logger.info("Database initialization complete")
    return Session

def get_session():
    """Get database session from thread-local registry"""
    return scoped_session(sessionmaker())

class DatabaseSessionManager:
    """Context manager for database sessions"""
    
    def __init__(self):
        self.session = get_session()
    
    def __enter__(self):
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Roll back on error
            self.session.rollback()
            logger.error(f"Rolling back transaction due to {exc_type.__name__}: {exc_val}")
        else:
            # Commit on success
            self.session.commit()
        
        # Always close the session
        self.session.close()
