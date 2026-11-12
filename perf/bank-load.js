import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:8081";
const JSON_HDR = { headers: { "Content-Type": "application/json" } };

export const options = {
  scenarios: {
    bank: {
      executor: "constant-arrival-rate",
      rate: 20,
      timeUnit: "1s",
      duration: "4m",
      preAllocatedVUs: 50,
      maxVUs: 800,
    },
  },
};

export function setup() {
  const create = (owner) => {
    const r = http.post(`${BASE}/accounts`,
      JSON.stringify({ owner, initial_balance: 1000000 }), JSON_HDR);
    if (r.status !== 201) throw new Error(`setup failed: ${r.status} ${r.body}`);
    return r.json("id");
  };
  const customers = [];
  for (let i = 0; i < 50; i++) customers.push(create(`customer-${i}`));
  const merchant = create("merchant");
  return { customers, merchant };
}

const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

export default function (data) {
  const roll = Math.random();
  if (roll < 0.5) {
    const r = http.get(`${BASE}/accounts/${pick(data.customers)}`,
      { tags: { name: "get_account" } });
    check(r, { "read 200": (x) => x.status === 200 });
  } else {
    const from = pick(data.customers);
    const to = roll < 0.8 ? data.merchant : pick(data.customers);
    if (to === from) return;
    const r = http.post(`${BASE}/transfer`,
      JSON.stringify({ from_id: from, to_id: to, amount: 1 }),
      { ...JSON_HDR, tags: { name: "transfer" } });
    check(r, { "transfer 201": (x) => x.status === 201 });
  }
}