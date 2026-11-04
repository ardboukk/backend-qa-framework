import time
import requests

URL = "https://restful-booker.herokuapp.com/ping"

start = time.time()
codes = [requests.get(URL).status_code for _ in range(3)]
elapsed = time.time() - start

print("codes:", codes)
print("elapsed:", round(elapsed, 2), "seconds")