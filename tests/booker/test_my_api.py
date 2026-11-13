import requests
from tests.config import BOOKER_URL as BASE_URL, JSON_HEADERS as HEADERS


def test_booking_price_and_deposit(booking, booking_data):
    r = requests.get(f"{BASE_URL}/booking/{booking}", headers=HEADERS)

    assert r.status_code == 200
    assert r.json()["totalprice"] == booking_data["totalprice"]
    assert r.json()["depositpaid"] == True