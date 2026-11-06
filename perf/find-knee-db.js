import http from "k6/http";
import { check } from "k6";
import exec from "k6/execution";

const RATES = [90, 92, 94, 96, 98];
const RAMP = 5;
const HOLD = 20;
const BLOCK = RAMP + HOLD;

const stages = [];
for (const rate of RATES) {
  stages.push({ target: rate, duration: `${RAMP}s` });
  stages.push({ target: rate, duration: `${HOLD}s` });
}

const thresholds = {};
for (const rate of RATES) {
  thresholds[`http_req_duration{stage:${rate}}`] = ["p(95)>=0"];
}

export const options = {
  scenarios: {
    find_knee: {
      executor: "ramping-arrival-rate",
      startRate: 0,
      timeUnit: "1s",
      preAllocatedVUs: 400,
      maxVUs: 1000,
      stages: stages,
    },
  },
  thresholds: thresholds,
};

function currentStage() {
  const elapsed = (Date.now() - exec.scenario.startTime) / 1000;
  const block = Math.floor(elapsed / BLOCK);
  const secondsIntoBlock = elapsed % BLOCK;
  if (block >= RATES.length || secondsIntoBlock < RAMP) {
    return "ramp";
  }
  return String(RATES[block]);
}

export default function () {
  const res = http.get("http://localhost:5050/db", {
    tags: { stage: currentStage() },
  });
  check(res, { "status is 200": (r) => r.status === 200 });
}
