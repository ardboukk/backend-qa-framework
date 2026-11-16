import psycopg
import pytest

from tests.clients.bank_client import BankClient
from tests.config import BANK_DB_DSN
from tests.db.helpers import unique_owner


@pytest.fixture
def bank(request):
    """A bank-api client whose request IDs carry this test's name."""
    return BankClient(tag=request.node.name)


@pytest.fixture
def db():
    """Direct connection to Postgres, bypassing the API."""
    with psycopg.connect(BANK_DB_DSN, autocommit=True) as conn:
        yield conn


@pytest.fixture
def make_account(bank):
    """Factory: create an account with a unique owner and return its id."""
    def _make(balance=100):
        r = bank.create_account(unique_owner(), balance)
        assert r.status_code == 201, f"setup failed: {r.status_code} {r.text}"
        return r.json()["id"]
    return _make