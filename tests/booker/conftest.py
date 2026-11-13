import uuid                     # a library for random IDs
import pytest                   # Part A/B: pytest's toolbox
import requests                 # Script 1: sends HTTP requests

from tests.config import BOOKER_URL as BASE_URL, JSON_HEADERS as HEADERS


@pytest.fixture(scope="session")                     # Part B: shared, because tests only READ the token
def token():
    r = requests.post(f"{BASE_URL}/auth",            # Script 1: a POST request
                      json={"username": "admin", "password": "password123"})
    assert r.status_code == 200, "Login failed, cannot run tests"   # Script 3: assert with a message
    return r.json()["token"]                         # Script 1: read a key from the JSON


@pytest.fixture                                      # Part B: fresh for every test
def booking_data():
    return {
        "firstname": f"QA-{uuid.uuid4().hex[:6]}",   # an f-string with a random 6-character ID
        "lastname": "Tester",
        "totalprice": 150,
        "depositpaid": True,
        "bookingdates": {"checkin": "2026-11-01", "checkout": "2026-11-05"},
        "additionalneeds": "Breakfast",
    }


@pytest.fixture
def booking(token, booking_data):                    # ⭐ NEW: a fixture that ASKS FOR other fixtures
    r = requests.post(f"{BASE_URL}/booking", json=booking_data, headers=HEADERS)
    booking_id = r.json()["bookingid"]               # SETUP: create a real booking on the server

    yield booking_id                                 # Part B: hand the ID to the test, and pause

    requests.delete(f"{BASE_URL}/booking/{booking_id}",       # TEARDOWN: delete it from the server
                    headers={"Cookie": f"token={token}"})