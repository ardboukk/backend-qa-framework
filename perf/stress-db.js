import http from "k6/http";
import { check } from "k6";
import exec from "k6/execution";

// Phase windows in seconds since the start: [name, from, to]
const PHASES = [
  ["normal", 10, 70],
  ["above", 80, 140],
  ["stress", 150, 210],
  ["recovery_early", 215, 245],
  ["recovery_late", 275, 305],
];

const thresholds = {
  http_req_duration: ["p(95)>=0"],
};
for (const [name] of PHASES) {
  thresholds[`http_req_duration{phase:${name}}`] = ["p(95)>=0"];
  thresholds[`http_req_failed{phase:${name}}`] = ["rate>=0"];
}

export const options = {
  scenarios: {
    stress: {
      executor: "ramping-arrival-rate",
      startRate: 0,
      timeUnit: "1s",
      preAllocatedVUs: 800,
      maxVUs: 1500,
      stages: [
        { target: 70, duration: "10s" },
        { target: 70, duration: "60s" },
        { target: 100, duration: "10s" },
        { target: 100, duration: "60s" },
        { target: 130, duration: "10s" },
        { target: 130, duration: "60s" },
        { target: 50, duration: "5s" },
        { target: 50, duration: "90s" },
      ],
    },
  },
  thresholds: thresholds,
};

function currentPhase() {
  const t = (Date.now() - exec.scenario.startTime) / 1000;
  for (const [name, from, to] of PHASES) {
    if (t >= from && t < to) return name;
  }
  return "transition";
}

export default function () {
  const res = http.get("http://localhost:5050/db", {
    tags: { phase: currentPhase() },
    timeout: "5s",
  });
  check(res, { "status is 200": (r) => r.status === 200 });
}
