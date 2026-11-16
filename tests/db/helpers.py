"""Plain helper functions for bank tests. Fixtures live in conftest.py; import these."""
import uuid


def unique_owner():
    return f"qa-{uuid.uuid4().hex[:8]}"


def db_balance(db, account_id):
    row = db.execute("SELECT balance FROM accounts WHERE id = %s", (account_id,)).fetchone()
    assert row is not None, f"account {account_id} not found in DB"
    return row[0]  # Decimal, exact


def balances(db, ids):
    rows = db.execute("SELECT id, balance FROM accounts WHERE id = ANY(%s)", (list(ids),)).fetchall()
    return dict(rows)


def transfer_count(db, *account_ids):
    ids = list(account_ids)
    return db.execute(
        "SELECT count(*) FROM transfers WHERE from_id = ANY(%s) OR to_id = ANY(%s)",
        (ids, ids),
    ).fetchone()[0]