import pytest
import requests
from conftest import BASE_URL, HEADERS


def valid_booking():
    """A known-good booking. Each negative case breaks ONE thing in it."""
    return {
        "firstname": "QA",
        "lastname": "Negative",
        "totalprice": 100,
        "depositpaid": True,
        "bookingdates": {"checkin": "2026-11-01", "checkout": "2026-11-05"},
    }


def without(field):
    data = valid_booking()
    del data[field]
    return data


def with_value(field, value):
    data = valid_booking()
    data[field] = value
    return data


def with_dates(checkin, checkout):
    data = valid_booking()
    data["bookingdates"] = {"checkin": checkin, "checkout": checkout}
    return data


# ---- The negative payload library: (test name, payload) ----
BAD_PAYLOADS = [
    ("empty body",              {}),
    ("missing firstname",       without("firstname")),
    ("missing totalprice",      without("totalprice")),
    ("missing bookingdates",    without("bookingdates")),
    ("empty firstname",         with_value("firstname", "")),
    ("firstname is a number",   with_value("firstname", 123)),
    ("price is text",           with_value("totalprice", "abc")),
    ("price is negative",       with_value("totalprice", -100)),
    ("depositpaid is text",     with_value("depositpaid", "yes")),
    ("checkout before checkin", with_dates("2026-11-10", "2026-11-01")),
    ("checkin not a date",      with_dates("not-a-date", "2026-11-05")),
]


@pytest.fixture
def cleanup(token):
    """Collects IDs of bookings the API wrongly accepted, and deletes them after."""
    created = []
    yield created
    for booking_id in created:
        requests.delete(f"{BASE_URL}/booking/{booking_id}",
                        headers={"Cookie": f"token={token}"})


@pytest.mark.parametrize("payload",
                         [p for _, p in BAD_PAYLOADS],
                         ids=[name for name, _ in BAD_PAYLOADS])
def test_invalid_booking_is_rejected_with_400(payload, cleanup):
    r = requests.post(f"{BASE_URL}/booking", json=payload, headers=HEADERS)

    if r.status_code in (200, 201):
        cleanup.append(r.json()["bookingid"])

    assert r.status_code == 400, f"Got {r.status_code}: {r.text[:150]}"