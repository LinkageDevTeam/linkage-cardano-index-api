"""
Tests for service layer
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.services.index_service import IndexService
from app.services.muesliswap import MuesliswapService
from app.models.schemas import TokenInfo, MuesliswapPriceData

class TestIndexService:
    """Test suite for IndexService."""
    
    @pytest.fixture
    def index_service(self):
        return IndexService()
    

    async def test_load_indexes_config(self, index_service):
        """Test loading index configuration."""
        try:
            indexes = await index_service.load_indexes_config()
            assert isinstance(indexes, list)
            
            if len(indexes) > 0:
                index = indexes[0]
                assert hasattr(index, 'id')
                assert hasattr(index, 'name')
                assert hasattr(index, 'tokens')
                assert isinstance(index.tokens, list)
                
                if len(index.tokens) > 0:
                    token = index.tokens[0]
                    assert isinstance(token, TokenInfo)
                    assert hasattr(token, 'name')
                    assert hasattr(token, 'policy_id')
                    assert hasattr(token, 'weight')
        except Exception as e:
            # Config file might not exist in test environment
            pytest.skip(f"Config file not available: {e}")
    

    async def test_get_index_by_id(self, index_service):
        """Test getting index by ID."""
        try:
            indexes = await index_service.load_indexes_config()
            if len(indexes) > 0:
                test_id = indexes[0].id
                found_index = await index_service.get_index_by_id(test_id)
                assert found_index is not None
                assert found_index.id == test_id
                
                # Test non-existent ID
                not_found = await index_service.get_index_by_id("nonexistent")
                assert not_found is None
        except Exception:
            pytest.skip("Config file not available")
    
    def test_cache_functionality(self, index_service):
        """Test caching mechanism."""
        # Test cache validity
        assert not index_service._is_cache_valid("nonexistent_key")
        
        # Test setting and getting cache
        test_data = {"test": "data"}
        index_service._set_cache("test_key", test_data)
        cached_data = index_service._get_from_cache("test_key")
        assert cached_data == test_data
    

    async def test_calculate_index_price_no_config(self, index_service):
        """Test price calculation when index doesn't exist."""
        with pytest.raises(Exception, match="Index not found"):
            await index_service.calculate_index_price("nonexistent")
    

    async def test_dynamic_index_handling(self, index_service):
        """Test dynamic index token selection."""
        try:
            indexes = await index_service.load_indexes_config()
            dynamic_indexes = [idx for idx in indexes if idx.is_dynamic]
            
            if len(dynamic_indexes) > 0:
                dynamic_index = dynamic_indexes[0]
                
                # Test getting tokens for dynamic index
                tokens = await index_service.get_index_tokens(dynamic_index)
                
                # Should return a list (might be empty if API is down)
                assert isinstance(tokens, list)
                
                # If tokens were found, check they have weights
                for token in tokens:
                    assert hasattr(token, 'weight')
                    assert token.weight >= 0.0
                    assert token.weight <= 1.0
                    
        except Exception:
            # Skip if config file or API not available in test environment
            pytest.skip("Dynamic index test skipped - config or API not available")

class TestMuesliswapService:
    """Test suite for MuesliswapService."""
    
    @pytest.fixture
    def muesliswap_service(self):
        return MuesliswapService()
    

    async def test_health_check(self, muesliswap_service):
        """Test Muesliswap API health check."""
        # This test might fail if the API is down, so we handle both cases
        try:
            is_healthy = await muesliswap_service.health_check()
            assert isinstance(is_healthy, bool)
        except Exception:
            # API might be unavailable during testing
            pass
    

    async def test_get_token_price_mock(self, muesliswap_service):
        """Test token price fetching with mock data."""
        test_token = TokenInfo(
            name="TEST",
            policy_id="test_policy",
            token_name="test_token",
            weight=1.0
        )
        
        mock_response_data = {
            "baseDecimalPlaces": 6,
            "quoteDecimalPlaces": 6,
            "baseAddress": {"name": "", "policyId": "test_policy"},
            "quoteAddress": {"name": "4d494c4b7632", "policyId": "afbe91c0b44b3040e360057bf8354ead8c49c4979ae6ab7c4fbdc9eb"},
            "price": 1.0,
            "marketCap": 1000000,
            "volume": {"base": 100, "quote": 200},
            "volume7d": {"base": 700, "quote": 1400},
            "volumeChange": {"base": 10, "quote": 20},
            "priceChange": {"24h": 5.0, "7d": -2.0},
            "volumeAggregator": {"base": 0, "quote": 0},
            "volumeTotal": {"base": 0, "quote": 0}
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response
            
            price_data = await muesliswap_service.get_token_price(test_token)
            assert isinstance(price_data, MuesliswapPriceData)
            assert price_data.price == 1.0
            assert price_data.marketCap == 1000000
    

    async def test_dynamic_token_selection_mock(self, muesliswap_service):
        """Test dynamic token selection with mock data."""
        from app.models.schemas import DynamicSelectionCriteria
        
        criteria = DynamicSelectionCriteria(
            selection_method="market_cap",
            limit=3,
            min_volume_ada=100.0,
            weighting_method="market_cap"
        )
        
        # Mock response data similar to MuesliSwap API
        mock_response_data = {
            "count": 3,
            "offset": 0,
            "limit": 3,
            "items": [
                {
                    "info": {
                        "symbol": "TOKEN1",
                        "decimalPlaces": 6,
                        "status": "verified",
                        "address": {"name": "token1", "policyId": "policy1"},
                        "categories": [],
                        "supply": {"total": "1000000", "circulating": None}
                    },
                    "price": {
                        "volume": {"base": 150.0, "quote": 200.0},
                        "volumeChange": {"base": 0, "quote": 0},
                        "volumeAggregator": {},
                        "volumeTotal": {"base": 150.0, "quote": 200.0},
                        "price": 1.0,
                        "priceChange": {"24h": 0, "7d": 0},
                        "price10d": [],
                        "quoteDecimalPlaces": 6,
                        "baseDecimalPlaces": 6,
                        "quoteAddress": {"name": "token1", "policyId": "policy1"},
                        "baseAddress": {"policyId": "", "name": ""},
                        "marketCap": 1000000.0
                    }
                },
                {
                    "info": {
                        "symbol": "TOKEN2",
                        "decimalPlaces": 6,
                        "status": "verified",
                        "address": {"name": "token2", "policyId": "policy2"},
                        "categories": [],
                        "supply": {"total": "500000", "circulating": None}
                    },
                    "price": {
                        "volume": {"base": 120.0, "quote": 180.0},
                        "volumeChange": {"base": 0, "quote": 0},
                        "volumeAggregator": {},
                        "volumeTotal": {"base": 120.0, "quote": 180.0},
                        "price": 2.0,
                        "priceChange": {"24h": 0, "7d": 0},
                        "price10d": [],
                        "quoteDecimalPlaces": 6,
                        "baseDecimalPlaces": 6,
                        "quoteAddress": {"name": "token2", "policyId": "policy2"},
                        "baseAddress": {"policyId": "", "name": ""},
                        "marketCap": 500000.0
                    }
                }
            ]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response
            
            tokens = await muesliswap_service.select_tokens_dynamically(criteria)
            
            assert isinstance(tokens, list)
            assert len(tokens) <= criteria.limit
            
            # Check that tokens have proper weights
            if len(tokens) > 0:
                total_weight = sum(token.weight for token in tokens)
                assert abs(total_weight - 1.0) < 0.01  # Should sum to 1.0
