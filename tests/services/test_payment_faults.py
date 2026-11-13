import time
import pytest
import requests

MOCK = "http://localhost:4000"


def pay(path, timeout=2, retries=2):
    """A payment client: timeout + limited retries on temporary failures."""
    for attempt in range(1, retries + 2):
        try:
            r = requests.get(f"{MOCK}{path}", timeout=timeout)
            if r.status_code == 503 and attempt <= retries:
                time.sleep(0.2)            # short wait, then retry
                continue
            return {"status_code": r.status_code, "attempts": attempt}
        except (requests.Timeout, requests.ConnectionError):
            if attempt <= retries:
                continue
            return {"status_code": 503, "attempts": attempt}   # give up cleanly


def test_normal_payment_succeeds_first_try():
    result = pay("/pay")
    assert result == {"status_code": 200, "attempts": 1}


def test_slow_payment_times_out_instead_of_hanging():
    start = time.time()
    result = pay("/pay/slow", timeout=1, retries=0)
    elapsed = time.time() - start

    assert result["status_code"] == 503
    assert elapsed < 2, f"Client waited {elapsed:.1f}s, the timeout did not work"


def test_flaky_payment_succeeds_after_retry():
    result = pay("/pay/flaky")
    assert result["status_code"] == 200
    assert result["attempts"] >= 2


def test_connection_reset_does_not_crash():
    result = pay("/pay/reset")
    assert result["status_code"] == 503


def test_service_down_gives_clean_503_after_retries():
    result = pay("/pay/down", retries=2)
    assert result == {"status_code": 503, "attempts": 3}

def test_down_with_no_retries_gives_up_after_one_attempt():
    result = pay("/pay/down", retries = 0)
    assert result == {"status_code": 503, "attempts": 1}