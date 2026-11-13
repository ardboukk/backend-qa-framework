"""Where every test finds its servers. Override any value with an environment variable."""
import os

BOOKER_URL = os.getenv("BOOKER_URL", "https://restful-booker.herokuapp.com")
BANK_API_URL = os.getenv("BANK_API_URL", "http://localhost:8081")
BANK_DB_DSN = os.getenv("BANK_DB_DSN", "postgresql://qa:qa_local_only@localhost:5433/bank")
RATELIMIT_URL = os.getenv("RATELIMIT_URL", "http://localhost:3000")
MOCK_PAYMENT_URL = os.getenv("MOCK_PAYMENT_URL", "http://localhost:4000")

JSON_HEADERS = {"Accept": "application/json"}
