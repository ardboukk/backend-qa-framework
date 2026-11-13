def valid_booking():
    """A known-good booking. Each negative case breaks ONE thing in it."""
    return {
        "firstname": "QA",
        "lastname": "Negative",
        "totalprice": 100,
        "depositpaid": True,
        "bookingdates": {"checkin": "2026-11-01", "checkout": "2026-11-05"},
    }


def without(field):
    data = valid_booking()     # 1. get a fresh, VALID booking
    del data[field]            # 2. remove ONE field
    return data                # 3. hand back the broken version


def with_value(field, value):
    data = valid_booking()     # 1. get a fresh, VALID booking
    data[field] = value        # 2. replace ONE field's value
    return data                # 3. hand back the broken version

print(without("totalprice"))
print(with_value("depositpaid", "yes"))
print(with_value("firstname", ""))

print("\n--- SHARED version (the wrong way) ---")

SHARED = valid_booking()          # ONE booking, created once

def without_shared(field):
    data = SHARED                 # NOT a fresh copy: the same dictionary every time
    del data[field]
    return data

print(without_shared("totalprice"))
print(without_shared("firstname"))