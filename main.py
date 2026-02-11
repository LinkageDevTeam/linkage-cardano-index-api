"""
Cardano Index API
A FastAPI application for providing cryptocurrency index data for Cardano ecosystem tokens.
"""

from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from app.routers import indexes, linkage_funds
from app.core.config import get_settings
from app.core.auth import verify_api_key
from app.db.database import get_db_manager
from app.services.historical_querier import get_historical_querier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    settings = get_settings()
    
    # Startup
    logger.info("Starting Cardano Index API...")
    
    # Initialize database
    db_manager = get_db_manager()
    try:
        await db_manager.create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Start historical data querier if enabled
    if settings.querier_enabled:
        try:
            querier = get_historical_querier()
            await querier.start()
            logger.info("Historical data querier started")
        except Exception as e:
            logger.error(f"Failed to start historical querier: {e}")
            # Don't fail startup if querier fails, just log the error
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cardano Index API...")
    
    # Close index service (e.g. MuesliSwap HTTP client)
    try:
        await indexes.index_service.close()
        logger.info("Index service closed")
    except Exception as e:
        logger.error(f"Error closing index service: {e}")
    
    # Stop historical querier
    if settings.querier_enabled:
        try:
            querier = get_historical_querier()
            await querier.stop()
            logger.info("Historical data querier stopped")
        except Exception as e:
            logger.error(f"Error stopping querier: {e}")
    
    # Close database connections
    try:
        await db_manager.close()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="Cardano Index API",
    description="API for accessing cryptocurrency index data from the Cardano ecosystem",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(indexes.router, prefix="/indexes", tags=["indexes"])
app.include_router(linkage_funds.router, prefix="/linkage-funds", tags=["linkage-funds"])

@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "message": "Cardano Index API",
        "version": "1.0.0",
        "description": "API for accessing cryptocurrency index data from the Cardano ecosystem",
        "docs": "/docs",
        "features": {
            "static_indexes": "Pre-configured token indexes with fixed weights",
            "dynamic_indexes": "Automatically updated indexes based on market conditions",
            "historical_data": "Real historical price data collected every 15 minutes",
            "live_prices": "Real-time price calculations from MuesliSwap"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    querier = get_historical_querier()
    querier_status = await querier.get_querier_status()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
        "database": "connected",
        "querier": {
            "enabled": settings.querier_enabled,
            "running": querier.is_running if settings.querier_enabled else False,
            "interval_minutes": settings.querier_interval_minutes,
            "last_run": querier_status.get("last_run_at") if querier_status else None,
            "success_rate": f"{querier_status.get('success_rate', 0) * 100:.1f}%" if querier_status else "N/A"
        }
    }

@app.get("/admin/querier/status", tags=["admin"])
async def get_querier_status(api_key: str = Depends(verify_api_key)):
    """Get detailed status of the historical data querier."""
    querier = get_historical_querier()
    status = await querier.get_querier_status()
    
    if not status:
        return {"message": "Querier has not started yet"}
    
    return {
        "querier_status": status,
        "settings": {
            "enabled": get_settings().querier_enabled,
            "interval_minutes": get_settings().querier_interval_minutes,
            "startup_delay_seconds": get_settings().querier_startup_delay_seconds,
            "timeout_seconds": get_settings().querier_timeout_seconds
        }
    }

@app.post("/admin/querier/force-run", tags=["admin"])
async def force_querier_run(api_key: str = Depends(verify_api_key)):
    """Force an immediate data collection run."""
    querier = get_historical_querier()
    result = await querier.force_collection()
    
    return {
        "message": "Forced data collection completed",
        "result": result
    }

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
