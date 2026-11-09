import http from "k6/http";
import { check, sleep } from "k6";
import exec from "k6/execution";

const BASE = "http://localhost:5050";
export const options = { vus: 5, duration: "20s" };

// Runs ONCE before any VU starts
export function setup() {
  const health = http.get(`${BASE}/fast`);
  if (health.status !== 200) {
    exec.test.abort(`Server not healthy (status ${health.status}): stopping before load`);
  }
  const login = http.post(
    `${BASE}/login`,
    JSON.stringify({ username: "user1", password: "pass1" }),
    { headers: { "Content-Type": "application/json" } }
  );
  const before = http.get(`${BASE}/metrics`).json();
  console.log(`setup: server healthy, heap ${before.heap_used_mb} MB`);
  return { token: login.json("token"), heapBefore: before.heap_used_mb };
}

// Runs in every VU, many times. Receives what setup() returned.
export default function (data) {
  const res = http.get(`${BASE}/orders`, {
    headers: { Authorization: `Bearer ${data.token}` },
  });
  check(res, { "orders 200 with shared token": (r) => r.status === 200 });
  sleep(1);
}

// Runs ONCE after all VUs finish
export function teardown(data) {
  const after = http.get(`${BASE}/metrics`).json();
  console.log(`teardown: heap before ${data.heapBefore} MB, after ${after.heap_used_mb} MB`);
}
