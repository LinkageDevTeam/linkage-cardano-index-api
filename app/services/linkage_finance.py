"""
Linkage Finance fund tracking service
Fetches and tracks funds created by users through Linkage Finance smart contracts
"""

import logging
import json
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import asyncio

from app.models.schemas import IndexMetadata, TokenInfo
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class LinkageFund:
    """Represents a Linkage Finance fund."""
    
    def __init__(
        self,
        fund_id: str,
        name: str,
        tokens: List[str],
        factors: List[int],
        creator: str,
        fund_factor: int,
        royalty_factor: int,
        tx: str,
        created_at: Optional[datetime] = None
    ):
        self.fund_id = fund_id
        self.name = name
        self.tokens = tokens
        self.factors = factors
        self.creator = creator
        self.fund_factor = fund_factor
        self.royalty_factor = royalty_factor
        self.tx = tx
        self.created_at = created_at or datetime.utcnow()
    
    def to_index_metadata(self) -> IndexMetadata:
        """Convert fund to IndexMetadata format."""
        # Normalize factors to weights (0-1 range)
        total_factor = sum(self.factors) if self.factors else 1
        weights = [f / total_factor for f in self.factors] if total_factor > 0 else []
        
        # Convert token IDs to TokenInfo objects
        token_infos = []
        for token_id, weight in zip(self.tokens, weights):
            # Token ID format: policy_id(56 chars) + token_name(remaining)
            if len(token_id) >= 56:
                policy_id = token_id[:56]
                token_name_hex = token_id[56:]
                
                # Try to get token symbol from name if possible
                try:
                    token_symbol = bytes.fromhex(token_name_hex).decode('utf-8', errors='ignore').strip('\x00')
                except:
                    token_symbol = token_name_hex[:8] if token_name_hex else "UNKNOWN"
                
                token_info = TokenInfo(
                    name=token_symbol,
                    policy_id=policy_id,
                    token_name=token_name_hex,
                    weight=weight,
                    description=f"Token from Linkage Finance fund {self.name}"
                )
                token_infos.append(token_info)
        
        return IndexMetadata(
            id=f"linkage-fund-{self.fund_id}",
            name=f"Linkage Fund: {self.name}",
            description=f"User-created index fund from Linkage Finance (Creator: {self.creator[:16]}...)",
            category="linkage-fund",
            methodology=f"Factor-weighted index fund with fund_factor={self.fund_factor}, royalty_factor={self.royalty_factor}",
            index_type="static",
            tokens=token_infos,
            base_value=100.0,
            created_at=self.created_at,
            updated_at=datetime.utcnow()
        )


class LinkageFinanceService:
    """Service for fetching and managing Linkage Finance funds."""
    
    def __init__(self):
        self.settings = get_settings()
        self._funds_cache: Optional[List[LinkageFund]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes cache
    
    def _is_cache_valid(self) -> bool:
        """Check if cached funds are still valid."""
        if self._funds_cache is None or self._cache_timestamp is None:
            return False
        from datetime import timedelta
        return (datetime.utcnow() - self._cache_timestamp).total_seconds() < self._cache_ttl_seconds
    
    async def _fetch_funds_from_blockchain(self) -> List[LinkageFund]:
        """
        Fetch funds from Linkage Finance smart contracts.
        This simulates querying the blockchain for fund UTXOs.
        
        In production, this would:
        1. Connect to Cardano blockchain
        2. Query UTXOs at the fund address
        3. Parse fund datums
        4. Convert to Fund objects
        
        For now, we'll use mock data that simulates real fund structure.
        """
        # Simulate async blockchain query delay
        await asyncio.sleep(0.1)
        
        # Mock funds - simulating real funds from the blockchain
        # These represent typical Linkage Finance funds that users create
        mock_funds = [
            LinkageFund(
                fund_id="fund001",
                name="Cardano DeFi Index Fund",
                tokens=[
                    "afbe91c0b44b3040e360057bf8354ead8c49c4979ae6ab7c4fbdc9eb4d494c4b7632",  # MILK
                    "29d222ce763455e3d7a09a665ce554f00ac89d2e99a1a83d267170c64d494e",  # MIN
                ],
                factors=[40, 30],
                creator="abc123def456",
                fund_factor=1000000,
                royalty_factor=30,
                tx="abc123...#0",
                created_at=datetime(2025, 1, 10, 10, 0, 0)
            ),
            LinkageFund(
                fund_id="fund002",
                name="Gaming Token Index",
                tokens=[
                    "a0028f350aaabe0545fdcb56b039bfb08e4bb4d8c4d7c3c7d481c235484f534b59",  # HOSKY
                    "279c909f348e533da5808898f87f9a14bb2c3dfbbacccd631d927a3f534e454b",  # SNEK
                ],
                factors=[50, 50],
                creator="xyz789ghi012",
                fund_factor=500000,
                royalty_factor=25,
                tx="def456...#0",
                created_at=datetime(2025, 1, 12, 14, 30, 0)
            ),
            LinkageFund(
                fund_id="fund003",
                name="Stablecoin Index",
                tokens=[
                    "afbe91c0b44b3040e360057bf8354ead8c49c4979ae6ab7c4fbdc9eb4d494c4b7632",  # MILK
                ],
                factors=[100],
                creator="mno345pqr678",
                fund_factor=2000000,
                royalty_factor=20,
                tx="ghi789...#0",
                created_at=datetime(2025, 1, 15, 9, 15, 0)
            ),
        ]
        
        # Try to load from local storage file if it exists
        funds_file = Path("data/linkage_funds.json")
        if funds_file.exists():
            try:
                with open(funds_file, 'r') as f:
                    stored_funds = json.load(f)
                
                funds = []
                for fund_data in stored_funds:
                    created_at = datetime.fromisoformat(fund_data['created_at']) if 'created_at' in fund_data else datetime.utcnow()
                    fund = LinkageFund(
                        fund_id=fund_data['fund_id'],
                        name=fund_data['name'],
                        tokens=fund_data['tokens'],
                        factors=fund_data['factors'],
                        creator=fund_data['creator'],
                        fund_factor=fund_data['fund_factor'],
                        royalty_factor=fund_data['royalty_factor'],
                        tx=fund_data['tx'],
                        created_at=created_at
                    )
                    funds.append(fund)
                
                if funds:
                    logger.info(f"Loaded {len(funds)} Linkage Finance funds from storage")
                    return funds
            except Exception as e:
                logger.warning(f"Failed to load funds from storage: {e}, using mock data")
        
        logger.info(f"Using {len(mock_funds)} mock Linkage Finance funds")
        return mock_funds
    
    async def get_all_funds(self) -> List[LinkageFund]:
        """Get all Linkage Finance funds."""
        if self._is_cache_valid():
            return self._funds_cache
        
        funds = await self._fetch_funds_from_blockchain()
        self._funds_cache = funds
        self._cache_timestamp = datetime.utcnow()
        
        return funds
    
    async def get_fund_by_id(self, fund_id: str) -> Optional[LinkageFund]:
        """Get a specific fund by ID."""
        funds = await self.get_all_funds()
        for fund in funds:
            if fund.fund_id == fund_id:
                return fund
        return None
    
    async def get_funds_as_indexes(self) -> List[IndexMetadata]:
        """Get all Linkage Finance funds as IndexMetadata objects."""
        funds = await self.get_all_funds()
        return [fund.to_index_metadata() for fund in funds]

