# ─── PART 1: THE FUNCTION (the code being tested) ───────────
def classify(code):
    if code < 300:
        return "success"
    elif code < 500:
        return "client error"
    else:
        return "server error"


# ─── PART 2: THE TESTS (they USE the function) ──────────────
assert classify(200) == "success"
assert classify(404) == "client error"
assert classify(500) == "server error"
assert classify(499) == "server error", f"499 should be server error, got {classify(499)}"

print("All tests passed")