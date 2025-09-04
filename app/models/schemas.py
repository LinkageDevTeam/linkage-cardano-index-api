"""
Pydantic schemas for the Cardano Index API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class IntervalType(str, Enum):
    """Available time intervals for historical data."""
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"

class TokenInfo(BaseModel):
    """Token information for index components."""
    name: str = Field(..., description="Token name")
    policy_id: str = Field(..., description="Cardano policy ID")
    token_name: str = Field(..., description="Token name on Cardano")
    weight: float = Field(..., ge=0, le=1, description="Weight in the index (0-1)")
    description: Optional[str] = Field(None, description="Token description")

class DynamicSelectionCriteria(BaseModel):
    """Criteria for dynamic token selection."""
    selection_method: str = Field(..., description="Selection method: 'market_cap', 'volume', 'custom'")
    limit: int = Field(..., ge=1, le=50, description="Maximum number of tokens to select")
    min_volume_ada: float = Field(default=100.0, description="Minimum 24h volume in ADA")
    min_market_cap: Optional[float] = Field(None, description="Minimum market cap filter")
    exclude_tokens: List[str] = Field(default=[], description="Token symbols to exclude")
    include_categories: List[str] = Field(default=[], description="Categories to include (e.g., 'defi', 'gaming')")
    weighting_method: str = Field(default="market_cap", description="How to weight tokens: 'market_cap', 'equal'")
    rebalance_frequency: str = Field(default="daily", description="Rebalancing frequency")

class IndexMetadata(BaseModel):
    """Metadata for a cryptocurrency index."""
    id: str = Field(..., description="Unique index identifier")
    name: str = Field(..., description="Human-readable index name")
    description: str = Field(..., description="Index description")
    category: str = Field(..., description="Index category (e.g., 'defi', 'gaming')")
    methodology: str = Field(..., description="Calculation methodology")
    index_type: str = Field(default="static", description="Index type: 'static' or 'dynamic'")
    tokens: Optional[List[TokenInfo]] = Field(default=[], description="List of tokens (for static indexes)")
    dynamic_criteria: Optional[DynamicSelectionCriteria] = Field(None, description="Dynamic selection criteria")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    base_value: float = Field(default=100.0, description="Base index value")
    
    @property
    def is_dynamic(self) -> bool:
        """Check if this is a dynamic index."""
        return self.index_type == "dynamic" and self.dynamic_criteria is not None

class PriceData(BaseModel):
    """Current price data for an index."""
    index_id: str = Field(..., description="Index identifier")
    price: float = Field(..., description="Current index price")
    market_cap: float = Field(..., description="Total market capitalization")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Price timestamp")
    price_change_24h: float = Field(default=0.0, description="24-hour price change percentage")
    price_change_7d: float = Field(default=0.0, description="7-day price change percentage")

class HistoricalPrice(BaseModel):
    """Historical price point."""
    timestamp: datetime = Field(..., description="Price timestamp")
    price: float = Field(..., description="Index price at timestamp")
    volume: float = Field(default=0.0, description="Trading volume")

class HistoricalPriceResponse(BaseModel):
    """Historical price data response."""
    index_id: str = Field(..., description="Index identifier")
    interval: IntervalType = Field(..., description="Data interval")
    data: List[HistoricalPrice] = Field(..., description="Historical price points")
    start_date: datetime = Field(..., description="Query start date")
    end_date: datetime = Field(..., description="Query end date")

class VolumeData(BaseModel):
    """Volume data for an index."""
    index_id: str = Field(..., description="Index identifier")
    volume_24h: float = Field(..., description="24-hour trading volume")
    volume_7d: float = Field(..., description="7-day trading volume")
    volume_change: float = Field(default=0.0, description="Volume change percentage")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Data timestamp")

class IndexListResponse(BaseModel):
    """Response model for listing all indexes."""
    indexes: List[IndexMetadata] = Field(..., description="List of available indexes")
    total_count: int = Field(..., description="Total number of indexes")

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

# Muesliswap API response models
class MuesliswapTokenAddress(BaseModel):
    """Muesliswap token address structure."""
    name: str
    policyId: str

class MuesliswapVolumeData(BaseModel):
    """Muesliswap volume data structure."""
    base: float
    quote: float

class MuesliswapSupplyInfo(BaseModel):
    """Muesliswap token supply information."""
    total: str
    circulating: Optional[str] = None

class MuesliswapTokenInfo(BaseModel):
    """Muesliswap token information."""
    symbol: Optional[str] = None
    decimalPlaces: int
    status: str
    image: Optional[str] = None
    address: MuesliswapTokenAddress
    categories: List[str] = []
    supply: MuesliswapSupplyInfo

class MuesliswapMarketPrice(BaseModel):
    """Muesliswap market price data."""
    volume: MuesliswapVolumeData
    volumeChange: MuesliswapVolumeData
    volumeAggregator: Dict = {}
    volumeTotal: MuesliswapVolumeData
    price: float
    priceChange: Dict[str, float]
    price10d: List[float] = []
    quoteDecimalPlaces: int
    baseDecimalPlaces: int
    quoteAddress: MuesliswapTokenAddress
    baseAddress: MuesliswapTokenAddress
    marketCap: float

class MuesliswapTokenListItem(BaseModel):
    """Individual token item from MuesliSwap token list API."""
    info: MuesliswapTokenInfo
    price: MuesliswapMarketPrice

class MuesliswapTokenListResponse(BaseModel):
    """Response from MuesliSwap token list API."""
    count: int
    offset: int
    limit: int
    items: List[MuesliswapTokenListItem]

class MuesliswapPriceData(BaseModel):
    """Muesliswap price response structure."""
    baseDecimalPlaces: int
    quoteDecimalPlaces: int
    baseAddress: MuesliswapTokenAddress
    quoteAddress: MuesliswapTokenAddress
    price: float
    marketCap: float
    volume: MuesliswapVolumeData
    volume7d: MuesliswapVolumeData
    volumeChange: MuesliswapVolumeData
    priceChange: Dict[str, float]
    volumeAggregator: MuesliswapVolumeData
    volumeTotal: MuesliswapVolumeData
