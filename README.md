# Cardano Index API

A comprehensive REST API that creates and tracks indexes for tokens in the Cardano ecosystem. This project provides real-time prices, historical data, and volume information for both **static** and **dynamic** Cardano token indexes.

**Live API Base URL:** `https://index-api.linkage.finance`

## Overview

The Cardano Index API is a first concept service that enables developers and applications to access aggregated token index data from the Cardano blockchain ecosystem. It provides:

- **Real-time index prices** calculated from live market data
- **Historical price tracking** with configurable time intervals
- **Volume analytics** for trading insights
- **Static indexes** with manually configured token weights
- **Dynamic indexes** that automatically update based on market conditions
- **Linkage Finance fund integration** for user-created investment funds
- **Comprehensive API documentation** with interactive Swagger UI

## What Does This Do?

This API helps you:
- Get current prices for Cardano token indexes
- View historical price data with charts  
- Check trading volume information
- Track both manual (static) and automated (dynamic) indexes
- Automatically select top tokens by market cap or volume
- Track Linkage Finance funds created by users
- Verify data accuracy and consistency with automated tools
- Build applications that depend on aggregated Cardano token market data

## Two Index Types: Static vs Dynamic

### Static Indexes
Pre-defined tokens with manually set weights - perfect for custom strategies.

### Dynamic Indexes  
Automatically select the best tokens based on live market data from [MuesliSwap](https://v2.muesliswap.com/markets?sortBy=volume1d&sortDir=desc). Filters by market cap, volume (minimum 100 ADA), and other criteria.

## Quick Start

### Using Docker (Recommended)

1. **Clone and run:**
Clone repository and then run
   ```bash
   docker-compose up -d
   ```

2. **Test it works:**
   ```bash
   curl -H "Authorization: Bearer demo-api-key-please-change" http://localhost:8000/indexes
   ```

### Manual Setup

1. **Install Python 3.11+ and dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the API:**
   ```bash
   python main.py
   ```

3. **Visit:** http://localhost:8000/docs for the interactive API documentation

## API Documentation

### Base URL
**Production Test API:** `https://index-api.linkage.finance`  
**Development:** `http://localhost:8000`

### Interactive Documentation
Once the API is running, access the interactive Swagger UI documentation at:
- **Swagger UI:** `https://index-api.linkage.finance/docs`
- **Health Check:** `https://index-api.linkage.finance/health`

The Swagger UI provides an interactive interface to test all endpoints directly from your browser.

## Authentication

All API endpoints (except `/` and `/health`) require authentication using an API key. Include your API key in the `Authorization` header using Bearer token authentication:

```bash
Authorization: Bearer your-api-key-here
```

### Getting an API Key

For development, you can use the default key: `demo-api-key-please-change`

### Example cURL Request

```bash
curl -H "Authorization: Bearer your-api-key-here" \
  https://index-api.linkage.finance/indexes
```

### Example JavaScript Fetch

```javascript
const response = await fetch('https://index-api.linkage.finance/indexes', {
  headers: {
    'Authorization': 'Bearer your-api-key-here'
  }
});
const data = await response.json();
```

### Example Python Requests

```python
import requests

headers = {'Authorization': 'Bearer your-api-key-here'}
response = requests.get('https://index-api.linkage.finance/indexes', headers=headers)
data = response.json()
```

## API Endpoints

### Core Endpoints

#### 1. Root Endpoint
```
GET /
```
Returns API information and available features. No authentication required.

**Example Response:**
```json
{
  "message": "Cardano Index API",
  "version": "1.0.0",
  "description": "API for accessing cryptocurrency index data from the Cardano ecosystem",
  "docs": "/docs",
  "features": {
    "static_indexes": "Pre-configured token indexes with fixed weights",
    "dynamic_indexes": "Automatically updated indexes based on market conditions",
    "historical_data": "Real historical price data collected every 15 minutes",
    "live_prices": "Real-time price calculations from MuesliSwap"
  }
}
```

#### 2. Health Check
```
GET /health
```
Returns API health status and system information. No authentication required.

**Example Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "database": "connected",
  "querier": {
    "enabled": true,
    "running": true,
    "interval_minutes": 15,
    "last_run": "2024-01-15T10:15:00Z",
    "success_rate": "98.5%"
  }
}
```

### Index Endpoints

#### 3. Get All Indexes
```
GET /indexes
```
Retrieve a list of all available indexes with their metadata.

**Response:**
```json
{
  "indexes": [
    {
      "id": "cardano-defi",
      "name": "Cardano DeFi Index",
      "description": "A weighted index tracking the top DeFi tokens",
      "category": "defi",
      "methodology": "Market cap weighted index",
      "index_type": "static",
      "tokens": [...],
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total_count": 5
}
```

#### 4. Get Index Metadata
```
GET /indexes/{index_id}
```
Get detailed metadata for a specific index by ID.

**Path Parameters:**
- `index_id` (string): The unique identifier of the index

**Example:**
```bash
GET https://index-api.linkage.finance/indexes/cardano-defi
```

#### 5. Get Index Price
```
GET /indexes/{index_id}/price
```
Get the current calculated price for a specific index, including market cap and price changes.

**Path Parameters:**
- `index_id` (string): The unique identifier of the index

**Example Response:**
```json
{
  "index_id": "cardano-defi",
  "price": 142.57,
  "market_cap": 2845692.34,
  "timestamp": "2024-01-15T10:30:00Z",
  "price_change_24h": 2.34,
  "price_change_7d": -1.67
}
```

#### 6. Get Historical Prices
```
GET /indexes/{index_id}/history
```
Retrieve historical price data for an index with configurable date range and intervals.

**Path Parameters:**
- `index_id` (string): The unique identifier of the index

**Query Parameters:**
- `start_date` (datetime, optional): Start date for historical data in ISO format (default: 30 days ago)
- `end_date` (datetime, optional): End date for historical data in ISO format (default: now)
- `interval` (string, optional): Time interval for data points. Options: `1h`, `4h`, `1d`, `1w`, `1M` (default: `1d`)

**Example:**
```bash
GET https://index-api.linkage.finance/indexes/cardano-defi/history?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&interval=1d
```

**Example Response:**
```json
{
  "index_id": "cardano-defi",
  "interval": "1d",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "data": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "price": 140.25,
      "volume": 45230.50
    },
    {
      "timestamp": "2024-01-02T00:00:00Z",
      "price": 141.10,
      "volume": 48920.75
    }
  ]
}
```

**Note:** Maximum date range is 365 days (1 year).

#### 7. Get Index Volume
```
GET /indexes/{index_id}/volume
```
Get trading volume information for a specific index over various time windows.

**Path Parameters:**
- `index_id` (string): The unique identifier of the index

**Example Response:**
```json
{
  "index_id": "cardano-defi",
  "volume_24h": 152340.50,
  "volume_7d": 1023456.75,
  "volume_change": 5.2,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Linkage Finance Fund Endpoints

#### 8. Get All Linkage Finance Funds
```
GET /linkage-funds
```
List all Linkage Finance funds created by users through smart contracts.

**Example Response:**
```json
{
  "funds": [
    {
      "fund_id": "fund001",
      "name": "My DeFi Fund",
      "tokens": [...],
      "factors": [...],
      "creator": "addr1...",
      "fund_factor": 1.0,
      "royalty_factor": 0.02,
      "tx": "abc123...",
      "created_at": "2024-01-10T12:00:00Z",
      "index_id": "linkage-fund-fund001"
    }
  ],
  "total_count": 10
}
```

#### 9. Get Specific Linkage Finance Fund
```
GET /linkage-funds/{fund_id}
```
Get detailed information for a specific Linkage Finance fund.

**Path Parameters:**
- `fund_id` (string): The unique identifier of the fund

**Example:**
```bash
GET https://index-api.linkage.finance/linkage-funds/fund001
```

### Admin Endpoints

#### 10. Get Querier Status
```
GET /admin/querier/status
```
Get detailed status information about the historical data collection querier. Requires authentication.

#### 11. Force Querier Run
```
POST /admin/querier/force-run
```
Force an immediate data collection run. Requires authentication.

## Response Codes

The API uses standard HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid API key
- `403 Forbidden`: API key not authorized
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Error Responses

When an error occurs, the API returns a JSON error response:

```json
{
  "detail": "Index 'invalid-id' not found"
}
```

For validation errors:
```json
{
  "detail": [
    {
      "loc": ["query", "start_date"],
      "msg": "invalid datetime format",
      "type": "value_error.datetime"
    }
  ]
}
```

## Index Configuration

You can add new indexes by editing `config/indexes.json`. No code changes needed!

### Static Index Example
```json
{
  "id": "my-static-index",
  "name": "My Custom Static Index",
  "description": "Hand-picked DeFi tokens",
  "category": "defi",
  "methodology": "Manual selection with equal weighting",
  "index_type": "static",
  "tokens": [
    {
      "name": "MILK",
      "policy_id": "afbe91c0b44b3040e360057bf8354ead8c49c4979ae6ab7c4fbdc9eb",
      "token_name": "4d494c4b7632",
      "weight": 0.6,
      "description": "MuesliSwap governance token"
    },
    {
      "name": "MIN", 
      "policy_id": "29d222ce763455e3d7a09a665ce554f00ac89d2e99a1a83d267170c6",
      "token_name": "4d494e",
      "weight": 0.4,
      "description": "Minswap token"
    }
  ]
}
```

### Dynamic Index Example
```json
{
  "id": "top-5-dynamic",
  "name": "Top 5 Market Cap Dynamic Index", 
  "description": "Top 5 Cardano tokens by market cap with 100+ ADA volume",
  "category": "market-cap",
  "methodology": "Auto-selected by market cap, minimum 100 ADA volume",
  "index_type": "dynamic",
  "dynamic_criteria": {
    "selection_method": "market_cap",
    "limit": 5,
    "min_volume_ada": 100.0,
    "min_market_cap": 50000.0,
    "weighting_method": "market_cap",
    "rebalance_frequency": "daily",
    "exclude_tokens": ["SCAM_TOKEN"],
    "include_categories": ["2"]
  }
}
```

### Dynamic Selection Options

**Selection & Filtering:**
- `selection_method`: `"market_cap"` or `"volume"` 
- `limit`: Max tokens (1-50)
- `min_volume_ada`: Minimum 24h volume in ADA (filters low-liquidity tokens)
- `min_market_cap`: Minimum market cap filter
- `exclude_tokens`: Token symbols to never include
- `include_categories`: Only include specific categories (`"2"` = DeFi)

**Weighting:**
- `market_cap`: Weight by market cap (larger tokens get higher weight)
- `equal`: All tokens get equal weight

The API automatically fetches the latest market data from [MuesliSwap's API](https://api-v2.muesliswap.com/list/v2?base-policy-id=&base-tokenname=&verified=true&limit=20&offset=0&search=&sort_by=marketCap&desc=true) to keep dynamic indexes current.

## Configuration

### Environment Variables
You can set these in a `.env` file or as environment variables:

- `CARDANO_INDEX_API_KEYS` - Comma-separated list of valid API keys
- `CARDANO_INDEX_DEBUG` - Set to `true` for debug mode  
- `CARDANO_INDEX_CACHE_TTL_SECONDS` - How long to cache price data (default: 300)

### Example .env file
```
CARDANO_INDEX_API_KEYS=your-secret-key,another-key
CARDANO_INDEX_DEBUG=false
CARDANO_INDEX_CACHE_TTL_SECONDS=300
```

## Linkage Finance Funds Integration

The API now automatically tracks all Linkage Finance funds created by users through smart contracts. These funds are:

- Fetched from Linkage Finance smart contracts
- Converted to index format and served through the API
- Included in historical data collection
- Available through both `/linkage-funds` and `/indexes` endpoints

**Linkage Finance Fund Endpoints:**
- `GET /linkage-funds` - List all user-created funds
- `GET /linkage-funds/{fund_id}` - Get details for a specific fund
- Linkage funds also appear in `GET /indexes` with IDs prefixed with `linkage-fund-`

Funds are stored in `data/linkage_funds.json` and are automatically loaded when the API starts.

## Testing and Data Verification

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run specific test suites
pytest tests/test_api.py
pytest tests/test_linkage_funds.py

# Run with coverage
pytest --cov=app tests/
```

### Data Verification Tool

Verify data accuracy and consistency automatically:

```bash
python tools/verify_data.py
```

This tool checks:
- Index metadata consistency
- Price calculation accuracy
- Historical data integrity
- Linkage Finance funds validation

Results are saved to a JSON report file.

### Performance Testing

Throughput and data freshness are tested with two scripts; full methodology and results are in [PERFORMANCE_TESTING_REPORT.md](PERFORMANCE_TESTING_REPORT.md).

```bash
# Load test (API must be running): concurrent requests, success rate, requests/sec
python3 -m tools.performance_load_test --concurrent 10 --duration 30

# Freshness test: how old is cached price data (cache_age_seconds)
python3 -m tools.performance_freshness_test --samples 5
```

### Backtest Data Generator

Generate historical test data for backtesting API changes:

```bash
python tools/backtest_data.py
```

This generates realistic historical price data for all indexes and exports it for testing. See `tools/README.md` for detailed documentation.

## How It Works

1. **Price Data:** Real-time price data from [MuesliSwap](https://v2.muesliswap.com/markets) (a Cardano DEX)
2. **Static Indexes:** Use pre-configured tokens with fixed weights
3. **Dynamic Indexes:** Automatically select tokens based on market cap, volume filters (min 100 ADA), and other criteria  
4. **Historical Data:** Background querier collects actual index prices every 15 minutes and stores them in a database
5. **Index Calculation:** Prices are weighted according to each token's percentage in the index
6. **Caching:** Recent data cached for 5 minutes to improve performance
7. **Volume Filtering:** Dynamic indexes only include tokens with sufficient trading activity

## Live Examples

The API comes with sample indexes:

**Static Indexes:**
- `cardano-defi` - Curated DeFi tokens (MILK, MIN, SUNDAE)
- `cardano-gaming` - Gaming & NFT tokens (HOSKY, CLAY)

**Dynamic Indexes:**
- `cardano-top5-dynamic` - Top 5 by market cap, min 100 ADA volume
- `cardano-defi-dynamic` - Auto-selected DeFi tokens, min 500 ADA volume

**Linkage Finance Funds:**
- All user-created funds from Linkage Finance smart contracts
- Automatically tracked and converted to index format
- Example IDs: `linkage-fund-fund001`, `linkage-fund-fund002`, etc.

## API Documentation

Once running, visit these URLs:
- **Interactive docs:** http://localhost:8000/docs
- **Alternative docs:** http://localhost:8000/redoc  
- **Health check:** http://localhost:8000/health

## Production Deployment

### Deployment URL
The API is deployed at: **https://index-api.linkage.finance**


### Performance Tips
- Adjust `CARDANO_INDEX_CACHE_TTL_SECONDS` based on your needs (lower = more fresh data, higher = better performance)
- Monitor MuesliSwap API rate limits
- Historical data is stored in the database for efficient querying
- Use appropriate date ranges for historical queries (max 365 days)
- Cache responses client-side when possible

### Getting Help
- **Interactive API docs:** Visit `https://index-api.linkage.finance/docs` for interactive testing
- **Health check:** Visit `https://index-api.linkage.finance/health` to verify API status
- **Check logs:** `docker-compose logs cardano-index-api` (for local development)
- **Verify configuration:** Use the `/health` endpoint to check system status

## Usage Guide

For detailed usage examples and common use cases, see [USAGE_GUIDE.md](USAGE_GUIDE.md).

The usage guide covers:
- Getting started with the API
- Common integration patterns
- Code examples in multiple languages
- Best practices and tips
- Troubleshooting common issues

## Contributing

This is an open-source project. Feel free to:
- Report bugs
- Suggest features  
- Submit improvements
- Add new index categories or selection methods

## Technical Details

### Architecture
- **FastAPI** - Modern, fast web framework for building APIs
- **Pydantic** - Data validation and settings management
- **httpx** - Async HTTP client for external API calls
- **uvicorn** - ASGI server for production deployment
- **SQLite/AsyncIO** - Database for historical data storage
- **asyncio** - Asynchronous programming for concurrent operations

### Data Flow

1. **Price Calculation:**
   - Fetches real-time token prices from MuesliSwap API
   - Applies index weights to calculate aggregate index price
   - Caches results for 5 minutes (configurable)

2. **Historical Data Collection:**
   - Background querier runs every 15 minutes (configurable)
   - Collects current prices for all indexes
   - Stores in SQLite database with timestamps
   - Supports querying with various time intervals

3. **Dynamic Index Updates:**
   - Fetches market data from MuesliSwap
   - Applies selection criteria (market cap, volume filters)
   - Calculates token weights based on methodology
   - Updates index composition automatically

### File Structure
```
├── app/                    # Application code
│   ├── core/              # Configuration and authentication
│   │   ├── auth.py        # API key authentication
│   │   └── config.py      # Settings management
│   ├── db/                # Database models and management
│   │   ├── database.py    # Database connection and queries
│   │   └── models.py      # SQLAlchemy models
│   ├── models/            # Pydantic schemas
│   │   └── schemas.py     # Request/response models
│   ├── routers/           # API endpoint handlers
│   │   ├── indexes.py     # Index endpoints
│   │   └── linkage_funds.py  # Linkage Finance fund endpoints
│   └── services/          # Business logic
│       ├── index_service.py        # Index price calculations
│       ├── historical_querier.py   # Background data collection
│       ├── linkage_finance.py      # Linkage Finance integration
│       └── muesliswap.py           # MuesliSwap API client
├── config/                # JSON configuration files
│   └── indexes.json       # Index definitions
├── data/                  # Data files
│   ├── linkage_funds.json # Linkage Finance fund data
│   └── cardano_index_data.db  # SQLite database
├── tools/                 # Utility tools
│   ├── verify_data.py     # Data verification tool
│   └── backtest_data.py   # Backtest data generator
├── tests/                 # Test files
│   ├── test_api.py        # API endpoint tests
│   ├── test_linkage_funds.py  # Linkage Finance tests
│   └── test_services.py   # Service layer tests
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── docker-compose.yml    # Docker deployment configuration
```

See `tools/README.md` for detailed documentation on testing and verification tools.
