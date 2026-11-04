const express = require("express");
const app = express();

let flakyCalls = 0;

// ✅ Normal: payment succeeds
app.get("/pay", (req, res) => {
  res.json({ status: "paid" });
});

// 🐢 Slow: answers after 5 seconds
app.get("/pay/slow", (req, res) => {
  setTimeout(() => res.json({ status: "paid" }), 5000);
});

// ❌ Down: service unavailable
app.get("/pay/down", (req, res) => {
  res.status(503).json({ error: "payment service unavailable" });
});

// 🔁 Flaky: fails the first time, works the second time
app.get("/pay/flaky", (req, res) => {
  flakyCalls++;
  if (flakyCalls % 2 === 1) {
    return res.status(503).json({ error: "temporary failure", attempt: flakyCalls });
  }
  res.json({ status: "paid", attempt: flakyCalls });
});

// 💥 Reset: cuts the connection without answering
app.get("/pay/reset", (req, res) => {
  req.socket.destroy();
});

app.listen(4000, () => console.log("Mock payment service on http://localhost:4000"));