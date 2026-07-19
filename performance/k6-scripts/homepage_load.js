// Baseline homepage load test.
// Configured entirely through environment variables so the same script serves
// the dashboard, pytest smoke checks and CI:
//   TARGET_URL  - base URL to hit (required)
//   VUS         - virtual users (default 5)
//   DURATION    - test duration, e.g. "30s" (default 30s)
//   P95_MS      - p95 latency threshold in ms (default 800)
//   MAX_FAIL    - max allowed failure rate 0..1 (default 0.01)

import http from "k6/http";
import { check, sleep } from "k6";

const target = __ENV.TARGET_URL;

export const options = {
  vus: Number(__ENV.VUS || 5),
  duration: __ENV.DURATION || "30s",
  thresholds: {
    http_req_duration: [`p(95)<${Number(__ENV.P95_MS || 800)}`],
    http_req_failed: [`rate<${Number(__ENV.MAX_FAIL || 0.01)}`],
  },
};

export default function () {
  const response = http.get(target);
  check(response, {
    "status is 2xx/3xx": (r) => r.status >= 200 && r.status < 400,
    "body is non-empty": (r) => (r.body || "").length > 0,
  });
  sleep(1);
}
