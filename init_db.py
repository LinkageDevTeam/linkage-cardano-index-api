#!/usr/bin/env python3
"""
Database initialization script for Cardano Index API
"""

import asyncio
import logging
from app.db.database import get_db_manager
from app.core.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_database():
    """Initialize the database tables."""
    logger.info("Initializing Cardano Index API database...")
    
    settings = get_settings()
    logger.info(f"Database URL: {settings.database_url}")
    
    db_manager = get_db_manager()
    
    try:
        # Create all tables
        await db_manager.create_tables()
        logger.info("✅ Database tables created successfully")
        
        # Test connection
        async with db_manager.get_session() as session:
            logger.info("✅ Database connection test successful")
        
        logger.info("🎉 Database initialization completed!")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    finally:
        await db_manager.close()

async def reset_database():
    """Reset the database (drop and recreate tables)."""
    logger.warning("⚠️  RESETTING DATABASE - ALL DATA WILL BE LOST!")
    
    db_manager = get_db_manager()
    
    try:
        # Drop all tables
        await db_manager.drop_tables()
        logger.info("✅ Database tables dropped")
        
        # Recreate all tables
        await db_manager.create_tables()
        logger.info("✅ Database tables recreated")
        
        logger.info("🎉 Database reset completed!")
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        raise
    finally:
        await db_manager.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        # Reset database
        asyncio.run(reset_database())
    else:
        # Initialize database
        asyncio.run(init_database())
