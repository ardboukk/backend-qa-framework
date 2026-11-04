import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 20,              // 20 virtual users at the same time
  duration: "30s",      // for 30 seconds
  thresholds: {
    http_req_duration: ["p(95)<200", "p(99)<500"],   // 95% under 200 ms, 99% under 500 ms
    http_req_failed: ["rate<0.01"],                  // less than 1% errors
  },
};

export default function () {
  const res = http.get("http://localhost:4000/pay/slow");

  check(res, {
    "status is 200": (r) => r.status === 200,
  });

  sleep(1);             // each user waits 1 second between requests, like a real person
}