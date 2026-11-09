const express = require("express");
const crypto = require("crypto");
const app = express();

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

app.listen(5000, () => {
  console.log("perf-api on 5000");
});
