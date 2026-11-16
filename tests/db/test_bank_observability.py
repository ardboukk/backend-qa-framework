"""
Observability contract: every response carries a request ID; error bodies include it.

    pytest tests/db/test_bank_observability.py -v
"""
import re
import uuid

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def test_every_response_has_a_generated_request_id(bank):
    r = bank.health(headers={"X-Request-Id": None})  # None = send no ID at all
    rid = r.headers.get("X-Request-Id")
    assert rid, "response has no X-Request-Id header"
    assert UUID_RE.match(rid), f"generated id is not a UUID: {rid!r}"


def test_client_request_id_is_reused(bank):
    sent = f"qa-{uuid.uuid4()}"
    r = bank.health(headers={"X-Request-Id": sent})
    assert r.headers.get("X-Request-Id") == sent


def test_unsafe_request_id_is_replaced(bank):
    sent = 'bad id "<script>"'
    r = bank.health(headers={"X-Request-Id": sent})
    rid = r.headers.get("X-Request-Id")
    assert rid, "response has no X-Request-Id header"
    assert rid != sent, f"unsafe id was accepted: {rid!r}"
    assert UUID_RE.match(rid), f"replacement is not a UUID: {rid!r}"


def test_error_body_includes_the_request_id(bank):
    sent = f"qa-{uuid.uuid4()}"
    r = bank.transfer(1, 1, 5, headers={"X-Request-Id": sent})  # same account -> 400, no DB needed
    assert r.status_code == 400, r.text
    assert r.json().get("request_id") == sent, f"error body: {r.text}"


def test_client_tags_requests_with_the_test_name(bank):
    r = bank.health()
    rid = r.headers.get("X-Request-Id", "")
    assert rid.startswith("qa-test_client_tags_requests_with_the_test_name-"), (
        f"test traffic is not tagged; got {rid!r}"
    )