# Backend QA Test Framework

![API tests](https://github.com/ardboukk/backend-qa-framework/actions/workflows/tests.yml/badge.svg)

API test framework built during a Backend QA course (Module 6: API & Backend Testing).

## What's inside

| Area | Files |
|---|---|
| CRUD API tests with fixtures | `conftest.py`, `test_booking_crud.py`, `test_my_api.py` |
| Negative and boundary tests | `test_booking_negative.py`, `test_login_negative.py`, `test_classify.py` |
| Rate-limit tests | `test_rate_limit.py` |
| Fault-injection tests (timeouts, retries, resets) | `test_payment_faults.py` |
| Performance tests (k6) | `perf/` |
| Mock servers (Node.js, Docker) | `ratelimit-api/`, `docker-compose.yml` |
| CI pipeline (GitHub Actions) | `.github/workflows/tests.yml` |

## Requirements

- Python 3.9+
- Docker Desktop (for the mock servers)
- k6 (optional, for performance tests)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the tests

1. Start the mock servers (rate-limited API on port 3000, mock payment service on port 4000):

```bash
docker compose up -d --build
```

2. Run the tests:

```bash
pytest -v
```

3. Stop the servers when you're done:

```bash
docker compose down
```

## Performance tests

With the servers running:

```bash
k6 run perf/load-test.js
```

## Known defects

Some tests are marked `xfail` because they document real bugs in the public practice API (Restful-Booker), for example a failed login returning 200 instead of 401.
