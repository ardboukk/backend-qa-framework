import requests

BASE_URL = "https://restful-booker.herokuapp.com"

response = requests.post(
    f"{BASE_URL}/auth",
    json={"username": "admin", "password": "password123"},
)

print("Status:", response.status_code)
print("Body:", response.json())
#print("Token:", response.json().get("token"))
token = response.json().get("token")
if token is None:
    print("Login failed:", response.json().get("reason"))
else:
    print("Login OK, token:", token)