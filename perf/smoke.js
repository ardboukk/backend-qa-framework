import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:5050";

export const options = {
  vus: 1,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    checks: ["rate==1.0"],
    "http_req_duration{name:fast}": ["p(95)<20"],
    "http_req_duration{name:cpu}": ["p(95)<50"],
    "http_req_duration{name:io}": ["p(95)<150"],
    "http_req_duration{name:db}": ["p(95)<80"],
  },
};

export default function () {
  for (const name of ["fast", "cpu", "io", "db"]) {
    const res = http.get(`${BASE}/${name}`, { tags: { name: name } });
    check(res, { [`${name} is 200`]: (r) => r.status === 200 });
  }
  sleep(1);
}
