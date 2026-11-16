"""
bank-api <-> Postgres integrity checks.

    pytest tests/db/test_bank_db.py -v
"""
from decimal import Decimal

import pytest

from tests.db.helpers import db_balance, transfer_count, unique_owner


# ---------- 1. Did it save what the API says it saved? ----------

@pytest.mark.parametrize("balance", [100, 0, 25.5])
def test_created_account_is_stored_as_returned(db, bank, balance):
    owner = unique_owner()
    r = bank.create_account(owner, balance)
    assert r.status_code == 201, r.text
    body = r.json()

    row = db.execute("SELECT owner, balance FROM accounts WHERE id = %s", (body["id"],)).fetchone()
    assert row is not None, "API returned an id that is not in the DB"
    assert row[0] == owner
    assert Decimal(str(body["balance"])) == row[1], f"API said {body['balance']}, DB stored {row[1]}"


def test_sub_cent_balance_is_rejected_or_stored_exactly(db, bank):
    r = bank.create_account(unique_owner(), 100.005)
    if r.status_code == 400:
        return  # rejecting invalid money is acceptable
    assert r.status_code == 201, r.text
    body = r.json()
    stored = db_balance(db, body["id"])
    assert Decimal(str(body["balance"])) == stored, (
        f"API reported {body['balance']} but DB stored {stored} (silent rounding)"
    )


def test_negative_initial_balance_is_rejected_cleanly(db, bank):
    owner = unique_owner()
    r = bank.create_account(owner, -50)

    saved = db.execute("SELECT count(*) FROM accounts WHERE owner = %s", (owner,)).fetchone()[0]
    assert saved == 0, "an account with a negative balance was saved"
    assert r.status_code == 400, f"expected 400 validation error, got {r.status_code}: {r.text}"


# ---------- 2. Transfers: correct, complete, and rule-preserving ----------

def test_transfer_updates_both_balances_in_db(db, bank, make_account):
    a, b = make_account(100), make_account(50)
    r = bank.transfer(a, b, 30)
    assert r.status_code == 201, r.text

    assert db_balance(db, a) == Decimal("70.00")
    assert db_balance(db, b) == Decimal("80.00")
    row = db.execute(
        "SELECT from_id, to_id, amount FROM transfers WHERE id = %s", (r.json()["transfer_id"],)
    ).fetchone()
    assert row == (a, b, Decimal("30.00")), f"transfer record wrong: {row}"


def test_transfer_conserves_total_money(db, bank, make_account):
    a, b = make_account(100), make_account(50)
    before = db_balance(db, a) + db_balance(db, b)

    r = bank.transfer(a, b, 12.34)
    assert r.status_code == 201, r.text

    after = db_balance(db, a) + db_balance(db, b)
    assert after == before, f"money changed: {before} -> {after}"


# ---------- 3. Did a failed request leave nothing behind? ----------

def test_insufficient_funds_changes_nothing(db, bank, make_account):
    a, b = make_account(20), make_account(0)
    r = bank.transfer(a, b, 50)
    assert r.status_code == 422, r.text

    assert db_balance(db, a) == Decimal("20.00")
    assert db_balance(db, b) == Decimal("0.00")
    assert transfer_count(db, a, b) == 0


def test_transfer_to_missing_account_changes_nothing(db, bank, make_account):
    a = make_account(100)
    r = bank.transfer(a, 999999999, 10)
    assert r.status_code == 404, r.text

    assert db_balance(db, a) == Decimal("100.00")
    assert transfer_count(db, a) == 0


def test_sub_cent_transfer_is_rejected_cleanly(db, bank, make_account):
    a, b = make_account(100), make_account(50)
    r = bank.transfer(a, b, 0.001)

    # Data first: a failed request must leave no trace
    assert db_balance(db, a) == Decimal("100.00")
    assert db_balance(db, b) == Decimal("50.00")
    assert transfer_count(db, a, b) == 0
    # Then the contract
    assert r.status_code == 400, f"expected 400 validation error, got {r.status_code}: {r.text}"


# ---------- 4. Contract: endpoints agree with each other ----------

def test_post_and_get_return_identical_balance(bank):
    r = bank.create_account(unique_owner(), 42)
    assert r.status_code == 201, r.text
    posted = r.json()["balance"]
    got = bank.get_account(r.json()["id"]).json()["balance"]
    assert posted == got, f"POST returned {posted!r}, GET returned {got!r}"