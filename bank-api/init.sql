CREATE TABLE accounts (
  id         SERIAL PRIMARY KEY,
  owner      TEXT NOT NULL,
  balance    NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (balance >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE transfers (
  id         SERIAL PRIMARY KEY,
  from_id    INT NOT NULL REFERENCES accounts(id),
  to_id      INT NOT NULL REFERENCES accounts(id),
  amount     NUMERIC(12,2) NOT NULL CHECK (amount > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
