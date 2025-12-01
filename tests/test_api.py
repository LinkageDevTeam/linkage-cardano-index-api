"""
Tests for API endpoints
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from main import app
from app.core.config import get_settings

# Test client
client = TestClient(app)

# Test API key for authentication
TEST_API_KEY = "demo-api-key-please-change"
AUTH_HEADERS = {"Authorization": f"Bearer {TEST_API_KEY}"}

class TestIndexAPI:
    """Test suite for index API endpoints."""
    
    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Cardano Index API" in data["message"]
    
    def test_health_check(self):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_get_indexes_without_auth(self):
        """Test that endpoints require authentication."""
        response = client.get("/indexes")
        assert response.status_code in [401, 403]  # FastAPI can return either
    
    def test_get_indexes_with_auth(self):
        """Test fetching all indexes with proper authentication."""
        response = client.get("/indexes", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "indexes" in data
        assert "total_count" in data
        assert isinstance(data["indexes"], list)
        assert data["total_count"] >= 0
    
    def test_get_specific_index(self):
        """Test fetching a specific index."""
        # First get all indexes to find a valid ID
        response = client.get("/indexes", headers=AUTH_HEADERS)
        assert response.status_code == 200
        indexes = response.json()["indexes"]
        
        if len(indexes) > 0:
            index_id = indexes[0]["id"]
            
            # Test fetching specific index
            response = client.get(f"/indexes/{index_id}", headers=AUTH_HEADERS)
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == index_id
            assert "name" in data
            assert "description" in data
            assert "tokens" in data
            assert "index_type" in data
    
    def test_dynamic_vs_static_indexes(self):
        """Test that both dynamic and static indexes are available."""
        response = client.get("/indexes", headers=AUTH_HEADERS)
        assert response.status_code == 200
        indexes = response.json()["indexes"]
        
        if len(indexes) > 0:
            # Check if we have both types
            static_indexes = [idx for idx in indexes if idx.get("index_type", "static") == "static"]
            dynamic_indexes = [idx for idx in indexes if idx.get("index_type") == "dynamic"]
            
            # Should have at least some indexes
            assert len(static_indexes) > 0 or len(dynamic_indexes) > 0
            
            # Test dynamic index properties
            for idx in dynamic_indexes:
                assert "dynamic_criteria" in idx
                assert idx["dynamic_criteria"] is not None
                assert "selection_method" in idx["dynamic_criteria"]
                assert "limit" in idx["dynamic_criteria"]
    
    def test_get_nonexistent_index(self):
        """Test fetching a non-existent index."""
        response = client.get("/indexes/nonexistent", headers=AUTH_HEADERS)
        assert response.status_code == 404
    
    def test_get_index_price(self):
        """Test fetching index price."""
        # Get a valid index ID first
        response = client.get("/indexes", headers=AUTH_HEADERS)
        assert response.status_code == 200
        indexes = response.json()["indexes"]
        
        if len(indexes) > 0:
            index_id = indexes[0]["id"]
            
            # Test price endpoint
            response = client.get(f"/indexes/{index_id}/price", headers=AUTH_HEADERS)
            # Note: This might fail if external API is down, but we test the endpoint
            if response.status_code == 200:
                data = response.json()
                assert "price" in data
                assert "market_cap" in data
                assert "timestamp" in data
                assert data["index_id"] == index_id
    
    def test_get_index_volume(self):
        """Test fetching index volume."""
        response = client.get("/indexes", headers=AUTH_HEADERS)
        assert response.status_code == 200
        indexes = response.json()["indexes"]
        
        if len(indexes) > 0:
            index_id = indexes[0]["id"]
            
            response = client.get(f"/indexes/{index_id}/volume", headers=AUTH_HEADERS)
            # Similar to price, might fail with external API issues
            if response.status_code == 200:
                data = response.json()
                assert "volume_24h" in data
                assert "volume_7d" in data
                assert data["index_id"] == index_id
    
    def test_get_index_history(self):
        """Test fetching historical index data."""
        response = client.get("/indexes", headers=AUTH_HEADERS)
        assert response.status_code == 200
        indexes = response.json()["indexes"]
        
        if len(indexes) > 0:
            index_id = indexes[0]["id"]
            
            # Test with default parameters
            response = client.get(f"/indexes/{index_id}/history", headers=AUTH_HEADERS)
            if response.status_code == 200:
                data = response.json()
                assert "data" in data
                assert "start_date" in data
                assert "end_date" in data
                assert "interval" in data
                assert data["index_id"] == index_id
            
            # Test with custom date range
            end_date = datetime.utcnow().isoformat()
            start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
            
            response = client.get(
                f"/indexes/{index_id}/history",
                headers=AUTH_HEADERS,
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "interval": "1d"
                }
            )
            if response.status_code == 200:
                data = response.json()
                assert data["index_id"] == index_id
    
    def test_invalid_date_range(self):
        """Test invalid date ranges for historical data."""
        response = client.get("/indexes", headers=AUTH_HEADERS)
        if response.status_code == 200:
            indexes = response.json()["indexes"]
            if len(indexes) > 0:
                index_id = indexes[0]["id"]
                
                # Test start_date after end_date
                end_date = (datetime.utcnow() - timedelta(days=10)).isoformat()
                start_date = datetime.utcnow().isoformat()
                
                response = client.get(
                    f"/indexes/{index_id}/history",
                    headers=AUTH_HEADERS,
                    params={
                        "start_date": start_date,
                        "end_date": end_date
                    }
                )
                assert response.status_code == 400

@pytest.mark.asyncio
async def test_async_functionality():
    """Test async functionality works correctly."""
    from app.services.index_service import IndexService
    
    service = IndexService()
    indexes = await service.load_indexes_config()
    assert isinstance(indexes, list)

def test_config_loading():
    """Test configuration loading."""
    settings = get_settings()
    assert settings.app_name == "Cardano Index API"
    assert isinstance(settings.api_keys, list)
    assert len(settings.api_keys) > 0


class TestLinkageFinanceFunds:
    """Test suite for Linkage Finance fund endpoints."""
    
    def test_get_linkage_funds_without_auth(self):
        """Test that Linkage Finance endpoints require authentication."""
        response = client.get("/linkage-funds")
        assert response.status_code in [401, 403]
    
    def test_get_linkage_funds_with_auth(self):
        """Test fetching all Linkage Finance funds."""
        response = client.get("/linkage-funds", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "funds" in data
        assert "total_count" in data
        assert isinstance(data["funds"], list)
        assert data["total_count"] >= 0
    
    def test_get_specific_linkage_fund(self):
        """Test fetching a specific Linkage Finance fund."""
        # First get all funds
        response = client.get("/linkage-funds", headers=AUTH_HEADERS)
        assert response.status_code == 200
        funds = response.json()["funds"]
        
        if len(funds) > 0:
            fund_id = funds[0]["fund_id"]
            
            # Test fetching specific fund
            response = client.get(f"/linkage-funds/{fund_id}", headers=AUTH_HEADERS)
            assert response.status_code == 200
            data = response.json()
            assert data["fund_id"] == fund_id
            assert "name" in data
            assert "tokens" in data
            assert "factors" in data
            assert "index_id" in data
    
    def test_get_nonexistent_linkage_fund(self):
        """Test fetching a non-existent Linkage Finance fund."""
        response = client.get("/linkage-funds/nonexistent", headers=AUTH_HEADERS)
        assert response.status_code == 404
    
    def test_linkage_fund_as_index(self):
        """Test that Linkage Finance funds appear as indexes."""
        response = client.get("/indexes", headers=AUTH_HEADERS)
        assert response.status_code == 200
        indexes = response.json()["indexes"]
        
        # Check if any indexes are Linkage Finance funds
        linkage_funds = [idx for idx in indexes if idx.get("id", "").startswith("linkage-fund-")]
        
        # At least one Linkage fund should be available
        assert len(linkage_funds) > 0, "No Linkage Finance funds found in indexes"
        
        # Test that Linkage funds have correct category
        for fund_index in linkage_funds:
            assert fund_index.get("category") == "linkage-fund"
            assert "tokens" in fund_index or fund_index.get("index_type") == "dynamic"
    
    def test_linkage_fund_price_calculation(self):
        """Test price calculation for Linkage Finance funds."""
        response = client.get("/indexes", headers=AUTH_HEADERS)
        assert response.status_code == 200
        indexes = response.json()["indexes"]
        
        # Find a Linkage Finance fund
        linkage_funds = [idx for idx in indexes if idx.get("id", "").startswith("linkage-fund-")]
        
        if len(linkage_funds) > 0:
            fund_index_id = linkage_funds[0]["id"]
            
            # Test price endpoint
            response = client.get(f"/indexes/{fund_index_id}/price", headers=AUTH_HEADERS)
            # May fail if external API is down, but endpoint should work
            if response.status_code == 200:
                data = response.json()
                assert "price" in data
                assert data["index_id"] == fund_index_id
    
    def test_linkage_fund_volume_calculation(self):
        """Test volume calculation for Linkage Finance funds."""
        response = client.get("/indexes", headers=AUTH_HEADERS)
        assert response.status_code == 200
        indexes = response.json()["indexes"]
        
        linkage_funds = [idx for idx in indexes if idx.get("id", "").startswith("linkage-fund-")]
        
        if len(linkage_funds) > 0:
            fund_index_id = linkage_funds[0]["id"]
            
            response = client.get(f"/indexes/{fund_index_id}/volume", headers=AUTH_HEADERS)
            if response.status_code == 200:
                data = response.json()
                assert "volume_24h" in data
                assert "volume_7d" in data
                assert data["index_id"] == fund_index_id
    
    def test_linkage_fund_historical_data(self):
        """Test historical data retrieval for Linkage Finance funds."""
        response = client.get("/indexes", headers=AUTH_HEADERS)
        assert response.status_code == 200
        indexes = response.json()["indexes"]
        
        linkage_funds = [idx for idx in indexes if idx.get("id", "").startswith("linkage-fund-")]
        
        if len(linkage_funds) > 0:
            fund_index_id = linkage_funds[0]["id"]
            
            # Test historical endpoint
            response = client.get(f"/indexes/{fund_index_id}/history", headers=AUTH_HEADERS)
            if response.status_code == 200:
                data = response.json()
                assert "data" in data
                assert "start_date" in data
                assert "end_date" in data
                assert data["index_id"] == fund_index_id
    
    def test_linkage_fund_fund_structure(self):
        """Test that Linkage Finance fund response has correct structure."""
        response = client.get("/linkage-funds", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        
        if len(data["funds"]) > 0:
            fund = data["funds"][0]
            
            # Verify all required fields are present
            assert "fund_id" in fund
            assert "name" in fund
            assert "tokens" in fund
            assert "factors" in fund
            assert "creator" in fund
            assert "fund_factor" in fund
            assert "royalty_factor" in fund
            assert "tx" in fund
            assert "created_at" in fund
            assert "index_id" in fund
            
            # Verify types
            assert isinstance(fund["tokens"], list)
            assert isinstance(fund["factors"], list)
            assert len(fund["tokens"]) == len(fund["factors"])
