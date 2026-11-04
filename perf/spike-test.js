import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "10s", target: 5 },     // warm up: ramp to 5 users
    { duration: "5s",  target: 200 },   // SPIKE: jump to 200 users in 5 seconds
    { duration: "20s", target: 200 },   // hold the spike
    { duration: "10s", target: 5 },     // drop back down
    { duration: "10s", target: 0 },     // recovery: ramp down to zero
  ],
  thresholds: {
    http_req_duration: ["p(95)<200", "p(99)<500"],
    http_req_failed: ["rate<0.01"],
  },
};

export default function () {
  const res = http.get("http://localhost:4000/pay");
  check(res, { "status is 200": (r) => r.status === 200 });
  sleep(1);
}