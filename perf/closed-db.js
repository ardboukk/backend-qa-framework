import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    closed_model: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS) || 20,
      duration: "30s",
    },
  },
};

export default function () {
  const res = http.get("http://localhost:5050/db");
  check(res, { "status is 200": (r) => r.status === 200 });
}
