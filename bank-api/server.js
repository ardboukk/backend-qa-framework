const express = require("express");
const { Pool } = require("pg");

const app = express();
app.use(express.json());

const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 10 });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Money: non-negative, at most 2 decimals, fits NUMERIC(12,2)
const MONEY = /^\d{1,10}(\.\d{1,2})?$/;
const isMoney = (x) => typeof x === "number" && MONEY.test(String(x));

app.get("/health", async (req, res) => {
  try {
    await pool.query("SELECT 1");
    res.json({ ok: true });
  } catch {
    res.status(503).json({ ok: false });
  }
});

// Create an account
app.post("/accounts", async (req, res) => {
  const { owner, initial_balance } = req.body;
  if (typeof owner !== "string" || owner.trim() === "") {
    return res.status(400).json({ error: "owner is required" });
  }
  if (!isMoney(initial_balance)) {
    return res.status(400).json({ error: "initial_balance must be a non-negative amount with at most 2 decimals" });
  }
  try {
    const result = await pool.query(
      "INSERT INTO accounts (owner, balance) VALUES ($1, $2) RETURNING id, owner, balance",
      [owner, initial_balance]
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error("create account failed:", err.message);
    res.status(500).json({ error: "internal error" });
  }
});

// Read an account
app.get("/accounts/:id", async (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ error: "invalid id" });
  try {
    const result = await pool.query(
      "SELECT id, owner, balance FROM accounts WHERE id = $1", [id]
    );
    if (result.rowCount === 0) return res.status(404).json({ error: "not found" });
    res.json(result.rows[0]);
  } catch (err) {
    console.error("read account failed:", err.message);
    res.status(500).json({ error: "internal error" });
  }
});

// Transfer money between accounts
app.post("/transfer", async (req, res) => {
  const { from_id, to_id, amount } = req.body;
  if (!Number.isInteger(from_id) || !Number.isInteger(to_id)) {
    return res.status(400).json({ error: "from_id and to_id must be integers" });
  }
  if (from_id === to_id) return res.status(400).json({ error: "cannot transfer to same account" });
  if (!isMoney(amount) || amount <= 0) {
    return res.status(400).json({ error: "amount must be a positive amount with at most 2 decimals" });
  }

  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const from = await client.query("SELECT id, balance FROM accounts WHERE id = $1", [from_id]);
    const to = await client.query("SELECT id, balance FROM accounts WHERE id = $1", [to_id]);
    if (from.rowCount === 0 || to.rowCount === 0) {
      await client.query("ROLLBACK");
      return res.status(404).json({ error: "account not found" });
    }

    const fromBalance = Number(from.rows[0].balance);
    const toBalance = Number(to.rows[0].balance);
    if (fromBalance < amount) {
      await client.query("ROLLBACK");
      return res.status(422).json({ error: "insufficient funds" });
    }

    await sleep(20); // simulates a fraud check call

    await client.query("UPDATE accounts SET balance = $1 WHERE id = $2", [fromBalance - amount, from_id]);
    await client.query("UPDATE accounts SET balance = $1 WHERE id = $2", [toBalance + amount, to_id]);
    const t = await client.query(
      "INSERT INTO transfers (from_id, to_id, amount) VALUES ($1, $2, $3) RETURNING id",
      [from_id, to_id, amount]
    );
    await client.query("COMMIT");
    res.status(201).json({ transfer_id: t.rows[0].id, from_id, to_id, amount });
  } catch (err) {
    await client.query("ROLLBACK");
    console.error("transfer failed:", err.message);
    res.status(500).json({ error: "internal error" });
  } finally {
    client.release();
  }
});

app.listen(8080, () => console.log("bank-api listening on 8080"));