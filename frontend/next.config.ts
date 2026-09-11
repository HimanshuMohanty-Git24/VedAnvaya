import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    // The rewrite proxy's default ceiling is 30 seconds, and one route behind it is
    // routinely slower than that: POST /ask waits on a provider, and a 550B model on a
    // free tier measured 38s for a one-passage question. The proxy reset the socket, Next
    // answered 500, and the UI showed "the knowledge service could not be reached" -- a
    // service-outage message for a backend that was answering correctly. Raised past the
    // provider's own 60s timeout so the backend's own error is what surfaces, rather than
    // a proxy giving up first and mislabelling a slow answer as an unreachable graph.
    experimental: { proxyTimeout: 120_000 },
    async rewrites() {
        const apiBase = process.env.VEDAGRAPH_API_URL ?? "http://127.0.0.1:8000";
        return [{ source: "/backend/:path*", destination: `${apiBase}/api/v1/:path*` }];
    },
};

export default nextConfig;
