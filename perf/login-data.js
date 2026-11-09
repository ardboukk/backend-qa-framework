import http from "k6/http";
import { check } from "k6";
import { SharedArray } from "k6/data";
import exec from "k6/execution";

// Loaded ONCE, shared read-only by every VU
const users = new SharedArray("users", function () {
  return JSON.parse(open("./data/users.json"));
});

export const options = {
  scenarios: {
    every_user_once: {
      executor: "shared-iterations",
      vus: 10,
      iterations: users.length,
    },
  },
  thresholds: {
    checks: ["rate==1.0"],
  },
};

export default function () {
  // Iteration 0 -> user1, 1 -> user2, ... 49 -> user50 (no repeats)
  const user = users[exec.scenario.iterationInTest];

  const res = http.post(
    "http://localhost:5050/login",
    JSON.stringify({ username: user.username, password: user.password }),
    { headers: { "Content-Type": "application/json" } }
  );

  check(res, {
    "login is 200": (r) => r.status === 200,
    "got a token": (r) => r.json("token") !== undefined,
  });
  console.log(`VU ${exec.vu.idInTest} logged in as ${user.username}`);
}
