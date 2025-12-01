"""
API routes for Linkage Finance fund operations
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from datetime import datetime

from app.services.linkage_finance import LinkageFinanceService
from app.services.index_service import IndexService
from app.models.schemas import IndexListResponse
from app.core.auth import verify_api_key
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
linkage_service = LinkageFinanceService()
index_service = IndexService()

@router.get(
    "",
    summary="Get all Linkage Finance funds",
    description="Retrieve a list of all Linkage Finance funds created by users"
)
async def get_linkage_funds(
    api_key: str = Depends(verify_api_key)
):
    """Get all Linkage Finance funds as indexes."""
    try:
        funds = await linkage_service.get_all_funds()
        indexes = [fund.to_index_metadata() for fund in funds]
        return {
            "funds": [
                {
                    "fund_id": fund.fund_id,
                    "name": fund.name,
                    "tokens": fund.tokens,
                    "factors": fund.factors,
                    "creator": fund.creator,
                    "fund_factor": fund.fund_factor,
                    "royalty_factor": fund.royalty_factor,
                    "tx": fund.tx,
                    "created_at": fund.created_at.isoformat(),
                    "index_id": f"linkage-fund-{fund.fund_id}"
                }
                for fund in funds
            ],
            "total_count": len(funds)
        }
    except Exception as e:
        logger.error(f"Failed to fetch Linkage Finance funds: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Linkage Finance funds: {str(e)}"
        )

@router.get(
    "/{fund_id}",
    summary="Get specific Linkage Finance fund",
    description="Retrieve details for a specific Linkage Finance fund by ID"
)
async def get_linkage_fund(
    fund_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get details for a specific Linkage Finance fund."""
    try:
        fund = await linkage_service.get_fund_by_id(fund_id)
        if not fund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Linkage Finance fund '{fund_id}' not found"
            )
        
        index_metadata = fund.to_index_metadata()
        
        return {
            "fund_id": fund.fund_id,
            "name": fund.name,
            "tokens": fund.tokens,
            "factors": fund.factors,
            "creator": fund.creator,
            "fund_factor": fund.fund_factor,
            "royalty_factor": fund.royalty_factor,
            "tx": fund.tx,
            "created_at": fund.created_at.isoformat(),
            "index_id": index_metadata.id,
            "index_metadata": index_metadata.dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch Linkage Finance fund {fund_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fund: {str(e)}"
        )

