import http from "k6/http";
import { check } from "k6";
import exec from "k6/execution";

// Measurement windows in seconds since start: [name, from, to]
const PHASES = [
  ["baseline", 8, 30],
  ["spike", 33, 50],
  ["after_0_10", 52, 62],
  ["after_10_30", 62, 82],
  ["after_30_60", 82, 112],
];

const thresholds = {};
for (const [name] of PHASES) {
  thresholds[`http_req_duration{phase:${name}}`] = ["p(95)>=0"];
  thresholds[`http_req_failed{phase:${name}}`] = ["rate>=0"];
}
// Real rule: no request may hang until the client timeout, in any phase
thresholds["checks"] = ["rate==1.0"];

export const options = {
  scenarios: {
    spike: {
      executor: "ramping-arrival-rate",
      startRate: 0,
      timeUnit: "1s",
      preAllocatedVUs: 300,
      maxVUs: 1000,
      stages: [
        { target: 40, duration: "5s" },
        { target: 40, duration: "25s" },
        { target: 200, duration: "2s" },
        { target: 200, duration: "18s" },
        { target: 40, duration: "2s" },
        { target: 40, duration: "60s" },
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
  check(res, { "answered before timeout (200 or fast 503)": (r) => r.status === 200 || r.status === 503 });
}
