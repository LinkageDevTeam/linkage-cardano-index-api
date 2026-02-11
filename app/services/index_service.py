"""
Index calculation and management service
"""

import json
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

from app.models.schemas import (
    IndexMetadata, PriceData, HistoricalPrice, VolumeData,
    TokenInfo, IntervalType, DynamicSelectionCriteria
)
from typing import Dict
from app.services.muesliswap import MuesliswapService
from app.services.linkage_finance import LinkageFinanceService
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class IndexService:
    """Service for managing and calculating cryptocurrency indexes."""
    
    def __init__(self):
        self.settings = get_settings()
        self.muesliswap = MuesliswapService()
        self.linkage_finance = LinkageFinanceService()
        self._cache: Dict = {}
        self._cache_timestamps: Dict = {}
        
    async def load_indexes_config(self) -> List[IndexMetadata]:
        """
        Load index configurations from JSON file.
        
        Returns:
            List[IndexMetadata]: List of configured indexes
        """
        config_path = Path(self.settings.index_config_path)
        
        if not config_path.exists():
            logger.warning(f"Index config file not found: {config_path}")
            return []
        
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            indexes = []
            for index_data in config_data.get('indexes', []):
                # Handle static vs dynamic configuration
                tokens = []
                dynamic_criteria = None
                
                if index_data.get('index_type') == 'dynamic' and 'dynamic_criteria' in index_data:
                    # Dynamic index - parse criteria
                    dynamic_criteria = DynamicSelectionCriteria(**index_data['dynamic_criteria'])
                    # Tokens will be empty for dynamic indexes initially
                elif 'tokens' in index_data:
                    # Static index - convert token data to TokenInfo objects
                    for token_data in index_data.get('tokens', []):
                        token = TokenInfo(**token_data)
                        tokens.append(token)
                
                # Create IndexMetadata object
                index_data['tokens'] = tokens
                index_data['dynamic_criteria'] = dynamic_criteria
                
                if 'created_at' in index_data:
                    index_data['created_at'] = datetime.fromisoformat(index_data['created_at'])
                if 'updated_at' in index_data:
                    index_data['updated_at'] = datetime.fromisoformat(index_data['updated_at'])
                
                index_metadata = IndexMetadata(**index_data)
                indexes.append(index_metadata)
            
            logger.info(f"Loaded {len(indexes)} index configurations")
            return indexes
            
        except Exception as e:
            logger.error(f"Failed to load index config: {e}")
            raise Exception(f"Config loading error: {e}")
    
    async def get_all_indexes(self) -> List[IndexMetadata]:
        """Get all configured indexes, including Linkage Finance funds."""
        static_indexes = await self.load_indexes_config()
        
        # Fetch Linkage Finance funds as indexes
        try:
            linkage_funds = await self.linkage_finance.get_funds_as_indexes()
            logger.info(f"Loaded {len(linkage_funds)} Linkage Finance funds as indexes")
            return static_indexes + linkage_funds
        except Exception as e:
            logger.error(f"Failed to load Linkage Finance funds: {e}")
            # Return static indexes even if Linkage Finance fails
            return static_indexes
    
    async def get_index_by_id(self, index_id: str) -> Optional[IndexMetadata]:
        """
        Get a specific index by its ID.
        
        Args:
            index_id: The index identifier
            
        Returns:
            IndexMetadata: The index metadata or None if not found
        """
        # Check static indexes first
        indexes = await self.load_indexes_config()
        for index in indexes:
            if index.id == index_id:
                return index
        
        # Check Linkage Finance funds
        if index_id.startswith("linkage-fund-"):
            fund_id = index_id.replace("linkage-fund-", "")
            fund = await self.linkage_finance.get_fund_by_id(fund_id)
            if fund:
                return fund.to_index_metadata()
        
        return None
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        timestamp = self._cache_timestamps[cache_key]
        expiry = timestamp + timedelta(seconds=self.settings.cache_ttl_seconds)
        return datetime.utcnow() < expiry
    
    def _get_from_cache(self, cache_key: str):
        """Get data from cache if valid."""
        if self._is_cache_valid(cache_key):
            return self._cache.get(cache_key)
        return None
    
    def _set_cache(self, cache_key: str, data):
        """Set data in cache with timestamp."""
        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = datetime.utcnow()
    
    async def close(self) -> None:
        """Close shared resources (e.g. MuesliSwap HTTP client). Call from app shutdown."""
        await self.muesliswap.close()
    
    async def get_index_tokens(self, index: IndexMetadata) -> List[TokenInfo]:
        """
        Get tokens for an index (static or dynamic).
        
        Args:
            index: Index metadata
            
        Returns:
            List[TokenInfo]: List of tokens with weights
        """
        if index.is_dynamic and index.dynamic_criteria:
            # Dynamic index - select tokens based on criteria
            cache_key = f"dynamic_tokens_{index.id}"
            cached_tokens = self._get_from_cache(cache_key)
            
            if cached_tokens:
                return cached_tokens
            
            try:
                selected_tokens = await self.muesliswap.select_tokens_dynamically(index.dynamic_criteria)
                
                # Cache the dynamically selected tokens
                self._set_cache(cache_key, selected_tokens)
                
                logger.info(f"Dynamically selected {len(selected_tokens)} tokens for index {index.id}")
                return selected_tokens
                
            except Exception as e:
                logger.error(f"Failed to select dynamic tokens for {index.id}: {e}")
                # Fall back to empty list
                return []
        else:
            # Static index - return configured tokens
            return index.tokens or []
    
    async def calculate_index_price(self, index_id: str) -> PriceData:
        """
        Calculate the current price for an index.
        
        Args:
            index_id: The index identifier
            
        Returns:
            PriceData: Current index price and market data
        """
        cache_key = f"price_{index_id}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            age_seconds = int((datetime.utcnow() - self._cache_timestamps[cache_key]).total_seconds())
            return cached_data.model_copy(update={"cache_age_seconds": age_seconds})
        
        index = await self.get_index_by_id(index_id)
        if not index:
            raise Exception(f"Index not found: {index_id}")
        
        try:
            # Get tokens for this index (static or dynamic)
            index_tokens = await self.get_index_tokens(index)
            
            if not index_tokens:
                raise Exception(f"No tokens available for index {index_id}")
            
            # Fetch prices for all tokens in the index
            token_prices = await self.muesliswap.get_multiple_token_prices(index_tokens)
            
            if not token_prices:
                raise Exception(f"No price data available for index {index_id}")
            
            # Calculate weighted index price
            total_weighted_price = 0.0
            total_market_cap = 0.0
            total_weight = 0.0
            price_change_24h = 0.0
            price_change_7d = 0.0
            
            for token in index_tokens:
                if token.name in token_prices:
                    price_data = token_prices[token.name]
                    weighted_price = price_data.price * token.weight
                    total_weighted_price += weighted_price
                    total_market_cap += price_data.marketCap * token.weight
                    total_weight += token.weight
                    
                    # Weight the price changes by token weight
                    if hasattr(price_data, 'priceChange'):
                        if '24h' in price_data.priceChange:
                            price_change_24h += price_data.priceChange['24h'] * token.weight
                        if '7d' in price_data.priceChange:
                            price_change_7d += price_data.priceChange['7d'] * token.weight
            
            if total_weight == 0:
                raise Exception(f"No valid price data for index {index_id}")
            
            # Normalize the index price by base value
            final_price = (total_weighted_price / total_weight) * index.base_value
            
            price_data = PriceData(
                index_id=index_id,
                price=final_price,
                market_cap=total_market_cap,
                timestamp=datetime.utcnow(),
                price_change_24h=price_change_24h / total_weight if total_weight > 0 else 0.0,
                price_change_7d=price_change_7d / total_weight if total_weight > 0 else 0.0
            )
            
            # Cache the result
            self._set_cache(cache_key, price_data)
            return price_data
            
        except Exception as e:
            logger.error(f"Failed to calculate price for index {index_id}: {e}")
            raise
    
    async def get_index_volume(self, index_id: str) -> VolumeData:
        """
        Calculate volume data for an index.
        
        Args:
            index_id: The index identifier
            
        Returns:
            VolumeData: Volume information for the index
        """
        cache_key = f"volume_{index_id}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        index = await self.get_index_by_id(index_id)
        if not index:
            raise Exception(f"Index not found: {index_id}")
        
        try:
            # Get tokens for this index (static or dynamic)
            index_tokens = await self.get_index_tokens(index)
            
            if not index_tokens:
                raise Exception(f"No tokens available for index {index_id}")
                
            # Fetch prices for all tokens (which includes volume data)
            token_prices = await self.muesliswap.get_multiple_token_prices(index_tokens)
            
            total_volume_24h = 0.0
            total_volume_7d = 0.0
            total_volume_change = 0.0
            
            for token in index_tokens:
                if token.name in token_prices:
                    price_data = token_prices[token.name]
                    # Weight the volume by token weight in index
                    total_volume_24h += (price_data.volume.base + price_data.volume.quote) * token.weight
                    total_volume_7d += (price_data.volume7d.base + price_data.volume7d.quote) * token.weight
                    total_volume_change += (price_data.volumeChange.base + price_data.volumeChange.quote) * token.weight
            
            volume_data = VolumeData(
                index_id=index_id,
                volume_24h=total_volume_24h,
                volume_7d=total_volume_7d,
                volume_change=total_volume_change,
                timestamp=datetime.utcnow()
            )
            
            # Cache the result
            self._set_cache(cache_key, volume_data)
            return volume_data
            
        except Exception as e:
            logger.error(f"Failed to calculate volume for index {index_id}: {e}")
            raise
    
    async def get_historical_prices(
        self,
        index_id: str,
        start_date: datetime,
        end_date: datetime,
        interval: IntervalType = IntervalType.ONE_DAY
    ) -> List[HistoricalPrice]:
        """
        Retrieve historical price data for an index from the database.
        
        Args:
            index_id: The index identifier
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Time interval for data points
            
        Returns:
            List[HistoricalPrice]: List of historical price points
        """
        from app.db.database import get_db_manager
        from app.db.models import HistoricalIndexPrice
        from sqlalchemy import select, and_
        
        index = await self.get_index_by_id(index_id)
        if not index:
            raise Exception(f"Index not found: {index_id}")
        
        db_manager = get_db_manager()
        
        async with db_manager.get_session() as session:
            # Query historical data from database
            stmt = select(HistoricalIndexPrice).where(
                and_(
                    HistoricalIndexPrice.index_id == index_id,
                    HistoricalIndexPrice.timestamp >= start_date,
                    HistoricalIndexPrice.timestamp <= end_date,
                    HistoricalIndexPrice.calculation_successful == True
                )
            ).order_by(HistoricalIndexPrice.timestamp)
            
            result = await session.execute(stmt)
            db_records = result.scalars().all()
            
            if not db_records:
                logger.warning(f"No historical data found for index {index_id} between {start_date} and {end_date}")
                return []
            
            # Convert database records to HistoricalPrice objects
            historical_prices = []
            
            # Group data by the requested interval
            grouped_data = self._group_data_by_interval(db_records, interval)
            
            for timestamp, records in grouped_data.items():
                if start_date <= timestamp <= end_date:
                    # Use the last record in each interval (most recent)
                    record = records[-1]
                    
                    historical_price = HistoricalPrice(
                        timestamp=timestamp,
                        price=record.price,
                        volume=record.volume_24h
                    )
                    historical_prices.append(historical_price)
            
            logger.info(f"Retrieved {len(historical_prices)} historical data points for {index_id}")
            return sorted(historical_prices, key=lambda x: x.timestamp)
    
    def _group_data_by_interval(self, records: List, interval: IntervalType) -> Dict[datetime, List]:
        """Group historical records by the requested time interval."""
        from collections import defaultdict
        
        # Determine time delta based on interval
        interval_deltas = {
            IntervalType.ONE_HOUR: timedelta(hours=1),
            IntervalType.FOUR_HOURS: timedelta(hours=4),
            IntervalType.ONE_DAY: timedelta(days=1),
            IntervalType.ONE_WEEK: timedelta(weeks=1),
            IntervalType.ONE_MONTH: timedelta(days=30),
        }
        
        delta = interval_deltas.get(interval, timedelta(days=1))
        grouped = defaultdict(list)
        
        for record in records:
            # Round timestamp down to interval boundary
            if interval == IntervalType.ONE_HOUR:
                boundary = record.timestamp.replace(minute=0, second=0, microsecond=0)
            elif interval == IntervalType.FOUR_HOURS:
                hour = (record.timestamp.hour // 4) * 4
                boundary = record.timestamp.replace(hour=hour, minute=0, second=0, microsecond=0)
            elif interval == IntervalType.ONE_DAY:
                boundary = record.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            elif interval == IntervalType.ONE_WEEK:
                # Round to beginning of week (Monday)
                days_since_monday = record.timestamp.weekday()
                boundary = record.timestamp.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
            elif interval == IntervalType.ONE_MONTH:
                # Round to beginning of month
                boundary = record.timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                boundary = record.timestamp
            
            grouped[boundary].append(record)
        
        return dict(grouped)
