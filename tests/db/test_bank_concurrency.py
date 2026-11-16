"""
Concurrency checks for /transfer: many requests released at the same instant.

    pytest tests/db/test_bank_concurrency.py -v
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import psycopg
import pytest
import requests

from tests.config import BANK_DB_DSN
from tests.db.helpers import balances

N = 20  # simultaneous requests

# These tests fill the API's DB pool on purpose: never run them in parallel with others
pytestmark = pytest.mark.serial


def fire_at_once_timed(calls):
    """Release every call at the same instant; return (status, seconds) for each."""
    barrier = threading.Barrier(len(calls), timeout=10)

    def run(call):
        barrier.wait()  # each thread waits here until all are ready, then all go
        start = time.monotonic()
        try:
            status = call().status_code
        except requests.exceptions.Timeout:
            status = "timeout"  # record it, don't crash: we want the full picture
        return status, round(time.monotonic() - start, 2)

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        return list(pool.map(run, calls))


def fire_at_once(calls):
    """Same, status codes only."""
    return [status for status, _ in fire_at_once_timed(calls)]


def test_concurrent_transfers_cannot_overspend(db, bank, make_account):
    sender = make_account(100)
    receivers = [make_account(0) for _ in range(N)]
    all_ids = [sender] + receivers
    total_before = sum(balances(db, all_ids).values())

    # One transfer of 100 to each receiver: only ONE can be affordable
    statuses = fire_at_once([lambda to=to: bank.transfer(sender, to, 100) for to in receivers])

    after = balances(db, all_ids)
    total_after = sum(after.values())
    sent_count, sent_sum = db.execute(
        "SELECT count(*), coalesce(sum(amount), 0) FROM transfers WHERE from_id = %s", (sender,)
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


def test_opposite_transfers_do_not_deadlock(db, bank, make_account):
    a, b = make_account(1000), make_account(1000)

    # Half go A->B, half go B->A, all at the same instant
    statuses = fire_at_once([
        lambda i=i: bank.transfer(a if i % 2 == 0 else b, b if i % 2 == 0 else a, 10)
        for i in range(N)
    ])

    after = balances(db, [a, b])
    summary = (
        f"\n  statuses: 201 x{statuses.count(201)}, other {[s for s in statuses if s != 201]}"
        f"\n  balances: a={after[a]}, b={after[b]}"
    )
    assert sum(after.values()) == Decimal("2000.00"), "money changed" + summary
    assert after[a] == after[b] == Decimal("1000.00"), "10 each way should cancel out" + summary
    assert statuses.count(201) == N, "every transfer is affordable; all must succeed" + summary


def test_locked_account_fails_fast_and_does_not_stall_others(bank, make_account):
    hot, payer, bystander = make_account(100), make_account(100), make_account(0)

    # Simulate a long-running transaction holding a lock on the hot account
    lock_conn = psycopg.connect(BANK_DB_DSN)  # NOT autocommit: the transaction stays open
    try:
        lock_conn.execute("SELECT id FROM accounts WHERE id = %s FOR UPDATE", (hot,))
        transfers = [lambda: bank.transfer(payer, hot, 1) for _ in range(12)]  # > 10 pool connections
        read = [lambda: bank.get_account(bystander)]
        results = fire_at_once_timed(transfers + read)
    finally:
        lock_conn.rollback()
        lock_conn.close()

    transfer_results, (read_status, read_secs) = results[:-1], results[-1]
    statuses = [status for status, _ in transfer_results]
    slowest = max(secs for _, secs in transfer_results)
    summary = f"\n  transfers: {transfer_results}\n  read: {read_status} in {read_secs}s"

    # Design: 2 s timeout per statement, pool of 10, 12 transfers -> at most 2 waves
    assert read_status == 200, "unrelated read failed" + summary
    assert read_secs < 2.5, "unrelated read was stalled by a lock on another account" + summary
    assert set(statuses) == {503}, "locked account should return 503 (busy)" + summary
    assert slowest < 5, "a transfer waited longer than 2 waves x 2 s" + summary