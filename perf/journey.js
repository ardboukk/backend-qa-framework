import http from "k6/http";
import { check, group, sleep } from "k6";
import { SharedArray } from "k6/data";
import exec from "k6/execution";

const BASE = "http://localhost:5050";
const users = new SharedArray("users", function () {
  return JSON.parse(open("./data/users.json"));
});

export const options = {
  scenarios: {
    shoppers: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { target: 20, duration: "30s" },
        { target: 20, duration: "1m" },
        { target: 0, duration: "15s" },
      ],
    },
  },
  thresholds: {
    checks: ["rate>0.99"],
    "group_duration{group:::1 login}": ["p(95)<200"],
    "group_duration{group:::5 checkout}": ["p(95)<200"],
    "http_req_duration{name:orders}": ["p(95)<150"],
  },
};

function thinkTime() {
  sleep(1 + Math.random() * 2); // a real person pauses 1-3 s
}

// Each VU = one shopper. Its token lives as long as the VU (one session).
let token = null;

export default function () {
  const user = users[(exec.vu.idInTest - 1) % users.length];

  if (!token) {
    group("1 login", function () {
      const res = http.post(
        `${BASE}/login`,
        JSON.stringify({ username: user.username, password: user.password }),
        { headers: { "Content-Type": "application/json" }, tags: { name: "login" } }
      );
      check(res, { "login 200": (r) => r.status === 200 });
      token = res.json("token");
    });
    thinkTime();
  }

  group("2 browse", function () {
    const res = http.get(`${BASE}/fast`, { tags: { name: "browse" } });
    check(res, { "browse 200": (r) => r.status === 200 });
  });
  thinkTime();

  group("3 view product", function () {
    const res = http.get(`${BASE}/io`, { tags: { name: "product" } });
    check(res, { "product 200": (r) => r.status === 200 });
  });
  thinkTime();

  group("4 my orders", function () {
    const res = http.get(`${BASE}/orders`, {
      headers: { Authorization: `Bearer ${token}` },
      tags: { name: "orders" },
    });
    check(res, { "orders 200": (r) => r.status === 200 });
  });
  thinkTime();

  group("5 checkout", function () {
    const res = http.get(`${BASE}/db`, { tags: { name: "checkout" } });
    check(res, { "checkout 200": (r) => r.status === 200 });
  });
  thinkTime();
}
