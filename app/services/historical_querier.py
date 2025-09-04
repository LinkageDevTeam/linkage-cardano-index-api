"""
Historical data collection service for background price tracking
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import traceback

from app.services.index_service import IndexService
from app.db.database import get_db_manager
from app.db.models import HistoricalIndexPrice, QuerierStatus, IndexSnapshot
from app.core.config import get_settings
from sqlalchemy import select, desc
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class HistoricalQuerier:
    """Background service for collecting historical price data."""
    
    def __init__(self):
        self.settings = get_settings()
        self.index_service = IndexService()
        self.db_manager = get_db_manager()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self._querier_name = "main_historical_querier"
    
    async def start(self):
        """Start the background data collection."""
        if self.is_running:
            logger.warning("Historical querier is already running")
            return
        
        logger.info(f"Starting historical querier with {self.settings.querier_interval_minutes} minute intervals")
        self.is_running = True
        
        # Start background task with initial delay
        self._task = asyncio.create_task(self._collection_loop())
    
    async def stop(self):
        """Stop the background data collection."""
        if not self.is_running:
            return
        
        logger.info("Stopping historical querier...")
        self.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Historical querier stopped")
    
    async def _collection_loop(self):
        """Main collection loop that runs periodically."""
        try:
            # Initial startup delay
            await asyncio.sleep(self.settings.querier_startup_delay_seconds)
            
            while self.is_running:
                try:
                    await self._collect_all_data()
                    
                    # Wait for next collection
                    interval_seconds = self.settings.querier_interval_minutes * 60
                    await asyncio.sleep(interval_seconds)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in collection loop: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        except asyncio.CancelledError:
            logger.info("Collection loop cancelled")
    
    async def force_collection(self) -> Dict:
        """Force an immediate data collection run."""
        start_time = datetime.utcnow()
        logger.info("Starting forced data collection...")
        
        try:
            result = await self._collect_all_data()
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "success": True,
                "message": f"Collected data for {result['successful_indexes']} indexes",
                "duration_seconds": duration,
                "details": result
            }
        
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Forced collection failed: {e}")
            
            return {
                "success": False,
                "message": "Data collection failed",
                "duration_seconds": duration,
                "error": str(e)
            }
    
    async def _collect_all_data(self) -> Dict:
        """Collect price data for all configured indexes."""
        start_time = datetime.utcnow()
        successful_indexes = 0
        failed_indexes = 0
        errors = []
        
        try:
            # Get all configured indexes
            indexes = await self.index_service.load_indexes_config()
            
            async with self.db_manager.get_session() as session:
                for index in indexes:
                    try:
                        # Calculate current price data
                        price_data = await self.index_service.calculate_index_price(index.id)
                        
                        # Store historical price record
                        historical_record = HistoricalIndexPrice(
                            index_id=index.id,
                            timestamp=start_time,
                            price=price_data.price,
                            market_cap=price_data.market_cap,
                            volume_24h=getattr(price_data, 'volume_24h', 0.0),
                            price_change_24h=price_data.price_change_24h,
                            price_change_7d=price_data.price_change_7d,
                            token_count=len(index.tokens) if index.tokens else 0,
                            index_type=index.index_type,
                            calculation_successful=True
                        )
                        
                        session.add(historical_record)
                        successful_indexes += 1
                        
                        logger.debug(f"Collected data for {index.id}: {price_data.price:.4f}")
                    
                    except Exception as e:
                        failed_indexes += 1
                        error_msg = f"Index {index.id}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(f"Failed to collect data for {index.id}: {e}")
                        
                        # Store failed record
                        failed_record = HistoricalIndexPrice(
                            index_id=index.id,
                            timestamp=start_time,
                            price=0.0,
                            market_cap=0.0,
                            calculation_successful=False,
                            error_message=str(e)
                        )
                        session.add(failed_record)
                
                # Update querier status
                await self._update_querier_status(
                    session, successful_indexes > 0, 
                    None if successful_indexes > 0 else "; ".join(errors[:3])
                )
                
                # Commit all changes
                await session.commit()
        
        except Exception as e:
            logger.error(f"Critical error in data collection: {e}")
            async with self.db_manager.get_session() as session:
                await self._update_querier_status(session, False, str(e))
                await session.commit()
            raise
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Data collection completed: {successful_indexes} successful, {failed_indexes} failed in {duration:.2f}s")
        
        return {
            "successful_indexes": successful_indexes,
            "failed_indexes": failed_indexes,
            "duration_seconds": duration,
            "errors": errors
        }
    
    async def _update_querier_status(self, session, success: bool, error_message: Optional[str] = None):
        """Update the querier status in the database."""
        try:
            # Get existing status record
            stmt = select(QuerierStatus).where(QuerierStatus.querier_name == self._querier_name)
            result = await session.execute(stmt)
            status_record = result.scalar_one_or_none()
            
            now = datetime.utcnow()
            
            if status_record is None:
                # Create new status record
                status_record = QuerierStatus(
                    querier_name=self._querier_name,
                    last_run_at=now,
                    total_runs=1,
                    successful_runs=1 if success else 0,
                    failed_runs=0 if success else 1,
                    is_active=True
                )
                
                if success:
                    status_record.last_success_at = now
                else:
                    status_record.last_error_at = now
                    status_record.last_error_message = error_message
                
                session.add(status_record)
            else:
                # Update existing record
                status_record.last_run_at = now
                status_record.total_runs += 1
                status_record.updated_at = now
                
                if success:
                    status_record.successful_runs += 1
                    status_record.last_success_at = now
                else:
                    status_record.failed_runs += 1
                    status_record.last_error_at = now
                    status_record.last_error_message = error_message
        
        except Exception as e:
            logger.error(f"Failed to update querier status: {e}")
    
    async def get_querier_status(self) -> Optional[Dict]:
        """Get the current status of the querier."""
        try:
            async with self.db_manager.get_session() as session:
                stmt = select(QuerierStatus).where(QuerierStatus.querier_name == self._querier_name)
                result = await session.execute(stmt)
                status_record = result.scalar_one_or_none()
                
                if status_record is None:
                    return None
                
                success_rate = 0.0
                if status_record.total_runs > 0:
                    success_rate = status_record.successful_runs / status_record.total_runs
                
                return {
                    "querier_name": status_record.querier_name,
                    "last_run_at": status_record.last_run_at.isoformat() if status_record.last_run_at else None,
                    "last_success_at": status_record.last_success_at.isoformat() if status_record.last_success_at else None,
                    "last_error_at": status_record.last_error_at.isoformat() if status_record.last_error_at else None,
                    "last_error_message": status_record.last_error_message,
                    "total_runs": status_record.total_runs,
                    "successful_runs": status_record.successful_runs,
                    "failed_runs": status_record.failed_runs,
                    "success_rate": success_rate,
                    "is_active": status_record.is_active,
                    "created_at": status_record.created_at.isoformat(),
                    "updated_at": status_record.updated_at.isoformat()
                }
        
        except Exception as e:
            logger.error(f"Failed to get querier status: {e}")
            return None


# Global querier instance
_querier_instance: Optional[HistoricalQuerier] = None

def get_historical_querier() -> HistoricalQuerier:
    """Get the global historical querier instance."""
    global _querier_instance
    if _querier_instance is None:
        _querier_instance = HistoricalQuerier()
    return _querier_instance
