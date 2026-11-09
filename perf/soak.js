import http from "k6/http";
import { check } from "k6";
import { Trend, Gauge } from "k6/metrics";
import exec from "k6/execution";

const BASE = "http://localhost:5050";
const MINUTES = Number(__ENV.MINUTES) || 15;
const TOTAL = MINUTES * 60;

// Server-side memory, recorded by the monitor scenario
const heapMb = new Trend("server_heap_mb");
const heapGrowthMb = new Trend("server_heap_growth_mb");
const cacheEntries = new Gauge("server_cache_entries");

// Compare the first quarter of the run with the last quarter
function timeWindow() {
  const t = (Date.now() - exec.scenario.startTime) / 1000;
  if (t >= 60 && t < 60 + TOTAL / 4) return "early";
  if (t >= TOTAL * 0.75) return "late";
  return "middle";
}

export const options = {
  scenarios: {
    db_users: {
      executor: "constant-arrival-rate", exec: "dbUser",
      rate: 40, timeUnit: "1s", duration: `${MINUTES}m`,
      preAllocatedVUs: 20, maxVUs: 100,
    },
    report_users: {
      executor: "constant-arrival-rate", exec: "reportUser",
      rate: 20, timeUnit: "1s", duration: `${MINUTES}m`,
      preAllocatedVUs: 10, maxVUs: 50,
    },
    monitor: {
      executor: "constant-arrival-rate", exec: "watchMemory",
      rate: 1, timeUnit: "5s", duration: `${MINUTES}m`,
      preAllocatedVUs: 1, maxVUs: 1,
    },
  },
  thresholds: {
    "http_req_duration{name:db,window:early}": ["p(95)>=0"],
    "http_req_duration{name:db,window:late}": ["p(95)>=0"],
    "http_req_failed{name:db}": ["rate<0.01"],
    server_heap_growth_mb: ["max<20"],
    server_cache_entries: ["value<5000"], // a cache must have a limit
    dropped_iterations: ["count==0"],
  },
};

export function dbUser() {
  const res = http.get(`${BASE}/db`, { tags: { name: "db", window: timeWindow() } });
  check(res, { "db is 200": (r) => r.status === 200 });
}

export function reportUser() {
  const res = http.get(`${BASE}/report`, { tags: { name: "report" } });
  check(res, { "report is 200": (r) => r.status === 200 });
}

let firstHeap = null;
export function watchMemory() {
  const res = http.get(`${BASE}/metrics`, { tags: { name: "metrics" } });
  const m = res.json();
  if (firstHeap === null) firstHeap = m.heap_used_mb;
  heapMb.add(m.heap_used_mb);
  heapGrowthMb.add(m.heap_used_mb - firstHeap);
  cacheEntries.add(m.cache_entries);
}
