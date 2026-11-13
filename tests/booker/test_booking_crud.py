import pytest
import requests
from tests.config import BOOKER_URL as BASE_URL, JSON_HEADERS as HEADERS


def test_create_booking_returns_id(booking_data):
    r = requests.post(f"{BASE_URL}/booking", json=booking_data, headers=HEADERS)

    assert r.status_code == 200
    assert isinstance(r.json()["bookingid"], int)
    assert r.json()["booking"] == booking_data


def test_read_booking_returns_saved_data(booking, booking_data):
    r = requests.get(f"{BASE_URL}/booking/{booking}", headers=HEADERS)

    assert r.status_code == 200
    assert r.json() == booking_data
    assert "password" not in r.json()


def test_update_booking_changes_price(booking, booking_data, token):
    booking_data["totalprice"] = 300
    r = requests.put(f"{BASE_URL}/booking/{booking}", json=booking_data,
                     headers={**HEADERS, "Cookie": f"token={token}"})

    assert r.status_code == 200
    assert r.json()["totalprice"] == 300


def test_delete_booking_then_read_returns_404(booking, token):
    requests.delete(f"{BASE_URL}/booking/{booking}",
                    headers={"Cookie": f"token={token}"})
    r = requests.get(f"{BASE_URL}/booking/{booking}", headers=HEADERS)

    assert r.status_code == 404


@pytest.mark.xfail(reason="BUG-2: create returns 200 instead of 201")
def test_create_booking_returns_201(booking_data):
    r = requests.post(f"{BASE_URL}/booking", json=booking_data, headers=HEADERS)
    assert r.status_code == 201