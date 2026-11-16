# Backend QA Framework

A hands-on backend quality engineering portfolio: API functional tests, database integrity checks, concurrency testing, performance and resilience testing with k6, observability with Prometheus and Grafana, and CI pipelines in GitHub Actions.

Every service in this repo is a **practice target I own**. Bugs were planted, found with tests, fixed, and guarded with regression tests in CI.

---

## What's inside

| Area | Tools | Highlights |
|---|---|---|
| API functional testing | pytest, requests | CRUD, auth, schema and negative tests against a public practice API |
| Collection testing | Postman, Newman | Variables, chained requests, scripted assertions, HTML report in CI |
| Database integrity | PostgreSQL, psycopg | API response vs. stored row, no partial writes, money-conservation invariant |
| Concurrency | Python threads + barrier | Double-spend race reproduced and fixed; deadlock regression test |
| Performance | k6 | Smoke, load, stress, spike, soak, capacity (knee) and user-journey tests |
| Resilience | Express, Postgres | Load shedding (503 + Retry-After), lock and statement timeouts |
| Observability | prom-client, Prometheus, Grafana | Latency histograms, business metrics, pool saturation, provisioned dashboard |
| CI/CD | GitHub Actions, Docker Compose | Test gate, perf smoke gate, nightly load and spike runs, report artifacts |

---

## Services

All services run with Docker Compose.

| Service | Port (host) | Purpose |
|---|---|---|
| `ratelimit-api` | 3000 | Rate-limiting practice API |
| `mock-payment` | 4000 | Mocked payment provider for resilience tests |
| `perf-api` | 5050 | Express API with CPU-, I/O- and pool-bound endpoints for performance testing |
| `bank-db` | 5433 | PostgreSQL 17 for bank-api |
| `bank-api` | 8081 | Accounts and transfers on PostgreSQL, instrumented with metrics |
| `prometheus` | 9090 | Metrics storage *(profile `monitoring`)* |
| `grafana` | 3001 | Dashboards *(profile `monitoring`)* |

`perf-api` runs with a resource limit of 1 CPU and 256 MB, so performance results are repeatable.

---

## Quick start

```bash
# Python environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Core services (same set as CI)
docker compose up -d --build

# Optional monitoring stack
docker compose --profile monitoring up -d prometheus grafana
open http://localhost:3001/d/bank-api

# Run all tests
pytest -v

# Only the database and concurrency tests
pytest tests/db -v
```

k6 is used locally at v2.3.0 (`grafana/k6:2.3.0` in CI).

---

## Test suites

### 1. API functional tests (pytest)

Run against a public practice API (restful-booker).

- CRUD lifecycle: create → read → update → delete → read returns 404
- Auth token obtained once in a `conftest.py` fixture
- Known defects of the practice API are marked `xfail`, so they stay visible without breaking the build

### 2. Postman collection (Newman)

`postman/collection.json` and `postman/environment.json`.

- Variable scopes (local, environment, collection, global) and the Initial vs. Current value export pitfall
- Chained requests: Create saves `bookingId`; Read verifies against the value that was sent
- Login guard with try/catch so one failed login doesn't cascade into confusing failures
- Runs in CI with an HTML report artifact; the job is non-blocking because it depends on an external site

### 3. Database integrity tests (`tests/db/test_bank_db.py`)

Each test calls the API, then queries PostgreSQL directly.

| Check | Example |
|---|---|
| Saved what the API said it saved | Balance in the response equals the stored `NUMERIC(12,2)` value |
| Failed requests leave nothing behind | Insufficient funds, missing account and invalid amount change no balances and write no transfer row |
| Business invariant | Total money across both accounts is unchanged after a transfer |
| Contract consistency | `POST` and `GET` return `balance` in the same format |

Money is compared with `Decimal`, never `float`. Every test creates its own data, so tests are independent of order.

### 4. Concurrency tests (`tests/db/test_bank_concurrency.py`)

Requests are released at the same instant with `threading.Barrier`.

| Test | What it proves |
|---|---|
| `test_concurrent_transfers_cannot_overspend` | 20 simultaneous 100-transfers from a 100 account: exactly 1 succeeds, money is conserved, ledger matches balances |
| `test_opposite_transfers_do_not_deadlock` | A→B and B→A at the same time all succeed |
| `test_locked_account_fails_fast_and_does_not_stall_others` | A locked account returns 503 within two pool waves; unrelated reads stay fast |

Both the overspend and deadlock tests were **verified to fail** against the pre-fix code before being trusted.

### 5. Performance tests (k6, `perf/`)

| Script | Type | What it does |
|---|---|---|
| `smoke.js` | Smoke / CI gate | 1 VU for 30 s; per-endpoint p95 thresholds; fails the build on regression |
| `closed-db.js` | Closed model | Fixed number of VUs (`VUS`) |
| `open-db.js` | Open model | Fixed arrival rate (`RATE`) |
| `find-knee-db.js` | Capacity | Ramping arrival rate with per-stage tags to find the knee |
| `load-db.js` | Load | Ramps to `TARGET` req/s; SLO thresholds on p95, p99, errors, dropped iterations |
| `stress-db.js` | Stress + recovery | Pushes past capacity, then checks recovery phases |
| `spike-db.js` | Spike | 40 → 200 req/s in 2 s, then measures recovery |
| `soak.js` | Soak | Long run watching heap and cache size (`MINUTES`) |
| `journey.js` | User journey | Login once per VU, browse, product, orders, checkout, with think time |
| `journeys-mix.js` | Traffic mix | Browsers, buyers and order checkers as separate scenarios |
| `lifecycle.js` | Setup/teardown | Health check with abort, shared token, heap baseline |
| `login-data.js` | Data-driven | 50 users from JSON via `SharedArray` |
| `bank-load.js` | Load + incident | 20 req/s on bank-api with a hot merchant account |

### 6. Observability (`monitoring/`)

bank-api exposes `/metrics`:

| Metric | Type | Purpose |
|---|---|---|
| `http_request_duration_seconds` | Histogram | Latency by method, **route pattern** and status |
| `bank_transfers_total{outcome}` | Counter | success, insufficient_funds, not_found, busy, error (all initialised at 0) |
| `db_pool_connections{state}` | Gauge | total, idle and **waiting**: pool saturation |
| Node defaults | Mixed | CPU, memory, event-loop lag, GC |

The Grafana dashboard is provisioned from `monitoring/grafana/dashboards/bank-api.json`: requests/s, p95 by route, 5xx rate, transfers by outcome, event-loop lag, memory and DB pool.

---

## CI pipelines (`.github/workflows/`)

### `tests.yml`: on every push and pull request

| Job | What it does | Blocking |
|---|---|---|
| `test` | Starts all core services, waits until bank-api `/health` confirms the DB is reachable, runs pytest | ✅ |
| `perf-smoke` | Starts perf-api, runs `smoke.js` in pinned k6, uploads the HTML report | ✅ |
| `postman` | Runs the collection with Newman, uploads the HTML report | ❌ (external dependency) |

### `perf-nightly.yml`: scheduled nightly and on demand

Runs `load-db.js` and `spike-db.js` and uploads both HTML reports.

Practices used: pinned image versions, readiness loops instead of fixed sleeps, `if: always()` for reports and cleanup, `if-no-files-found: error`, a container `--user` matching the runner so reports can be written.

---

## Findings

### Defects found and fixed

| # | Defect | Found by | Severity | Fix |
|---|---|---|---|---|
| 1 | Sub-cent amounts silently rounded by the DB while the API reported the unrounded value | API vs. DB check | Medium–High | Money validation; return the saved row |
| 2 | Negative opening balance returned 500 instead of 400 | Data-first negative test | Low–Medium | Input validation |
| 3 | Sub-cent transfer returned 500 instead of 400 | Atomicity test | Low–Medium | Input validation |
| 4 | `POST` and `GET` returned `balance` as different types | Contract test | Medium | Return the persisted row |
| 5 | **Double spend**: 20 parallel transfers turned 100 into 1,000 | Barrier concurrency test | **Critical** | `SELECT … FOR UPDATE`, locking in `id` order |
| 6 | Deadlock on opposite-direction transfers (500s, 1 s stalls) | Deadlock test | High | Consistent lock order |
| 7 | One locked row exhausted the DB pool and stalled **every** endpoint for 30 s with 0% errors | k6 + Grafana | High | `lock_timeout` + `statement_timeout`, 503 + `Retry-After` |
| 8 | `/db` collapsed under overload (90–100% failures, no recovery) | k6 stress test | High | Load shedding with a bounded queue |
| 9 | Unbounded report cache (memory leak) | k6 soak test | High | Capped cache with eviction |

### Performance results (perf-api `/db`, 1 CPU)

| Measure | Result |
|---|---|
| Capacity (knee) | ~97 req/s |
| Load at 70 req/s | p95 54 ms, 0 errors |
| Stress at 130 req/s, after load shedding | 24.7% fast 503s, 0% failures in recovery, goodput 777 → 5,876 |
| Spike 40 → 200 req/s | 51% fast 503s, 0 timeouts, recovery under 1 s |
| CI regression gate | Turned red on an injected slowdown (db p95 122.8 ms), green after revert |

---

## Lessons and design decisions

- **Check the data, not just the response.** The API can say "success" while the database holds something else.
- **For failed requests, assert on data first, status second.** "Data safe, wrong status" and "data corrupted" are very different severities.
- **A transaction gives atomicity, not protection from races.** Under `READ COMMITTED`, a plain `SELECT` takes no lock.
- **Every test must fail once** against the buggy code before it's trusted. Race tests are run repeatedly.
- **Measure the distribution, not one number.** A total of 6 s turned out to be three 2 s waves, because `lock_timeout` restarts for each lock wait.
- **Monitor the four golden signals:** latency, traffic, errors and saturation. The pool incident produced 0% errors.
- **Prometheus percentiles are bucket estimates.** Bucket boundaries must match the SLO.
- **Keep metric labels low-cardinality.** Label by route pattern (`/accounts/:id`), never the raw URL.
- **A client timeout means "unknown", not "failed".** The server can still complete the work, so payment APIs need idempotency keys.
- **Keep CI trustworthy.** External dependencies shouldn't block the gate for your own code.

---

## Project structure

```
.
├── bank-api/                 # Express + PostgreSQL bank service (metrics, locking, timeouts)
│   ├── server.js
│   ├── init.sql
│   └── Dockerfile
├── perf-api/                 # Express service for performance experiments
├── ratelimit-api/            # Rate-limit API and mock payment provider
├── tests/db/                 # Database integrity and concurrency tests
├── perf/                     # k6 scripts and test data
├── postman/                  # Postman collection and environment
├── monitoring/               # Prometheus config and Grafana provisioning
├── .github/workflows/        # tests.yml, perf-nightly.yml
├── conftest.py               # Shared pytest fixtures (auth)
├── test_*.py                 # API functional tests
├── docker-compose.yml
└── requirements.txt
```

---

## Roadmap

- Structured JSON logs and correlation IDs (request ID in a header and on every log line)
- Framework refactor: API client layer, data factories, per-environment config, parallel runs with `pytest-xdist`, Allure reports
- pytest markers to separate own-code tests from external-dependency tests
- Idempotency keys for `/transfer`
- Bulkhead: a separate connection pool for reads
- Fix the unbounded sessions map in perf-api

---

## Safety rules for this repo

- Only practice targets are load-tested or attacked.
- No real secrets are committed; local-only passwords are clearly marked.
- Work files and employer data never enter this repository; `git status` and `git add --dry-run` are checked before every commit.
