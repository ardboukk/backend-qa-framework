import pytest

# ─── PART 1: the code being tested ───
def classify(code):
    if code < 300:
        return "success"
    elif code < 500:
        return "client error"
    else:
        return "server error"


# ─── PART 2: the tests ───

@pytest.mark.parametrize("code, expected", [
    (200, "success"),
    (404, "client error"),
    (500, "server error"),
    (499, "client error"),
    (201, "success"),
    (300, "client error"),
])
def test_classify(code, expected):
    assert classify(code) == expected

