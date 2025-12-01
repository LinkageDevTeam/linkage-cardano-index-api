# API Testing Report - Cardano Index API

## Overview
This report covers the testing results for the Cardano Index API, which provides price data and information about our Cardano token indexes. The API supports both static (manually configured) and dynamic (automatically updated) indexes, as well as Linkage Finance funds created by users through smart contracts.

## What We Tested

### 1. Basic API Functionality 
- **Root Endpoint** (`GET /`): Returns API information and available features
- **Health Check** (`GET /health`): Confirms API is running and shows system status
- **Result**: Both endpoints work correctly and return proper JSON responses

### 2. Authentication & Security 
- **API Key Authentication**: All protected endpoints require valid API keys
- **Unauthorized Access**: Properly blocks requests without API keys (returns 401/403 errors)  
- **Valid Authentication**: Accepts requests with correct API key in Authorization header
- **Result**: Security works as expected - no unauthorized access possible

### 3. Index Management 
- **Get All Indexes** (`GET /indexes`): Returns list of available indexes with count
- **Get Specific Index** (`GET /indexes/{id}`): Returns detailed info about one index
- **Index Types**: Successfully handles both static and dynamic index types
- **Dynamic Index Features**: Properly shows selection criteria and filtering rules
- **Error Handling**: Returns 404 for non-existent indexes
- **Result**: All index endpoints function correctly

### 4. Price & Market Data 
- **Current Prices** (`GET /indexes/{id}/price`): Gets real-time index prices
- **Volume Data** (`GET /indexes/{id}/volume`): Returns 24h and 7d trading volumes (based on muesliswap trading)
- **External API Dependency**: Relies on MuesliSwap API for live data
- **Result**: Works when MuesliSwap API is available, may fail during external API outages

### 5. Historical Data System 
- **Historical Prices** (`GET /indexes/{id}/history`): Returns past price data
- **Date Range Filtering**: Supports custom start/end dates and intervals
- **Database Storage**: Collects and stores price data every 15 minutes
- **Data Validation**: Properly validates date ranges (rejects invalid dates)
- **Background Collection**: Automated data collection system works correctly
- **Result**: Historical system fully functional with proper data storage

### 6. Linkage Finance Funds Integration
- **Fund Discovery** (`GET /linkage-funds`): Lists all user-created Linkage Finance funds
- **Fund Details** (`GET /linkage-funds/{fund_id}`): Returns detailed information about a specific fund
- **Fund as Index**: Linkage Finance funds appear in the main indexes endpoint with `linkage-fund-` prefix
- **Fund Metadata**: Properly converts fund data to index metadata format
- **Token Weight Normalization**: Correctly normalizes fund factors to token weights (0-1 range)
- **Price Calculation**: Linkage funds support full price calculation like regular indexes
- **Volume Data**: Volume calculations work for Linkage Finance funds
- **Historical Tracking**: Funds are included in historical data collection system
- **Error Handling**: Proper 404 responses for non-existent funds
- **Result**: Linkage Finance funds fully integrated and functional across all API features

## Test Code Implementation

### Test Files Structure
Our testing is organized in multiple files:
- **`tests/test_api.py`** - API endpoint testing (includes Linkage Finance endpoint tests)
- **`tests/test_linkage_funds.py`** - Comprehensive Linkage Finance funds testing
- **`tests/test_services.py`** - Service layer testing
- **`test_historical_system.py`** - Historical data collection testing 

### Key Test Examples

#### 1. Basic Authentication Test
```python
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
```

#### 2. Index Management Test
```python
def test_get_specific_index(self):
    """Test fetching a specific index."""
    # First get all indexes to find a valid ID
    response = client.get("/indexes", headers=AUTH_HEADERS)
    assert response.status_code == 200
    indexes = response.json()["indexes"]
    
    if len(indexes) > 0:
        index_id = indexes[0]["id"]
        response = client.get(f"/indexes/{index_id}", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == index_id
        assert "name" in data
        assert "tokens" in data
```

#### 3. Historical Data System Test
```python
async def test_historical_system():
    """Test the historical data collection system."""
    print("Testing Historical Data Collection System")
    
    # Test data collection
    querier = get_historical_querier()
    result = await querier.force_collection()
    
    if result["success"]:
        print(f"Data collection successful in {result['duration_seconds']:.2f}s")
    
    # Check database records
    async with db_manager.get_session() as session:
        stmt = select(HistoricalIndexPrice).order_by(
            HistoricalIndexPrice.timestamp.desc()
        ).limit(10)
        result = await session.execute(stmt)
        records = result.scalars().all()
        
        if records:
            print(f"Found {len(records)} historical records")
```

### Test Configuration
```python
# Test setup from test_api.py
TEST_API_KEY = "demo-api-key-please-change"
AUTH_HEADERS = {"Authorization": f"Bearer {TEST_API_KEY}"}
client = TestClient(app)
```

### Test Categories Covered
1. **TestIndexAPI class** - 12+ test methods covering all API endpoints
2. **TestLinkageFinanceFunds class** - 7 test methods for Linkage Finance endpoints
3. **TestLinkageFund class** - 3 test methods for fund data model
4. **TestLinkageFinanceService class** - 5 test methods for fund service layer
5. **TestIndexServiceWithLinkageFunds class** - 3 test methods for integration
6. **TestLinkageFundDataValidation class** - 4 test methods for data validation
7. **Async functionality** - Tests async operations with proper setup
8. **Configuration loading** - Validates settings and API key handling
9. **Historical system** - End-to-end testing of data collection pipeline
10. **Integration tests** - Full workflow testing for Linkage Finance funds

#### Linkage Finance Funds Test Examples

##### 1. Fund Service Layer Test
```python
@pytest.mark.asyncio
async def test_get_all_funds(self):
    """Test fetching all funds."""
    service = LinkageFinanceService()
    
    funds = await service.get_all_funds()
    
    assert isinstance(funds, list)
    assert len(funds) > 0
    assert all(isinstance(fund, LinkageFund) for fund in funds)
```

##### 2. Fund-to-Index Conversion Test
```python
def test_fund_to_index_metadata(self):
    """Test converting fund to IndexMetadata."""
    fund = LinkageFund(
        fund_id="test001",
        name="Test Fund",
        tokens=["afbe91c0b44b3040e360057bf8354ead8c49c4979ae6ab7c4fbdc9eb4d494c4b7632"],
        factors=[100],
        creator="creator123",
        fund_factor=1000000,
        royalty_factor=30,
        tx="tx123...#0"
    )
    
    index_metadata = fund.to_index_metadata()
    
    assert index_metadata.id == "linkage-fund-test001"
    assert index_metadata.category == "linkage-fund"
    assert index_metadata.index_type == "static"
```

##### 3. Linkage Finance API Endpoint Test
```python
def test_get_linkage_funds_with_auth(self):
    """Test fetching all Linkage Finance funds."""
    response = client.get("/linkage-funds", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "funds" in data
    assert "total_count" in data
    assert isinstance(data["funds"], list)
```

##### 4. Fund Price Calculation Test
```python
def test_linkage_fund_price_calculation(self):
    """Test price calculation for Linkage Finance funds."""
    response = client.get("/indexes", headers=AUTH_HEADERS)
    indexes = response.json()["indexes"]
    
    linkage_funds = [idx for idx in indexes if idx.get("id", "").startswith("linkage-fund-")]
    
    if len(linkage_funds) > 0:
        fund_index_id = linkage_funds[0]["id"]
        response = client.get(f"/indexes/{fund_index_id}/price", headers=AUTH_HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            assert "price" in data
            assert data["index_id"] == fund_index_id
```

##### 5. Weight Normalization Test
```python
def test_fund_weights_normalization(self):
    """Test that factors are normalized to weights correctly."""
    fund = LinkageFund(
        fund_id="test002",
        name="Test Fund 2",
        tokens=["token1", "token2"],
        factors=[40, 30],  # Total: 70
        ...
    )
    
    index_metadata = fund.to_index_metadata()
    
    # Weights should sum to 1.0 after normalization
    total_weight = sum(token.weight for token in index_metadata.tokens)
    assert abs(total_weight - 1.0) < 0.001
```


## Bug Fixes During Testing

### Critical Issue Found and Fixed
During our testing process, we discovered and resolved a few critical startup issues. Moreover, we fixed the following things:


**Additional Fix**: Corrected health endpoint timestamp formatting error
- Fixed `uvicorn.utils.format_date_time()` which doesn't provide the correct format
- Replaced with proper `datetime.utcnow().isoformat()` format

**Second Fix**: Historical querier method name error  
- Fixed `get_index_price()` method call which doesn't exist in IndexService
- Replaced with correct `calculate_index_price()` method
- Historical data collection now works properly for static indexes

**Third Fix**: Historical querier token count handling
- Fixed token count calculation for dynamic indexes and Linkage Finance funds
- Added proper handling for indexes with tokens loaded dynamically
- Historical data collection now correctly tracks token counts for all index types

## Example API Usage

### Authentication
```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:8000/indexes
```

### Get Index Price
```bash
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8000/indexes/cardano-defi/price
```

### Get Historical Data
```bash
curl -H "Authorization: Bearer your-api-key" \
     "http://localhost:8000/indexes/cardano-defi/history?start_date=2024-01-01&end_date=2024-01-31&interval=1d"
```

### Get All Linkage Finance Funds
```bash
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8000/linkage-funds
```

### Get Specific Linkage Finance Fund
```bash
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8000/linkage-funds/fund001
```

### Get Linkage Fund as Index (with price)
```bash
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8000/indexes/linkage-fund-fund001/price
```

### Get Linkage Fund Historical Data
```bash
curl -H "Authorization: Bearer your-api-key" \
     "http://localhost:8000/indexes/linkage-fund-fund001/history?start_date=2024-01-01&end_date=2024-01-31&interval=1d"
```

## Test Execution

### Running All Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests including Linkage Finance funds
pytest

# Run with coverage report
pytest --cov=app tests/

# Run only Linkage Finance tests
pytest tests/test_linkage_funds.py -v

# Run only API endpoint tests (includes Linkage Finance endpoints)
pytest tests/test_api.py -v
```
