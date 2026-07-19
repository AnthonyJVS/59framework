// Flow load test: an HTTP-level walk through a sequence of pages.
// The path list comes from FLOW_PATHS (comma-separated) so each application
// defines its real flow in performance/perf_config.yaml. Note for SPAs
// (like SauceDemo): inner routes are client-side only and 404 over plain
// HTTP, so the flow there is just the app shell - list real server routes
// for server-rendered applications.
// Environment variables: same contract as homepage_load.js, plus FLOW_PATHS.

import http from "k6/http";
import { check, group, sleep } from "k6";

const target = __ENV.TARGET_URL;
const paths = (__ENV.FLOW_PATHS || "/").split(",").map((p) => p.trim());

export const options = {
  vus: Number(__ENV.VUS || 5),
  duration: __ENV.DURATION || "30s",
  thresholds: {
    http_req_duration: [`p(95)<${Number(__ENV.P95_MS || 1000)}`],
    http_req_failed: [`rate<${Number(__ENV.MAX_FAIL || 0.01)}`],
  },
};

export default function () {
  group("page-flow", () => {
    for (const path of paths) {
      const response = http.get(`${target}${path}`);
      check(response, {
        [`${path} answers 2xx/3xx`]: (r) => r.status >= 200 && r.status < 400,
      });
      sleep(0.5);
    }
  });
}
