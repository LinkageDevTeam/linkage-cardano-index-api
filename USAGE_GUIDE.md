# Cardano Index API - Usage Guide

Quick reference guide for using the Cardano Index API at **https://index-api.linkage.finance**.

## Quick Start

### Base URL
```
https://index-api.linkage.finance
```

### Interactive Documentation
- **Swagger UI:** https://index-api.linkage.finance/docs
- **Health Check:** https://index-api.linkage.finance/health

### Your First Request
```bash
curl -H "Authorization: Bearer your-api-key-here" \
  https://index-api.linkage.finance/indexes
```

## Authentication

All endpoints (except `/` and `/health`) require an API key in the `Authorization` header.

**Development API key:** `demo-api-key-please-change`

### Examples

**cURL:**
```bash
curl -H "Authorization: Bearer your-api-key-here" \
  https://index-api.linkage.finance/indexes/cardano-defi/price
```

**JavaScript:**
```javascript
const response = await fetch('https://index-api.linkage.finance/indexes', {
  headers: { 'Authorization': 'Bearer your-api-key-here' }
});
const data = await response.json();
```

**Python:**
```python
import requests

headers = {'Authorization': 'Bearer your-api-key-here'}
response = requests.get('https://index-api.linkage.finance/indexes', headers=headers)
data = response.json()
```

## Main Endpoints

### 1. Get All Indexes
```
GET /indexes
```
Returns list of all available indexes with metadata.

### 2. Get Index Metadata
```
GET /indexes/{index_id}
```
Get detailed information about a specific index.

### 3. Get Current Price
```
GET /indexes/{index_id}/price
```
**Response:**
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

### 4. Get Historical Prices
```
GET /indexes/{index_id}/history?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&interval=1d
```

**Query Parameters:**
- `start_date` (optional): ISO format datetime (default: 30 days ago)
- `end_date` (optional): ISO format datetime (default: now)
- `interval` (optional): `1h`, `4h`, `1d`, `1w`, `1M` (default: `1d`)

**Max date range:** 365 days

**Response:**
```json
{
  "index_id": "cardano-defi",
  "interval": "1d",
  "data": [
    {"timestamp": "2024-01-01T00:00:00Z", "price": 140.25, "volume": 45230.50},
    {"timestamp": "2024-01-02T00:00:00Z", "price": 141.10, "volume": 48920.75}
  ]
}
```

### 5. Get Volume Data
```
GET /indexes/{index_id}/volume
```

### 6. Get Linkage Finance Funds
```
GET /linkage-funds
GET /linkage-funds/{fund_id}
```

Linkage Finance funds can be used as indexes with ID format: `linkage-fund-{fund_id}`. Please note all funds are currently on testnet only. 

