"""
Concurrency checks for /transfer: many identical requests at the same instant.

    pytest tests/db/test_bank_concurrency.py -v
"""
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import psycopg
import pytest
import requests

API = os.getenv("BANK_API_URL", "http://localhost:8081")
DB_DSN = os.getenv("BANK_DB_DSN", "postgresql://qa:qa_local_only@localhost:5433/bank")
N = 20  # simultaneous requests


@pytest.fixture
def db():
    with psycopg.connect(DB_DSN, autocommit=True) as conn:
        yield conn


def new_account(balance):
    r = requests.post(
        f"{API}/accounts",
        json={"owner": f"qa-{uuid.uuid4().hex[:8]}", "initial_balance": balance},
        timeout=5,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def balances(db, ids):
    rows = db.execute(
        "SELECT id, balance FROM accounts WHERE id = ANY(%s)", (ids,)
    ).fetchall()
    return dict(rows)


def fire_at_once(calls):
    """Release every call at the same instant; return their HTTP status codes."""
    barrier = threading.Barrier(len(calls), timeout=10)

    def run(call):
        barrier.wait()  # each thread waits here until all are ready, then all go
        return call().status_code

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        return list(pool.map(run, calls))


def test_concurrent_transfers_cannot_overspend(db):
    sender = new_account(100)
    receivers = [new_account(0) for _ in range(N)]
    all_ids = [sender] + receivers
    total_before = sum(balances(db, all_ids).values())

    # One transfer of 100 to each receiver: only ONE can be affordable
    calls = [
        lambda to=to: requests.post(
            f"{API}/transfer",
            json={"from_id": sender, "to_id": to, "amount": 100},
            timeout=10,
        )
        for to in receivers
    ]
    statuses = fire_at_once(calls)

    after = balances(db, all_ids)
    total_after = sum(after.values())
    sent_count, sent_sum = db.execute(
        "SELECT count(*), coalesce(sum(amount), 0) FROM transfers WHERE from_id = %s",
        (sender,),
    ).fetchone()

    summary = (
        f"\n  statuses: 201 x{statuses.count(201)}, 422 x{statuses.count(422)}, "
        f"other {[s for s in statuses if s not in (201, 422)]}"
        f"\n  total money: before {total_before}, after {total_after}"
        f"\n  sender balance: {after[sender]}"
        f"\n  transfer records from sender: {sent_count}, totalling {sent_sum}"
    )

    # Data first: money conserved, ledger matches balances
    assert total_after == total_before, "money was created or destroyed" + summary
    assert Decimal("100.00") - sent_sum == after[sender], "ledger does not match balance" + summary
    # Then the contract: exactly one success, everyone else refused
    assert statuses.count(201) == 1, "exactly one transfer should succeed" + summary
    assert statuses.count(422) == N - 1, "the rest should be refused" + summary

def test_opposite_transfers_do_not_deadlock(db):
    a, b = new_account(1000), new_account(1000)

    # Half go A->B, half go B->A, all at the same instant
    calls = [
        lambda i=i: requests.post(
            f"{API}/transfer",
            json={
                "from_id": a if i % 2 == 0 else b,
                "to_id": b if i % 2 == 0 else a,
                "amount": 10,
            },
            timeout=10,
        )
        for i in range(N)
    ]
    statuses = fire_at_once(calls)

    after = balances(db, [a, b])
    summary = (
        f"\n  statuses: 201 x{statuses.count(201)}, "
        f"other {[s for s in statuses if s != 201]}"
        f"\n  balances: a={after[a]}, b={after[b]}"
    )
    assert sum(after.values()) == Decimal("2000.00"), "money changed" + summary
    assert after[a] == after[b] == Decimal("1000.00"), "10 each way should cancel out" + summary
    assert statuses.count(201) == N, "every transfer is affordable; all must succeed" + summary
