/**
 * k6 Smoke Test — WAOOAW Platform
 * 10 virtual users, 2 minutes
 * Runs on every QA deploy (Gate 2)
 *
 * Constitutional basis: C-001 (Emergency Stop ≤250ms), C-071 (Quality Obligation)
 * ADR-013: CCTs are CI/CD gate — this is the performance equivalent
 */

import http from 'k6/http';
import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

// ─── Custom metrics (written to institutional.quality_metrics via OTel) ───────
const emergencyStopLatency = new Trend('emergency_stop_latency', true);
const ceValidateActionLatency = new Trend('ce_validate_action_latency', true);
const providerSelectionLatency = new Trend('pse_selection_latency', true);
const constitutionalViolations = new Rate('constitutional_violations');

// ─── Thresholds (failures block QA promotion) ─────────────────────────────────
export const options = {
  vus: 10,
  duration: '2m',
  thresholds: {
    // CONSTITUTIONAL FLOOR — C-001: Emergency Stop ≤250ms
    'emergency_stop_latency': ['p(99)<250'],
    // Performance SLAs from QA-STRATEGY.md Section 5.6
    'ce_validate_action_latency': ['p(99)<40'],
    'http_req_duration{name:bp_api}': ['p(99)<500'],
    'http_req_duration{name:web_portal}': ['p(99)<2500'],
    'http_req_failed': ['rate<0.01'],       // <1% HTTP error rate
    'constitutional_violations': ['rate<0.001'],  // Zero constitutional violations
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:5001';
const WS_URL = __ENV.WS_URL || 'ws://localhost:5003/emergency-stop';
const TOKEN = __ENV.K6_TEST_TOKEN || 'test-token';

const headers = {
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json',
};

export default function () {
  // ── 1. Health checks ────────────────────────────────────────────────────
  const health = http.get(`${BASE_URL}/health`, { headers, tags: { name: 'bp_api' } });
  check(health, { 'BP health 200': r => r.status === 200 });

  // ── 2. CE ValidateAction latency ──────────────────────────────────────
  const validateStart = Date.now();
  const validate = http.post(
    `${BASE_URL}/api/v1/constitutional/validate`,
    JSON.stringify({
      action_type: 'MCP_TOOL_CALL',
      tool_name: 'instagram-mcp',
      session_id: `smoke-session-${__VU}-${Date.now()}`,
    }),
    { headers, tags: { name: 'ce_validate' } }
  );
  const validateLatency = Date.now() - validateStart;
  ceValidateActionLatency.add(validateLatency);
  check(validate, { 'CE ValidateAction responds': r => r.status !== 503 });

  // ── 3. PSE provider selection latency ─────────────────────────────────
  const pseStart = Date.now();
  const pse = http.get(
    `${BASE_URL}/api/v1/ai/provider-status`,
    { headers, tags: { name: 'pse_status' } }
  );
  providerSelectionLatency.add(Date.now() - pseStart);
  check(pse, { 'PSE status reachable': r => r.status === 200 });

  // ── 4. Emergency Stop WebSocket latency (C-001 constitutional floor) ──
  const sessionId = `smoke-paas-${__VU}-${Date.now()}`;
  let esLatency = -1;

  const wsResult = ws.connect(
    `${WS_URL}?session_id=${sessionId}&token=${TOKEN}`,
    {},
    function(socket) {
      socket.on('open', () => {
        const sendTime = Date.now();
        socket.send(JSON.stringify({ type: 'EMERGENCY_STOP', session_id: sessionId }));
        socket.on('message', (msg) => {
          const data = JSON.parse(msg);
          if (data.type === 'EMERGENCY_STOP_CONFIRMED') {
            esLatency = Date.now() - sendTime;
            socket.close();
          }
        });
      });
      socket.setTimeout(() => socket.close(), 500); // 500ms timeout
    }
  );

  if (esLatency >= 0) {
    emergencyStopLatency.add(esLatency);
    // Constitutional violation if > 250ms
    if (esLatency > 250) {
      constitutionalViolations.add(1);
      console.error(`CONSTITUTIONAL VIOLATION: Emergency Stop latency ${esLatency}ms > 250ms — C-001`);
    } else {
      constitutionalViolations.add(0);
    }
  }

  // ── 5. Web portal LCP proxy (portal static assets) ────────────────────
  const portal = http.get(`${__ENV.WEB_URL || 'http://localhost:3000'}`, {
    tags: { name: 'web_portal' }
  });
  check(portal, { 'Portal accessible': r => r.status === 200 });

  sleep(Math.random() * 2 + 1); // 1-3s think time between iterations
}

export function handleSummary(data) {
  return {
    'results/smoke-summary.json': JSON.stringify(data),
  };
}
