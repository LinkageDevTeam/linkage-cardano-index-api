# Cardano Index API – Performance Testing Report

## 1. Introduction

This report describes the performance testing and optimizations done for the Cardano Index API. The API serves index prices, volume, and historical data for Cardano ecosystem tokens. Prices are derived from the MuesliSwap DEX via their public API.

The goals of this work were:

- **Throughput:** Support a reasonable number of concurrent requests (e.g. 10–20 parallel users) without errors or long delays.
- **Data freshness:** Make it clear how up to date the API is with DEX prices and ensure data is refreshed within a known time window (e.g. within the cache TTL).

We did not aim for extreme performance (e.g. thousands of requests per second). The focus was on stable, predictable behaviour and small, practical improvements.

---

## 2. How We Tested

### 2.1 Throughput (number of requests in parallel)

We use a small load test script that sends many requests at the same time and then reports:

- Total requests and how many succeeded (HTTP 200).
- Requests per second (throughput).
- Average response time (latency).

**Tool:** `tools/performance_load_test.py` (async Python, `httpx`).

**What it does:**

- Runs a fixed number of **concurrent clients** (e.g. 10 or 20).
- Each client repeatedly calls:
  - `GET /indexes`
  - `GET /indexes/{index_id}/price`
- The test runs for a fixed **duration** (e.g. 30 seconds).
- At the end it prints: total requests, success count, success rate, wall-clock time, requests per second, and average latency.

**How to run:**

```bash
# From project root, with the API running (e.g. uvicorn main:app)
python3 -m tools.performance_load_test --concurrent 10 --duration 30
```

Optional arguments: `--base-url`, `--api-key`, `--index-id`, `--concurrent`, `--duration`.

### 2.2 Data freshness (how quickly DEX prices show up in the API)

We measure how “old” the price data can be when a client calls the API. The API gets DEX prices from MuesliSwap and caches them for a short time. So “freshness” is determined by:

- **Cache TTL:** Default 300 seconds (5 minutes). Price data is at most this old.
- **Observed cache age:** The API now returns an optional `cache_age_seconds` field on price responses when the result is served from cache. This tells clients exactly how many seconds ago the data was fetched from MuesliSwap.

**Tool:** `tools/performance_freshness_test.py`.

**What it does:**

- Calls `GET /indexes/{index_id}/price` several times (e.g. 5 samples).
- Reads `timestamp` and `cache_age_seconds` from each response.
- Prints min/max/avg cache age so you can see how freshness behaves over time.

**How to run:**

```bash
python3 -m tools.performance_freshness_test --samples 5
```

**Interpretation:** After a DEX price change, the Index API will show the new price the next time it fetches from MuesliSwap (cache miss or TTL expiry). So “how quickly DEX prices propagate” is: **within at most the cache TTL (default 5 minutes)**. The `cache_age_seconds` value shows how many seconds ago the current response was last fetched from upstream.

---

## 3. Baseline (Before Improvements)

Before the changes below, the API behaved as follows:

- **HTTP client:** Each call to MuesliSwap created a new HTTP connection. Under load, that meant many short-lived connections and extra latency.
- **Cache:** Price and volume were already cached in memory for 5 minutes (configurable via `cache_ttl_seconds`), but the response did not expose how old the cached data was.
- **Throughput:** When the cache was warm, the API could handle a moderate number of concurrent requests because it did not hit MuesliSwap on every request. When the cache was cold or under many different index IDs, more MuesliSwap calls were made and throughput was lower and more variable.
- **Freshness:** Data could be up to 5 minutes old (cache TTL). There was no way for clients to know the exact age of the data.

---

## 4. Improvements Implemented

We implemented the following changes to meet the milestone and improve performance in a simple way.

| Improvement | Description |
|-------------|-------------|
| **Shared HTTP client for MuesliSwap** | The MuesliSwap service now uses a single shared `httpx.AsyncClient` instead of creating a new client per request. Connections are reused, which reduces latency and connection churn when many price requests are made (e.g. for multiple tokens or concurrent users). The client is closed on application shutdown. |
| **Cache age in price response** | The price endpoint response now includes an optional `cache_age_seconds` field when the result is served from cache. This allows clients and tests to see exactly how many seconds ago the data was fetched from the DEX, so you can measure and report on “how up to date” the API is. |
| **Performance test scripts** | Two scripts were added: `tools/performance_load_test.py` (throughput and success rate under concurrent load) and `tools/performance_freshness_test.py` (cache age over several samples). Both are documented above and can be run locally to reproduce the results. |

No new external dependencies were added for the tests; they use the existing `httpx` dependency.

---

## 5. Results After Improvements

- **Throughput:** With a shared HTTP client, requests that trigger MuesliSwap calls (e.g. cache miss or first request for an index) complete faster. Under concurrent load (e.g. 10 clients for 30 seconds), you should see a higher number of successful requests per second and a stable or improved success rate compared to the previous “new connection per request” behaviour. Exact numbers depend on your machine and network; run the load test as in section 6 to get your own results.
- **Freshness:** Price data is still at most **5 minutes old** (default `cache_ttl_seconds = 300`). DEX price changes therefore propagate to the API **within at most 5 minutes**. The new `cache_age_seconds` field lets you confirm this in the test: over several samples, cache age will stay between 0 and 300 seconds (and will reset when the cache is refreshed).
- **Stability:** Reusing one HTTP client and closing it on shutdown avoids connection leaks and keeps behaviour predictable under load.

---

## 6. Summary

- We **tested** the API for (1) **number of requests in parallel** (throughput and success rate) and (2) **how up to date the API is with DEX prices** (via cache TTL and the new `cache_age_seconds` field).
- We **implemented** shared HTTP connection reuse for MuesliSwap, optional `cache_age_seconds` in the price response, and two performance test scripts.
- The API is **suitable for moderate concurrency** (e.g. 10–20 concurrent users) and provides **transparent freshness**: clients can see how old the data is, and DEX prices propagate to the API within the configured cache TTL (default 5 minutes).

---

## 7. How to Reproduce

1. **Start the API** (from project root):
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Run the load test** (in another terminal):
   ```bash
   python3 -m tools.performance_load_test --concurrent 10 --duration 30
   ```
   Record: total requests, success rate, requests per second, average latency.

3. **Run the freshness test**:
   ```bash
   python3 -m tools.performance_freshness_test --samples 5
   ```
   Check that `cache_age_seconds` appears when the price is served from cache and that values stay within 0–300 seconds (for default TTL).

4. **Optional – change cache TTL:** Set `CARDANO_INDEX_CACHE_TTL_SECONDS` (e.g. in `.env`) to see how freshness changes. Shorter TTL means fresher data but more MuesliSwap calls; longer TTL means fewer calls and slightly staler data.

These steps give you the numbers and behaviour needed to fill in your milestone report (throughput and data freshness) and to re-run after any future changes.
