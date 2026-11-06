import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    open_model: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE) || 120,
      timeUnit: "1s",
      duration: "30s",
      preAllocatedVUs: 900,
      maxVUs: 1000,
    },
  },
};

export default function () {
  const res = http.get("http://localhost:5050/db");
  check(res, { "status is 200": (r) => r.status === 200 });
}
