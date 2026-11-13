import requests

Base_URL = "https://restful-booker.herokuapp.com/booking/1"

response = requests.get(
	f"{Base_URL}"
)

print("status:", response.status_code)
print("firstname:", response.json()["firstname"])