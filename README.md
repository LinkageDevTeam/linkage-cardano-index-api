# Cardano Index API

An API that creates and tracks indexes for tokens in the Cardano ecosystem. This project provides real-time prices, historical data, and volume information for both **static** and **dynamic** Cardano token indexes.

## What Does This Do?

This API helps you:
- Get current prices for Cardano token indexes
- View historical price data with charts  
- Check trading volume information
- Track both manual (static) and automated (dynamic) indexes
- Automatically select top tokens by market cap or volume

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

## How to Use the API

### Authentication
All API calls need an API key in the header:
```
Authorization: Bearer your-api-key-here
```

### Main Endpoints

1. **Get all indexes:**
   ```
   GET /indexes
   ```

2. **Get current price for an index:**
   ```
   GET /indexes/cardano-defi/price
   ```

3. **Get historical prices:**
   ```
   GET /indexes/cardano-defi/history?start_date=2024-01-01&end_date=2024-01-31&interval=1d
   ```

4. **Get volume data:**
   ```
   GET /indexes/cardano-defi/volume
   ```

### Example Response
```json
{
  "index_id": "cardano-top5-dynamic",
  "price": 142.57,
  "market_cap": 2845692.34,
  "timestamp": "2024-01-15T10:30:00Z",
  "price_change_24h": 2.34,
  "price_change_7d": -1.67
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

## Testing

Run the tests to make sure everything works:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

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

## API Documentation

Once running, visit these URLs:
- **Interactive docs:** http://localhost:8000/docs
- **Alternative docs:** http://localhost:8000/redoc  
- **Health check:** http://localhost:8000/health

## Production Deployment

### Security Checklist
- [ ] Change the default API key (`demo-api-key-please-change`)
- [ ] Use strong, unique API keys for each client
- [ ] Monitor API usage and set rate limits
- [ ] Regularly backup your index configuration

### Performance Tips
- Adjust `CARDANO_INDEX_CACHE_TTL_SECONDS` based on your needs
- Monitor MuesliSwap API rate limits
- Consider adding a database for historical price storage

### Getting Help
- Check the logs: `docker-compose logs cardano-index-api`
- Verify configuration: Visit `/health` endpoint
- Test individual endpoints: Use the `/docs` interactive interface

## Contributing

This is an open-source project. Feel free to:
- Report bugs
- Suggest features  
- Submit improvements
- Add new index categories or selection methods

## Technical Details

### Architecture
- **FastAPI** - Web framework
- **Pydantic** - Data validation  
- **httpx** - HTTP client for external APIs
- **uvicorn** - ASGI server

### File Structure
```
├── app/                 # Application code
│   ├── core/           # Configuration and auth
│   ├── models/         # Data models  
│   ├── routers/        # API endpoints
│   └── services/       # Business logic
├── config/             # JSON configuration files
├── tests/              # Test files
├── main.py            # Application entry point
└── requirements.txt   # Python dependencies
```
