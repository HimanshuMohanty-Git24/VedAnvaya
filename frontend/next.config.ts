import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    // The rewrite proxy's default ceiling is 30 seconds, and one route behind it is
    // routinely slower than that: POST /ask waits on a provider, and a 550B model on a
    // free tier measured 38s for a one-passage question. The proxy reset the socket, Next
    // answered 500, and the UI showed "the knowledge service could not be reached" -- a
    // service-outage message for a backend that was answering correctly.
    //
    // The ceiling has to clear the backend's *worst* case, not its typical one, or that
    // same false outage message comes back for the slowest questions only. The backend
    // bound is a product, not a single timeout: VEDAGRAPH_LLM_TIMEOUT_SECONDS (60) times
    // VEDAGRAPH_LLM_MAX_RETRIES + 1 (4), plus three backoff sleeps capped at 30s each by
    // _MAX_BACKOFF_SECONDS -- 330 seconds before the provider layer gives up and returns
    // an error of its own. A release-closure walk measured one Ask at 120.4s against the
    // old 120s ceiling, so the gap was already reachable rather than theoretical.
    //
    // Waiting is the lesser fault here: a pending Ask aborts when the reader navigates
    // away or asks again, whereas a proxy cutting first states something untrue about the
    // corpus. Raise this if either LLM setting rises. The latency itself is PERF_BACKLOG_01.
    experimental: { proxyTimeout: 345_000 },

    // Development only. `next dev` binds to localhost and treats a request arriving on
    // 127.0.0.1 as cross-origin, which blocks /_next/hmr and, with it, the client bundle:
    // the page server-renders and then never hydrates, so every button is inert and nothing
    // reports an error. Screenshot and e2e drivers reach the server by IP, so they hit this.
    //
    // This is a dev-server allowlist and has no effect on a production build, which does not
    // serve /_next/hmr at all and does no origin checking of its own here.
    allowedDevOrigins: ["127.0.0.1", "localhost"],
    /*
     * The world artifact is cached properly. It is still not compressed.
     *
     * Two separate findings, and this fixes one of them. `world.bin` was served with
     * `Cache-Control: max-age=0`, which is simply wrong about a build artifact: the filename is
     * stable and the contents are frozen per build, so every graph visit re-fetched 2.4 MB it
     * already had. A rebuilt artifact is a new deployment, not a stale cache, and the honest
     * header is a long immutable one.
     *
     * The compression half is NOT fixed here and this header does not fix it. Measured, the
     * file goes over the wire as 2,493,613 bytes with no `Content-Encoding`, while
     * `world.labels.json` beside it compresses by 78% - because the built-in compression skips
     * `application/octet-stream`. It is a packed array of little-endian numbers and compresses
     * well: gzip -9 reaches 966 KB and brotli 808 KB, a 61% saving on the critical path of
     * every graph visit. `Vary: Accept-Encoding` is set so that a reverse proxy or CDN which
     * does compress it caches the two variants separately rather than serving one to both.
     *
     * Closing it properly means either pre-compressing at build time in `build-world.mjs` and
     * serving the encoded variant, or doing it at the edge. Both are deployment decisions
     * rather than a config line, so this is recorded as a known residual rather than quietly
     * left looking solved.
     */
    async headers() {
        return [
            {
                source: "/world/:file*",
                headers: [
                    { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
                    { key: "Vary", value: "Accept-Encoding" },
                ],
            },
        ];
    },
    async rewrites() {
        const apiBase = process.env.VEDAGRAPH_API_URL ?? "http://127.0.0.1:8000";
        return [{ source: "/backend/:path*", destination: `${apiBase}/api/v1/:path*` }];
    },
    /*
     * Two names each for two surfaces, with one canonical address apiece.
     *
     * The Visualization Lab is at /visualizations because that is what the navigation slot
     * reserved for it says, and /lab is the short name it gets called by. Sources and method
     * are one page rather than two, because splitting them means a reader who wants to know
     * where a verse came from lands on the page that explains evidence grades; /sources is
     * canonical because five existing links already point there.
     *
     * Permanent rather than temporary: these are naming decisions, not a migration.
     */
    async redirects() {
        return [
            { source: "/lab", destination: "/visualizations", permanent: true },
            { source: "/methodology", destination: "/sources", permanent: true },
        ];
    },
};

export default nextConfig;
