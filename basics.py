import requests

BASE_URL = "https://restful-booker.herokuapp.com"

# ---------- 1. VARIABLES & TYPES ----------
# A variable is a named box for a value. Python works out the type itself.
name = "Abed"          # str   (text)       → JSON "Abed"
price = 150            # int   (number)     → JSON 150
paid = True            # bool  (true/false) → JSON true   (capital T in Python!)
print(type(price))     # <class 'int'>

# ---------- 2. DICTIONARIES = JSON objects ----------
# { "key": value } — exactly like the JSON bodies you've been sending.
booking = {
    "firstname": name,
    "lastname": "QA",
    "totalprice": price,
    "depositpaid": paid,
    "bookingdates": {"checkin": "2026-11-01", "checkout": "2026-11-05"},
}
print(booking["firstname"])                    # read a field    → Abed
print(booking["bookingdates"]["checkin"])      # nested field    → 2026-11-01
booking["totalprice"] = 300                    # change a field

# ---------- 3. LISTS = JSON arrays ----------
statuses = ["available", "pending", "sold"]    # like Petstore's enum
print(statuses[0])                             # first item → available
print(len(statuses))                           # how many   → 3

# ---------- 4. IF / ELSE ----------
response = requests.get(f"{BASE_URL}/booking/1")
if response.status_code == 200:
    print("Found it")
elif response.status_code == 404:
    print("Not found")
else:
    print("Unexpected:", response.status_code)

# ---------- 5. LOOPS ----------
# Do the same thing for each item — this is how one test covers many cases.
for status in statuses:
    print(f"Would test pet status: {status}")

# ---------- 6. FUNCTIONS ----------
# Wrap reusable steps in a function, so you write them once.
def get_token():
    r = requests.post(f"{BASE_URL}/auth",
                      json={"username": "admin", "password": "password123"})
    return r.json()["token"]

def create_booking(data):
    r = requests.post(f"{BASE_URL}/booking", json=data,
                      headers={"Accept": "application/json"})
    return r.json()["bookingid"]

token = get_token()
booking_id = create_booking(booking)
print(f"Token {token}, created booking {booking_id}")

# ---------- 7. ASSERT = the check ----------
# assert <something that must be true>, "message if it's not"
# If it's true, nothing happens. If it's false, the program stops with an error.
r = requests.get(f"{BASE_URL}/booking/{booking_id}",
                 headers={"Accept": "application/json"})
assert r.status_code == 200, f"Expected 200, got {r.status_code}"
assert r.json()["totalprice"] == 300, "Price was not saved"
assert r.json()["depositpaid"] == True, "Deposit should be paid"
assert "password" not in r.json(), "Response must not expose a password"
print("✅ All checks passed")

