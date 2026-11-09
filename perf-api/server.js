const express = require("express");
const crypto = require("crypto");
const app = express();
app.use(express.json());

// Baseline: no work at all
app.get("/fast", (req, res) => {
  res.json({ ok: true });
});

// CPU-bound: keeps the single thread busy
app.get("/cpu", (req, res) => {
  let hash = "start";
  for (let i = 0; i < 20000; i++) {
    hash = crypto.createHash("sha256").update(hash).digest("hex");
  }
  res.json({ hash: hash.slice(0, 12) });
});

// I/O-bound: waits 80-120 ms without blocking (like calling another service)
app.get("/io", (req, res) => {
  const delay = 80 + Math.floor(Math.random() * 40);
  setTimeout(() => {
    res.json({ waited_ms: delay });
  }, delay);
});

// Pool-bound: a fake database with only 5 connections, each query takes 50 ms
const POOL_SIZE = 5;
const MAX_QUEUE = 50; // load shedding: max requests allowed to wait
let inUse = 0;
const waiting = [];

function getConnection() {
  return new Promise((resolve) => {
    if (inUse < POOL_SIZE) {
      inUse++;
      resolve();
    } else {
      waiting.push(resolve);
    }
  });
}

function releaseConnection() {
  const next = waiting.shift();
  if (next) {
    next();
  } else {
    inUse--;
  }
}

app.get("/db", async (req, res) => {
  // Load shedding: if the pool is busy and the queue is full, refuse fast
  if (inUse >= POOL_SIZE && waiting.length >= MAX_QUEUE) {
    res.set("Retry-After", "1");
    return res.status(503).json({ error: "busy, try again shortly" });
  }
  const queuedAt = Date.now();
  await getConnection();
  const poolWait = Date.now() - queuedAt;
  setTimeout(() => {
    releaseConnection();
    res.json({ pool_wait_ms: poolWait, still_queued: waiting.length });
  }, 50);
});

// Report cache: was an unbounded leak (found by perf/soak.js), now capped at 1000 entries
const reportCache = new Map();
let reportCounter = 0;
app.get("/report", (req, res) => {
  reportCounter++;
  const report = crypto.randomBytes(2500).toString("hex"); // about 5 KB per report
  reportCache.set(reportCounter, report);
  // FIX: bounded cache - keep at most 1000 reports, evict the oldest
  if (reportCache.size > 1000) {
    const oldestKey = reportCache.keys().next().value;
    reportCache.delete(oldestKey);
  }
  res.json({ id: reportCounter, size: report.length });
});

// Metrics: lets tests watch the server's memory from the outside
app.get("/metrics", (req, res) => {
  const m = process.memoryUsage();
  res.json({
    rss_mb: Number((m.rss / 1048576).toFixed(1)),
    heap_used_mb: Number((m.heapUsed / 1048576).toFixed(1)),
    cache_entries: reportCache.size,
  });
});

// Level 3: simple login + protected endpoint
const USERS = {};
for (let i = 1; i <= 50; i++) USERS[`user${i}`] = `pass${i}`;
const sessions = new Map(); // token -> username

app.post("/login", (req, res) => {
  const { username, password } = req.body || {};
  if (!USERS[username] || USERS[username] !== password) {
    return res.status(401).json({ error: "invalid credentials" });
  }
  const token = crypto.randomBytes(16).toString("hex");
  sessions.set(token, username);
  res.json({ token });
});

app.get("/orders", (req, res) => {
  const auth = req.get("Authorization") || "";
  const user = sessions.get(auth.replace("Bearer ", ""));
  if (!user) return res.status(401).json({ error: "not logged in" });
  setTimeout(() => res.json({ user, orders: [{ id: 1, total: 42 }] }), 30);
});

app.listen(5000, () => {
  console.log("perf-api on 5000");
});
