// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §4 Run Lifecycle
// Constitutional basis: C-059 (Implementation Traceability), C-065 (Separation of Duties)
import { defineConfig, devices } from "@playwright/test";

// Trace and video are off in v1: they cannot be masked reliably, so evidence is screenshots-free,
// a redacted network log and the schema-validated report (ADR-054 item 7, section 4 step 10).
export default defineConfig({
  testDir: "./specs",
  testMatch: "**/*.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 240_000,
  reporter: [["list"]],
  use: {
    ...devices["Desktop Chrome"],
    trace: "off",
    video: "off",
    screenshot: "off",
  },
  projects: [{ name: "customer-journey" }],
});
