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
            /*
             * 390x844, not the Pixel 7 preset's 412x915.
             *
             * 390 is this phase's reference width - the narrowest phone the project designs
             * for, the width `ask-live-mobile.spec.ts` already pins, and the width every
             * measurement in the mobile audit was taken at. The 22px between it and the preset
             * is not slack: the graph chrome, the three sheet heights and the 44px touch pads
             * were all measured inside that margin, and several of them have under 5px of
             * clearance. A suite that asserts them at 412 is asserting them where they are
             * comfortable and not where they are tight.
             *
             * The rest of the preset is kept deliberately: the mobile user agent, the
             * device-scale factor of 3 and `hasTouch` are what make the browser report
             * `pointer: coarse`, which is the media query the whole touch-target layer hangs
             * off. Overriding the viewport alone is the smallest change that moves the
             * measurement without losing the device.
             */
            name: "mobile",
            testMatch: /mobile\.spec\.ts/,
            use: {
                ...devices["Pixel 7"],
                channel: process.env.PLAYWRIGHT_CHANNEL ?? "msedge",
                viewport: { width: 390, height: 844 },
            },
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
