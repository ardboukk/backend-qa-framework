import time

READY_AT = time.time() + 3          # pretend the file finishes processing in 3 seconds


def is_done():
    return time.time() >= READY_AT  # True once 3 seconds have passed


# ── Approach 1: fixed sleep ──
start = time.time()
time.sleep(60)
print("SLEEP:  done =", is_done(), "after", round(time.time() - start), "seconds")

# ── Approach 2: poll with a timeout ──
READY_AT = time.time() + 3
start = time.time()
deadline = time.time() + 60

while time.time() < deadline:
    if is_done():
        break                        # ready: stop waiting immediately
    time.sleep(1)                    # not yet: check again in 1 second

print("POLL:   done =", is_done(), "after", round(time.time() - start), "seconds")