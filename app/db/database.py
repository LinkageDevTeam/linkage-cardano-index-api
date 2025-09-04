"""
Database connection and session management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.db.models import Base
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_session = None
        self._setup_database()
    
    def _setup_database(self):
        """Initialize database engine and session factory."""
        # Use SQLite by default, PostgreSQL for production
        database_url = self.settings.database_url
        
        # Adjust URL for async drivers
        if database_url.startswith("sqlite"):
            # Use aiosqlite for async SQLite
            database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")
        elif database_url.startswith("postgresql"):
            # Use asyncpg for async PostgreSQL
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        self.engine = create_async_engine(
            database_url,
            echo=self.settings.debug,  # Log SQL queries in debug mode
            future=True,
            pool_pre_ping=True,  # Verify connections before use
        )
        
        self.async_session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info(f"Database engine created: {database_url}")
    
    async def create_tables(self):
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    
    async def drop_tables(self):
        """Drop all database tables (for testing)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")
    
    def get_session(self) -> AsyncSession:
        """Get a new database session."""
        return self.async_session()
    
    async def close(self):
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database engine closed")

# Global database manager instance
_db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

async def get_db_session():
    """Dependency for getting database sessions in FastAPI."""
    db_manager = get_db_manager()
    async with db_manager.get_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
