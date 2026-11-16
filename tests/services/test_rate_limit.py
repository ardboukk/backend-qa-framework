import time
import requests

from tests.config import RATELIMIT_URL, RATE_WINDOW_S

URL = f"{RATELIMIT_URL}/hello"     # our own rate-limited server
LIMIT = 5                                # 5 requests allowed...
WINDOW = RATE_WINDOW_S                   # ...per window (2 s in the test environment)


def start_fresh_window():                # a HELPER function (not a test: no "test_" at the start)
    time.sleep(WINDOW + 1)               # wait one window + 1 s, so any old window has expired


def test_requests_up_to_the_limit_succeed():
    start_fresh_window()
    codes = [requests.get(URL).status_code for _ in range(LIMIT)]    # 5 requests → list of 5 codes
    assert codes == [200] * LIMIT                                    # [200, 200, 200, 200, 200]


def test_one_request_over_the_limit_gets_429():
    start_fresh_window()
    for _ in range(LIMIT):        # use up the 5 allowed requests
        requests.get(URL)

    r = requests.get(URL)         # request number 6

    assert r.status_code == 429                 # blocked
    assert "error" in r.json()                  # the body explains why
    assert "Retry-After" in r.headers           # checking a HEADER, not the body


def test_limit_resets_after_the_window():
    start_fresh_window()
    for _ in range(LIMIT + 1):    # 6 requests: hit the limit
        requests.get(URL)

    time.sleep(WINDOW + 1)        # wait for the reset
    r = requests.get(URL)

    assert r.status_code == 200   # allowed again


def test_first_request_shows_4_remaining():
    start_fresh_window()
    r = requests.get(URL)

    assert r.status_code == 200
    assert "remaining=4" in r.headers["RateLimit"]