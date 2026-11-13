import hmac
import hashlib

SECRET = b"whsec_my_shared_secret"          # shared by the provider and your app (b"..." = bytes)


def sign(body):
    """What the PROVIDER does: create a signature for the message."""
    return hmac.new(SECRET, body, hashlib.sha256).hexdigest()


def is_genuine(body, signature):
    """What YOUR APP does: recalculate, and compare."""
    expected = sign(body)
    return hmac.compare_digest(expected, signature)


# 1. A real webhook from the provider
body = b'{"order_id": 55, "amount": 500}'
signature = sign(body)
print("Signature:", signature)
print("1. Real webhook accepted?     ", is_genuine(body, signature))

# 2. An attacker changes the amount, keeping the real signature
tampered = b'{"order_id": 55, "amount": 5}'
print("2. Tampered webhook accepted? ", is_genuine(tampered, signature))

# 3. An attacker invents a signature
print("3. Fake signature accepted?   ", is_genuine(body, "abc123"))

# 4. An attacker REPLAYS the real webhook, an hour later
print("4. Replayed webhook accepted? ", is_genuine(body, signature))

processed_ids = set()          # like a list, but each value can only appear once


def handle_webhook(event_id, body, signature):
    if not is_genuine(body, signature):
        return "401 rejected: bad signature"
    if event_id in processed_ids:
        return "200 ignored: already processed"
    processed_ids.add(event_id)
    return "200 processed: payment recorded"


print()
print("First delivery:  ", handle_webhook("evt_123", body, signature))
print("Replay/duplicate:", handle_webhook("evt_123", body, signature))
print("Tampered:        ", handle_webhook("evt_456", tampered, signature))