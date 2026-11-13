codes = [200, 201, 400, 404, 500]

for code in codes:
	if code < 300 :
		print(code, "200 → success")
	elif code < 500 :
		print(code, "400 → client error")
	else:
		print(code, "500 → server error")