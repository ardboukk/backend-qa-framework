import pytest
import requests
from conftest import BASE_URL, HEADERS

# Known defects in Restful-Booker, documented in the defect log
BUG_13 = "BUG-13: missing or wrong-type required fields crash the server (500 instead of 400)"
BUG_14 = "BUG-14: invalid business values are accepted (200 instead of 400)"
BUG_15 = "BUG-15: invalid types are silently converted (200 instead of 400)"


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


# ---- The negative payload library: (test name, payload, known defect) ----
BAD_PAYLOADS = [
    ("empty body",              {},                                       BUG_13),
    ("missing firstname",       without("firstname"),                     BUG_13),
    ("missing totalprice",      without("totalprice"),                    BUG_13),
    ("missing bookingdates",    without("bookingdates"),                  BUG_13),
    ("firstname is a number",   with_value("firstname", 123),             BUG_13),
    ("empty firstname",         with_value("firstname", ""),              BUG_14),
    ("price is negative",       with_value("totalprice", -100),           BUG_14),
    ("checkout before checkin", with_dates("2026-11-10", "2026-11-01"),   BUG_14),
    ("price is text",           with_value("totalprice", "abc"),          BUG_15),
    ("depositpaid is text",     with_value("depositpaid", "yes"),         BUG_15),
    ("checkin not a date",      with_dates("not-a-date", "2026-11-05"),   BUG_15),
]


@pytest.fixture
def cleanup(token):
    """Collects IDs of bookings the API wrongly accepted, and deletes them after."""
    created = []
    yield created
    for booking_id in created:
        requests.delete(f"{BASE_URL}/booking/{booking_id}",
                        headers={"Cookie": f"token={token}"})


@pytest.mark.parametrize("payload", [
    pytest.param(payload, id=name, marks=pytest.mark.xfail(reason=bug, strict=True))
    for name, payload, bug in BAD_PAYLOADS
])
def test_invalid_booking_is_rejected_with_400(payload, cleanup):
    r = requests.post(f"{BASE_URL}/booking", json=payload, headers=HEADERS)

    if r.status_code in (200, 201):
        cleanup.append(r.json()["bookingid"])

    assert r.status_code == 400, f"Got {r.status_code}: {r.text[:150]}"
