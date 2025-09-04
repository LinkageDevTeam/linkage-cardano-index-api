"""
API routes for index operations
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from datetime import datetime, timedelta

from app.models.schemas import (
    IndexListResponse, IndexMetadata, PriceData, 
    HistoricalPriceResponse, VolumeData, IntervalType,
    HistoricalPrice, ErrorResponse
)
from app.services.index_service import IndexService
from app.core.auth import verify_api_key
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
index_service = IndexService()

@router.get(
    "",
    response_model=IndexListResponse,
    summary="Get all available indexes",
    description="Retrieve a list of all configured cryptocurrency indexes with their metadata"
)
async def get_indexes(
    api_key: str = Depends(verify_api_key)
) -> IndexListResponse:
    """Get all available indexes with their metadata."""
    try:
        indexes = await index_service.get_all_indexes()
        return IndexListResponse(
            indexes=indexes,
            total_count=len(indexes)
        )
    except Exception as e:
        logger.error(f"Failed to fetch indexes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch indexes: {str(e)}"
        )

@router.get(
    "/{index_id}",
    response_model=IndexMetadata,
    summary="Get specific index metadata",
    description="Retrieve detailed metadata for a specific index by its ID"
)
async def get_index_metadata(
    index_id: str,
    api_key: str = Depends(verify_api_key)
) -> IndexMetadata:
    """Get metadata for a specific index."""
    try:
        index = await index_service.get_index_by_id(index_id)
        if not index:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Index '{index_id}' not found"
            )
        
        # For dynamic indexes, populate the current tokens
        if index.is_dynamic:
            current_tokens = await index_service.get_index_tokens(index)
            # Create a copy to avoid modifying the original
            index_dict = index.dict()
            index_dict['tokens'] = current_tokens
            return IndexMetadata(**index_dict)
        
        return index
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch index {index_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch index: {str(e)}"
        )

@router.get(
    "/{index_id}/price",
    response_model=PriceData,
    summary="Get current index price",
    description="Get the latest calculated price for a specific index, including market cap and price changes"
)
async def get_index_price(
    index_id: str,
    api_key: str = Depends(verify_api_key)
) -> PriceData:
    """Get current price data for a specific index."""
    try:
        price_data = await index_service.calculate_index_price(index_id)
        return price_data
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Index '{index_id}' not found"
            )
        logger.error(f"Failed to calculate price for index {index_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate index price: {str(e)}"
        )

@router.get(
    "/{index_id}/history",
    response_model=HistoricalPriceResponse,
    summary="Get historical index prices",
    description="Retrieve historical price data for an index with configurable date range and intervals"
)
async def get_index_history(
    index_id: str,
    start_date: Optional[datetime] = Query(
        default=None,
        description="Start date for historical data (ISO format). Defaults to 30 days ago."
    ),
    end_date: Optional[datetime] = Query(
        default=None,
        description="End date for historical data (ISO format). Defaults to now."
    ),
    interval: IntervalType = Query(
        default=IntervalType.ONE_DAY,
        description="Time interval for data points"
    ),
    api_key: str = Depends(verify_api_key)
) -> HistoricalPriceResponse:
    """Get historical price data for a specific index."""
    try:
        # Set default dates if not provided
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        # Validate date range
        if start_date >= end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before end_date"
            )
        
        # Check if date range is reasonable (not too large)
        max_days = 365  # 1 year maximum
        if (end_date - start_date).days > max_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Date range cannot exceed {max_days} days"
            )
        
        historical_data = await index_service.get_historical_prices(
            index_id, start_date, end_date, interval
        )
        
        return HistoricalPriceResponse(
            index_id=index_id,
            interval=interval,
            data=historical_data,
            start_date=start_date,
            end_date=end_date
        )
        
    except HTTPException:
        raise
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Index '{index_id}' not found"
            )
        logger.error(f"Failed to get historical data for index {index_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve historical data: {str(e)}"
        )

@router.get(
    "/{index_id}/volume",
    response_model=VolumeData,
    summary="Get index volume data",
    description="Get trading volume information for a specific index over various time windows"
)
async def get_index_volume(
    index_id: str,
    api_key: str = Depends(verify_api_key)
) -> VolumeData:
    """Get volume data for a specific index."""
    try:
        volume_data = await index_service.get_index_volume(index_id)
        return volume_data
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Index '{index_id}' not found"
            )
        logger.error(f"Failed to get volume data for index {index_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve volume data: {str(e)}"
        )
