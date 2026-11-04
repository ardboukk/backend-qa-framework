const express = require("express");
const rateLimit = require("express-rate-limit");

const app = express();

app.use(rateLimit({
  windowMs: 10 * 1000,      // a 10-second window
  limit: 5,                 // 5 requests allowed per window
  standardHeaders: "draft-7",
  legacyHeaders: false,
  message: { error: "Too many requests, slow down" },
}));

app.get("/hello", (req, res) => res.json({ message: "Hello QA!" }));

app.listen(3000, () => console.log("API running on http://localhost:3000"));