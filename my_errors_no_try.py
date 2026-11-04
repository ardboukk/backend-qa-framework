import requests

r = requests.get("http://localhost:5999/pay", timeout=2)
print(r.status_code)

print("Script finished normally")