import { defineConfig, devices } from "@playwright/test";

const PORT = Number(process.env.PLAYWRIGHT_PORT ?? 3100);
const baseURL = `http://127.0.0.1:${PORT}`;
// A second instance pointed at a port nothing listens on, so the API-offline journey
// exercises the real server-rendered failure path rather than a mocked client fetch.
const OFFLINE_PORT = PORT + 1;
export const OFFLINE_BASE = `http://127.0.0.1:${OFFLINE_PORT}`;

// Playwright's own Chromium build could not be downloaded in this environment, so the
// suite runs against the Chromium-based browser already installed on the machine.
// Override with PLAYWRIGHT_CHANNEL=chromium once `playwright install` has succeeded.

export default defineConfig({
    testDir: "./tests/e2e",
    timeout: 60_000,
    expect: { timeout: 12_000 },
    fullyParallel: true,
    workers: 3,
    // The first request to a revalidating route can be slow while the server warms.
    retries: 1,
    reporter: [["list"]],
    use: {
        baseURL,
        trace: "retain-on-failure",
        viewport: { width: 1440, height: 900 },
    },
    projects: [
        {
            name: "desktop",
            testIgnore: /mobile\.spec\.ts/,
            use: {
                ...devices["Desktop Chrome"],
                channel: process.env.PLAYWRIGHT_CHANNEL ?? "msedge",
                viewport: { width: 1440, height: 900 },
            },
        },
        {
            name: "mobile",
            testMatch: /mobile\.spec\.ts/,
            use: { ...devices["Pixel 7"], channel: process.env.PLAYWRIGHT_CHANNEL ?? "msedge" },
        },
    ],
    webServer: [
        {
            command: `pnpm start --port ${PORT}`,
            url: baseURL,
            reuseExistingServer: true,
            timeout: 120_000,
            env: { VEDAGRAPH_API_URL: process.env.VEDAGRAPH_API_URL ?? "http://127.0.0.1:8000" },
        },
        {
            command: `pnpm start --port ${OFFLINE_PORT}`,
            url: `${OFFLINE_BASE}/explore`,
            reuseExistingServer: true,
            timeout: 120_000,
            env: { VEDAGRAPH_API_URL: "http://127.0.0.1:9" },
        },
    ],
});
