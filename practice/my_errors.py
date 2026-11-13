import requests

try:
    r = requests.get("http://localhost:5999/pay", timeout=2)
    print("Status:", r.status_code)
except requests.ConnectionError:
    print("Payment service is DOWN")

print("Script finished normally")