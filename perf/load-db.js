import http from "k6/http";
import { check } from "k6";

const TARGET = Number(__ENV.RATE) || 70;

export const options = {
  scenarios: {
    load: {
      executor: "ramping-arrival-rate",
      startRate: 0,
      timeUnit: "1s",
      preAllocatedVUs: 100,
      maxVUs: 500,
      stages: [
        { target: TARGET, duration: "30s" },
        { target: TARGET, duration: "2m" },
        { target: 0, duration: "30s" },
      ],
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<100", "p(99)<200"],
    http_req_failed: [{ threshold: "rate<0.001", abortOnFail: true }],
    dropped_iterations: ["count==0"],
    checks: ["rate==1.0"],
  },
};

export default function () {
  const res = http.get("http://localhost:5050/db");
  check(res, { "status is 200": (r) => r.status === 200 });
}
