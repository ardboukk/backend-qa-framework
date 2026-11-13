const express = require("express");
const { Pool } = require("pg");

const app = express();
app.use(express.json());

// ---------- Request IDs + structured logs ----------
const crypto = require("crypto");
const SAFE_ID = /^[A-Za-z0-9._-]{1,64}$/; // blocks log injection via the header

// One JSON object per line: easy to search, filter and ship to a log system
function log(level, msg, fields = {}) {
  console.log(JSON.stringify({ ts: new Date().toISOString(), level, msg, ...fields }));
}

app.use((req, res, next) => {
  const incoming = req.get("X-Request-Id");
  req.id = incoming && SAFE_ID.test(incoming) ? incoming : crypto.randomUUID();
  res.set("X-Request-Id", req.id);

  // Every error body carries the id, so a customer can quote it to support
  const json = res.json.bind(res);
  res.json = (body) =>
    json(res.statusCode >= 400 && body && typeof body === "object"
      ? { ...body, request_id: req.id }
      : body);

  // One access-log line per request
  const start = process.hrtime.bigint();
  res.on("finish", () => {
    if (req.path === "/metrics") return; // scrapes every 5 s would drown the log
    log(res.statusCode >= 500 ? "error" : "info", "request", {
      request_id: req.id,
      method: req.method,
      route: req.route ? req.route.path : "unmatched",
      status: res.statusCode,
      duration_ms: Math.round(Number(process.hrtime.bigint() - start) / 1e5) / 10,
    });
  });
  next();
});

// ---------- Metrics (Prometheus) ----------
const promClient = require("prom-client");
promClient.collectDefaultMetrics(); // CPU, memory, event-loop lag, GC

const httpDuration = new promClient.Histogram({
  name: "http_request_duration_seconds",
  help: "HTTP request duration in seconds",
  labelNames: ["method", "route", "status"],
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5],
});

const transfersTotal = new promClient.Counter({
  name: "bank_transfers_total",
  help: "Transfer attempts by outcome",
  labelNames: ["outcome"],
});
// Create every outcome at 0 so "no errors" reads as 0, not as missing data
for (const outcome of ["success", "insufficient_funds", "not_found", "busy", "error"]) {
  transfersTotal.inc({ outcome }, 0);
}

// Time every request; label by route PATTERN (/accounts/:id), not the real URL
app.use((req, res, next) => {
  const end = httpDuration.startTimer();
  res.on("finish", () => {
    const route = req.route ? req.route.path : "unmatched";
    end({ method: req.method, route, status: res.statusCode });
  });
  next();
});

app.get("/metrics", async (req, res) => {
  res.set("Content-Type", promClient.register.contentType);
  res.end(await promClient.register.metrics());
});

const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 10 });

new promClient.Gauge({
  name: "db_pool_connections",
  help: "DB connection pool: total, idle, and requests waiting for a connection",
  labelNames: ["state"],
  collect() {
    this.set({ state: "total" }, pool.totalCount);
    this.set({ state: "idle" }, pool.idleCount);
    this.set({ state: "waiting" }, pool.waitingCount);
  },
});
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
    log("error", "create account failed", { request_id: req.id, error: err.message, code: err.code });
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
    log("error", "read account failed", { request_id: req.id, error: err.message, code: err.code });
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
    await client.query("SELECT set_config('application_name', $1, true)", [`bank-api ${req.id}`]);
    await client.query("SET LOCAL lock_timeout = '2s'"); // limit for each single lock wait
    await client.query("SET LOCAL statement_timeout = '2s'"); // limit for each whole statement
    await client.query("SET LOCAL statement_timeout = '2s'"); // limit for each whole statement
    // Lock both rows until COMMIT/ROLLBACK, always in id order so two transfers can't deadlock
    const locked = await client.query(
      "SELECT id, balance FROM accounts WHERE id = ANY($1::int[]) ORDER BY id FOR UPDATE",
      [[from_id, to_id]]
    );
    const from = locked.rows.find((r) => r.id === from_id);
    const to = locked.rows.find((r) => r.id === to_id);
    if (!from || !to) {
      await client.query("ROLLBACK");
      transfersTotal.inc({ outcome: "not_found" });
      return res.status(404).json({ error: "account not found" });
    }

    const fromBalance = Number(from.balance);
    const toBalance = Number(to.balance);
    if (fromBalance < amount) {
      await client.query("ROLLBACK");
      transfersTotal.inc({ outcome: "insufficient_funds" });
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
    transfersTotal.inc({ outcome: "success" });
    log("info", "transfer completed", { request_id: req.id, transfer_id: t.rows[0].id, from_id, to_id, amount });
    res.status(201).json({ transfer_id: t.rows[0].id, from_id, to_id, amount });
  } catch (err) {
    await client.query("ROLLBACK");
    if (err.code === "55P03" || err.code === "57014") { // lock_timeout or statement_timeout
      transfersTotal.inc({ outcome: "busy" });
      log("warn", "transfer busy", { request_id: req.id, from_id, to_id, error: err.message });
      res.set("Retry-After", "1");
      return res.status(503).json({ error: "account busy, try again shortly" });
    }
    transfersTotal.inc({ outcome: "error" });
    log("error", "transfer failed", { request_id: req.id, error: err.message, code: err.code });
    res.status(500).json({ error: "internal error" });
  } finally {
    client.release();
  }
});

app.listen(8080, () => console.log("bank-api listening on 8080"));