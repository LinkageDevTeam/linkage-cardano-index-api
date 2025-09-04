"""
Muesliswap API integration service for fetching token data
"""

import httpx
import asyncio
import logging
from typing import List, Dict, Optional
from app.core.config import get_settings
from app.models.schemas import (
    MuesliswapPriceData, TokenInfo, MuesliswapTokenListResponse,
    MuesliswapTokenListItem, DynamicSelectionCriteria
)

logger = logging.getLogger(__name__)

class MuesliswapService:
    """Service for interacting with the Muesliswap API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.muesliswap_base_url
        self.timeout = self.settings.muesliswap_timeout
    
    @staticmethod
    def normalize_price(price: float, quote_decimal_places: int, base_decimal_places: int) -> float:
        """
        Normalize price by adjusting for decimal places.
        
        Args:
            price: Raw price value
            quote_decimal_places: Quote token decimal places
            base_decimal_places: Base token decimal places
            
        Returns:
            float: Normalized price
        """
        decimal_adjustment = quote_decimal_places - base_decimal_places
        return price * (10 ** decimal_adjustment)
    
    @staticmethod
    def normalize_market_cap(market_cap: float, base_decimal_places: int) -> float:
        """
        Normalize market cap by adjusting for base decimal places to make number smaller.
        
        Args:
            market_cap: Raw market cap value
            base_decimal_places: Base token decimal places
            
        Returns:
            float: Normalized market cap
        """
        return market_cap * (10 ** (-base_decimal_places))
        
    async def get_token_list(self, limit: int = 50, offset: int = 0, sort_by: str = "marketCap") -> MuesliswapTokenListResponse:
        """
        Fetch tokens from Muesliswap list API.
        
        Args:
            limit: Number of tokens to fetch
            offset: Offset for pagination
            sort_by: Sort field ('marketCap', 'volume', etc.)
            
        Returns:
            MuesliswapTokenListResponse: Parsed response with token data (normalized)
        """
        url = f"{self.base_url}/list/v2"
        params = {
            "base-policy-id": "",
            "base-tokenname": "",
            "verified": "true",
            "limit": limit,
            "offset": offset,
            "search": "",
            "sort_by": sort_by,
            "desc": "true"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                token_response = MuesliswapTokenListResponse(**data)
                
                # Normalize price and market cap data for each token
                for item in token_response.items:
                    price_data = item.price
                    
                    # Normalize price using quote - base decimal places
                    price_data.price = self.normalize_price(
                        price_data.price,
                        price_data.quoteDecimalPlaces,
                        price_data.baseDecimalPlaces
                    )
                    
                    # Normalize market cap using negative base decimal places
                    price_data.marketCap = self.normalize_market_cap(
                        price_data.marketCap,
                        price_data.baseDecimalPlaces
                    )
                
                return token_response
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch token list from Muesliswap: {e}")
            raise Exception(f"Muesliswap API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching token list: {e}")
            raise
    
    async def get_token_price(self, token: TokenInfo, quote_policy_id: str = "", quote_token_name: str = "") -> MuesliswapPriceData:
        """
        Get price data for a specific token pair.
        
        Args:
            token: Token information
            quote_policy_id: Quote token policy ID (default: MILK v2)
            quote_token_name: Quote token name (default: MILK v2)
            
        Returns:
            MuesliswapPriceData: Price and market data (normalized)
        """
        url = f"{self.base_url}/price"

        # currently muesliswap is using quote token as base token and base token as quote token so we need to swap them
        params = {
            "base-policy-id": quote_policy_id,
            "base-tokenname": quote_policy_id,
            "quote-policy-id": token.policy_id,
            "quote-tokenname": token.token_name,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                price_data = MuesliswapPriceData(**data)
                
                # Normalize price using quote - base decimal places
                price_data.price = self.normalize_price(
                    price_data.price,
                    price_data.quoteDecimalPlaces,
                    price_data.baseDecimalPlaces
                )
                
                # Normalize market cap using negative base decimal places
                price_data.marketCap = self.normalize_market_cap(
                    price_data.marketCap,
                    price_data.baseDecimalPlaces
                )
                
                return price_data
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch price for {token.name}: {e}")
            raise Exception(f"Muesliswap API error for {token.name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching price for {token.name}: {e}")
            raise
    
    async def get_multiple_token_prices(self, tokens: List[TokenInfo]) -> Dict[str, MuesliswapPriceData]:
        """
        Fetch price data for multiple tokens concurrently.
        
        Args:
            tokens: List of tokens to fetch prices for
            
        Returns:
            Dict[str, MuesliswapPriceData]: Token prices keyed by token name (normalized)
        """
        tasks = []
        for token in tokens:
            task = asyncio.create_task(self.get_token_price(token))
            tasks.append((token.name, task))
        
        results = {}
        for token_name, task in tasks:
            try:
                price_data = await task
                results[token_name] = price_data
            except Exception as e:
                logger.warning(f"Failed to fetch price for {token_name}: {e}")
                # Continue with other tokens even if one fails
                continue
        
        return results
    
    async def select_tokens_dynamically(self, criteria: DynamicSelectionCriteria) -> List[TokenInfo]:
        """
        Select tokens dynamically based on criteria.
        
        Args:
            criteria: Selection criteria
            
        Returns:
            List[TokenInfo]: Selected tokens with calculated weights
        """
        try:
            # Determine sort method for API
            sort_by = "marketCap" if criteria.selection_method == "market_cap" else "volume"
            
            # Fetch tokens (get more than needed for filtering)
            fetch_limit = min(criteria.limit * 3, 100)  # Fetch 3x to account for filtering
            token_response = await self.get_token_list(
                limit=fetch_limit, 
                offset=0, 
                sort_by=sort_by
            )
            
            # Filter tokens based on criteria
            filtered_tokens = []
            for item in token_response.items:
                token_data = item.info
                price_data = item.price
                
                # Skip if no symbol
                if not token_data.symbol:
                    continue
                
                # Check exclusion list
                if token_data.symbol in criteria.exclude_tokens:
                    continue
                
                # Check volume filter (convert to ADA)
                total_volume_ada = price_data.volume.base + price_data.volume.quote
                if total_volume_ada < criteria.min_volume_ada:
                    continue
                
                # Check market cap filter
                if criteria.min_market_cap and price_data.marketCap < criteria.min_market_cap:
                    continue
                
                # Check categories if specified
                if criteria.include_categories and len(criteria.include_categories) > 0:
                    if not any(cat in token_data.categories for cat in criteria.include_categories):
                        continue
                
                # Create TokenInfo object
                token_info = TokenInfo(
                    name=token_data.symbol,
                    policy_id=token_data.address.policyId,
                    token_name=token_data.address.name,
                    weight=0.0,  # Will be calculated below
                    description=f"Market cap: {price_data.marketCap:.2f} ADA"
                )
                
                # Store market cap for weighting
                token_info._market_cap = price_data.marketCap
                filtered_tokens.append(token_info)
            
            # Limit to requested number
            selected_tokens = filtered_tokens[:criteria.limit]
            
            # Calculate weights based on weighting method
            if criteria.weighting_method == "equal":
                # Equal weighting
                weight = 1.0 / len(selected_tokens) if selected_tokens else 0.0
                for token in selected_tokens:
                    token.weight = weight
            elif criteria.weighting_method == "market_cap":
                # Market cap weighting
                total_market_cap = sum(getattr(token, '_market_cap', 0) for token in selected_tokens)
                if total_market_cap > 0:
                    for token in selected_tokens:
                        market_cap = getattr(token, '_market_cap', 0)
                        token.weight = market_cap / total_market_cap
                        # Clean up temporary attribute
                        delattr(token, '_market_cap')
            
            logger.info(f"Selected {len(selected_tokens)} tokens dynamically with {criteria.selection_method} method")
            return selected_tokens
            
        except Exception as e:
            logger.error(f"Failed to select tokens dynamically: {e}")
            raise Exception(f"Dynamic token selection error: {e}")
    
    async def health_check(self) -> bool:
        """
        Check if the Muesliswap API is responding.
        
        Returns:
            bool: True if API is healthy
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/list/v2", params={
                    "base-policy-id": "", 
                    "base-tokenname": "",
                    "verified": "true",
                    "limit": 1,
                    "offset": 0
                })
                return response.status_code == 200
        except:
            return False
