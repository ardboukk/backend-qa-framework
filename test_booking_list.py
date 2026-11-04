import requests
from conftest import BASE_URL

def test_get_all_bookings_returns_list_of_ids():
    # Sends a GET to https://restful-booker.herokuapp.com/booking with a 10 second timeout
    response = requests.get(f"{BASE_URL}/booking", timeout=10)
    
    # Asserts the status is 200
    assert response.status_code == 200
    
    # Asserts the response body is a list
    response_body = response.json()
    assert isinstance(response_body, list)
    
    # Asserts the list is not empty
    assert len(response_body) > 0
    
    # Loops through every item with informative error messages
    for item in response_body:
        assert "bookingid" in item, f"Missing bookingid in {item}"
        assert isinstance(item["bookingid"], int), f"Not an int: {item}"
