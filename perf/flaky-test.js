import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 10,
  duration: "15s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
  },
};

export default function () {
  const res = http.get("http://localhost:4000/pay/flaky");

  check(res, {
    "status is 200": (r) => r.status === 200,
  });

  sleep(1);
}