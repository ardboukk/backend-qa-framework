"""
Observability contract: every response carries a request ID; error bodies include it.

    pytest tests/db/test_bank_observability.py -v
"""
import os
import re
import uuid

import requests

API = os.getenv("BANK_API_URL", "http://localhost:8081")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def test_every_response_has_a_generated_request_id():
    r = requests.get(f"{API}/health", timeout=5)
    rid = r.headers.get("X-Request-Id")
    assert rid, "response has no X-Request-Id header"
    assert UUID_RE.match(rid), f"generated id is not a UUID: {rid!r}"


def test_client_request_id_is_reused():
    sent = f"qa-{uuid.uuid4()}"
    r = requests.get(f"{API}/health", headers={"X-Request-Id": sent}, timeout=5)
    assert r.headers.get("X-Request-Id") == sent


def test_unsafe_request_id_is_replaced():
    sent = 'bad id "<script>"'
    r = requests.get(f"{API}/health", headers={"X-Request-Id": sent}, timeout=5)
    rid = r.headers.get("X-Request-Id")
    assert rid, "response has no X-Request-Id header"
    assert rid != sent, f"unsafe id was accepted: {rid!r}"
    assert UUID_RE.match(rid), f"replacement is not a UUID: {rid!r}"


def test_error_body_includes_the_request_id():
    sent = f"qa-{uuid.uuid4()}"
    r = requests.post(
        f"{API}/transfer",
        json={"from_id": 1, "to_id": 1, "amount": 5},  # same account -> 400, no DB needed
        headers={"X-Request-Id": sent},
        timeout=5,
    )
    assert r.status_code == 400, r.text
    assert r.json().get("request_id") == sent, f"error body: {r.text}"