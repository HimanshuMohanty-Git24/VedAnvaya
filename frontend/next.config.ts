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
    async rewrites() {
        const apiBase = process.env.VEDAGRAPH_API_URL ?? "http://127.0.0.1:8000";
        return [{ source: "/backend/:path*", destination: `${apiBase}/api/v1/:path*` }];
    },
};

export default nextConfig;
