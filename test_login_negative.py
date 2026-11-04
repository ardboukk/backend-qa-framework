import pytest
import requests
from conftest import BASE_URL, HEADERS

@pytest.mark.xfail(reason="BUG-1: failed login returns 200 instead of 401")

@pytest.mark.parametrize("username, password", [
    ("admin", "wrong"),          # right username, wrong password
    ("Test", "password123"),     # wrong username, right password
    ("admin", ""),           # empty password
    ("", ""),            # both empty
])
def test_bad_login_is_rejected(username, password):
    r = requests.post(f"{BASE_URL}/auth",
                      json={"username": username, "password": password})

    assert "token" not in r.json()
    assert r.status_code == 401