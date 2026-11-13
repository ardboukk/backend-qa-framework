import pytest

@pytest.fixture
def booking():
    print("\n  SETUP")
    yield {"firstname": "Abed", "totalprice": 150, "depositpaid": True}
    print("\n  TEARDOWN")

def test_firstname_is_abed(booking):
    assert booking["firstname"] == "Abed"

def test_price_can_be_changed(booking):
    booking["totalprice"] = 300
    assert booking["totalprice"] == 300

def test_price_is_still_150(booking):
    assert booking["totalprice"] == 150
    