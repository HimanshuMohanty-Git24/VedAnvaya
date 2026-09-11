import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    async rewrites() {
        const apiBase = process.env.VEDAGRAPH_API_URL ?? "http://127.0.0.1:8000";
        return [{ source: "/backend/:path*", destination: `${apiBase}/api/v1/:path*` }];
    },
};

export default nextConfig;
