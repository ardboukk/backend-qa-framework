import http from "k6/http";
import { check, group, sleep } from "k6";
import { SharedArray } from "k6/data";
import exec from "k6/execution";

const BASE = "http://localhost:5050";
const users = new SharedArray("users", function () {
  return JSON.parse(open("./data/users.json"));
});

function hold(vus) {
  return [
    { target: vus, duration: "20s" },
    { target: vus, duration: "1m" },
    { target: 0, duration: "10s" },
  ];
}

export const options = {
  scenarios: {
    browsers:       { executor: "ramping-vus", exec: "browser",      stages: hold(18) },
    buyers:         { executor: "ramping-vus", exec: "buyer",        stages: hold(9) },
    order_checkers: { executor: "ramping-vus", exec: "orderChecker", stages: hold(3) },
  },
  thresholds: {
    checks: ["rate>0.99"],
    "http_req_duration{scenario:browsers}": ["p(95)<200"],
    "http_req_duration{scenario:buyers}": ["p(95)<200"],
    "http_req_duration{scenario:order_checkers}": ["p(95)<200"],
  },
};

function thinkTime() {
  sleep(1 + Math.random() * 2);
}

let token = null; // one session per VU

function login() {
  const user = users[(exec.vu.idInTest - 1) % users.length];
  const res = http.post(
    `${BASE}/login`,
    JSON.stringify({ username: user.username, password: user.password }),
    { headers: { "Content-Type": "application/json" }, tags: { name: "login" } }
  );
  check(res, { "login 200": (r) => r.status === 200 });
  token = res.json("token");
}

function getOrders() {
  const res = http.get(`${BASE}/orders`, {
    headers: { Authorization: `Bearer ${token}` },
    tags: { name: "orders" },
  });
  check(res, { "orders 200": (r) => r.status === 200 });
}

// 60%: look around, never log in
export function browser() {
  group("browse", () => check(http.get(`${BASE}/fast`, { tags: { name: "browse" } }), { "browse 200": (r) => r.status === 200 }));
  thinkTime();
  group("view product", () => check(http.get(`${BASE}/io`, { tags: { name: "product" } }), { "product 200": (r) => r.status === 200 }));
  thinkTime();
}

// 30%: full purchase
export function buyer() {
  if (!token) { group("login", login); thinkTime(); }
  group("browse", () => check(http.get(`${BASE}/fast`, { tags: { name: "browse" } }), { "browse 200": (r) => r.status === 200 }));
  thinkTime();
  group("view product", () => check(http.get(`${BASE}/io`, { tags: { name: "product" } }), { "product 200": (r) => r.status === 200 }));
  thinkTime();
  group("my orders", getOrders);
  thinkTime();
  group("checkout", () => check(http.get(`${BASE}/db`, { tags: { name: "checkout" } }), { "checkout 200": (r) => r.status === 200 }));
  thinkTime();
}

// 10%: log in, check orders, leave
export function orderChecker() {
  if (!token) { group("login", login); }
  group("my orders", getOrders);
  thinkTime();
}
