"""
bank-api <-> Postgres integrity checks.

Needs bank-db and bank-api running:
    docker compose up -d bank-db bank-api
    pytest tests/db -v
"""
import os
import uuid
from decimal import Decimal

import psycopg
import pytest
import requests

API = os.getenv("BANK_API_URL", "http://localhost:8081")
DB_DSN = os.getenv("BANK_DB_DSN", "postgresql://qa:qa_local_only@localhost:5433/bank")


# ---------- helpers ----------

@pytest.fixture
def db():
    """Direct connection to Postgres, bypassing the API."""
    with psycopg.connect(DB_DSN, autocommit=True) as conn:
        yield conn


def db_balance(db, account_id):
    row = db.execute("SELECT balance FROM accounts WHERE id = %s", (account_id,)).fetchone()
    assert row is not None, f"account {account_id} not found in DB"
    return row[0]  # Decimal, exact


def transfer_count(db, *account_ids):
    ids = list(account_ids)
    return db.execute(
        "SELECT count(*) FROM transfers WHERE from_id = ANY(%s) OR to_id = ANY(%s)",
        (ids, ids),
    ).fetchone()[0]


def unique_owner():
    return f"qa-{uuid.uuid4().hex[:8]}"


def create_account(owner, balance):
    return requests.post(
        f"{API}/accounts",
        json={"owner": owner, "initial_balance": balance},
        timeout=5,
    )


@pytest.fixture
def make_account():
    def _make(balance):
        r = create_account(unique_owner(), balance)
        assert r.status_code == 201, f"setup failed: {r.status_code} {r.text}"
        return r.json()["id"]
    return _make


def post_transfer(from_id, to_id, amount):
    return requests.post(
        f"{API}/transfer",
        json={"from_id": from_id, "to_id": to_id, "amount": amount},
        timeout=5,
    )


# ---------- 1. Did it save what the API says it saved? ----------

@pytest.mark.parametrize("balance", [100, 0, 25.5])
def test_created_account_is_stored_as_returned(db, balance):
    owner = unique_owner()
    r = create_account(owner, balance)
    assert r.status_code == 201, r.text
    body = r.json()

    row = db.execute(
        "SELECT owner, balance FROM accounts WHERE id = %s", (body["id"],)
    ).fetchone()
    assert row is not None, "API returned an id that is not in the DB"
    assert row[0] == owner
    assert Decimal(str(body["balance"])) == row[1], (
        f"API said {body['balance']}, DB stored {row[1]}"
    )


def test_sub_cent_balance_is_rejected_or_stored_exactly(db):
    r = create_account(unique_owner(), 100.005)
    if r.status_code == 400:
        return  # rejecting invalid money is acceptable
    assert r.status_code == 201, r.text
    body = r.json()
    stored = db_balance(db, body["id"])
    assert Decimal(str(body["balance"])) == stored, (
        f"API reported {body['balance']} but DB stored {stored} (silent rounding)"
    )


def test_negative_initial_balance_is_rejected_cleanly(db):
    owner = unique_owner()
    r = create_account(owner, -50)

    saved = db.execute(
        "SELECT count(*) FROM accounts WHERE owner = %s", (owner,)
    ).fetchone()[0]
    assert saved == 0, "an account with a negative balance was saved"
    assert r.status_code == 400, (
        f"expected 400 validation error, got {r.status_code}: {r.text}"
    )


# ---------- 2. Transfers: correct, complete, and rule-preserving ----------

def test_transfer_updates_both_balances_in_db(db, make_account):
    a, b = make_account(100), make_account(50)
    r = post_transfer(a, b, 30)
    assert r.status_code == 201, r.text

    assert db_balance(db, a) == Decimal("70.00")
    assert db_balance(db, b) == Decimal("80.00")
    row = db.execute(
        "SELECT from_id, to_id, amount FROM transfers WHERE id = %s",
        (r.json()["transfer_id"],),
    ).fetchone()
    assert row == (a, b, Decimal("30.00")), f"transfer record wrong: {row}"


def test_transfer_conserves_total_money(db, make_account):
    a, b = make_account(100), make_account(50)
    before = db_balance(db, a) + db_balance(db, b)

    r = post_transfer(a, b, 12.34)
    assert r.status_code == 201, r.text

    after = db_balance(db, a) + db_balance(db, b)
    assert after == before, f"money changed: {before} -> {after}"


# ---------- 3. Did a failed request leave nothing behind? ----------

def test_insufficient_funds_changes_nothing(db, make_account):
    a, b = make_account(20), make_account(0)
    r = post_transfer(a, b, 50)
    assert r.status_code == 422, r.text

    assert db_balance(db, a) == Decimal("20.00")
    assert db_balance(db, b) == Decimal("0.00")
    assert transfer_count(db, a, b) == 0


def test_transfer_to_missing_account_changes_nothing(db, make_account):
    a = make_account(100)
    r = post_transfer(a, 999999999, 10)
    assert r.status_code == 404, r.text

    assert db_balance(db, a) == Decimal("100.00")
    assert transfer_count(db, a) == 0


def test_sub_cent_transfer_is_rejected_cleanly(db, make_account):
    a, b = make_account(100), make_account(50)
    r = post_transfer(a, b, 0.001)

    # Data first: a failed request must leave no trace
    assert db_balance(db, a) == Decimal("100.00")
    assert db_balance(db, b) == Decimal("50.00")
    assert transfer_count(db, a, b) == 0
    # Then the contract
    assert r.status_code == 400, (
        f"expected 400 validation error, got {r.status_code}: {r.text}"
    )
    

# ---------- 4. Contract: endpoints agree with each other ----------

def test_post_and_get_return_identical_balance():
    r = create_account(unique_owner(), 42)
    assert r.status_code == 201, r.text
    posted = r.json()["balance"]
    got = requests.get(f"{API}/accounts/{r.json()['id']}", timeout=5).json()["balance"]
    assert posted == got, f"POST returned {posted!r}, GET returned {got!r}"
