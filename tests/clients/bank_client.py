"""One place that knows how to talk to bank-api. Tests call methods, not URLs."""
import re
import uuid

import requests

from tests.config import BANK_API_URL

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")  # same rule as the server's SAFE_ID


class BankClient:
    def __init__(self, base_url=BANK_API_URL, tag="manual", timeout=10):
        self.base_url = base_url.rstrip("/")
        self.tag = _UNSAFE.sub("_", tag)[:52]
        self.timeout = timeout

    def _request(self, method, path, **kwargs):
        # Tag every request so test traffic can be found (or filtered out) in the logs.
        # A caller's own X-Request-Id header wins over the tag.
        headers = {"X-Request-Id": f"qa-{self.tag}-{uuid.uuid4().hex[:8]}"}
        headers.update(kwargs.pop("headers", {}))
        timeout = kwargs.pop("timeout", self.timeout)
        # requests.request, not a shared Session: safe to call from many threads at once
        return requests.request(method, f"{self.base_url}{path}",
                                headers=headers, timeout=timeout, **kwargs)

    def health(self, **kwargs):
        return self._request("GET", "/health", **kwargs)

    def create_account(self, owner, initial_balance, **kwargs):
        return self._request("POST", "/accounts",
                             json={"owner": owner, "initial_balance": initial_balance}, **kwargs)

    def get_account(self, account_id, **kwargs):
        return self._request("GET", f"/accounts/{account_id}", **kwargs)

    def transfer(self, from_id, to_id, amount, **kwargs):
        return self._request("POST", "/transfer",
                             json={"from_id": from_id, "to_id": to_id, "amount": amount}, **kwargs)