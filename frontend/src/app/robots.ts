import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site";

/**
 * Local servers should never imply a production indexing policy. Production is deliberately
 * permissive: all public records and static assets remain crawlable, while the sitemap gives
 * crawlers the curated entry-point set.
 */
export default function robots(): MetadataRoute.Robots {
    if (process.env.NODE_ENV !== "production") {
        return { rules: { userAgent: "*", disallow: "/" } };
    }

    return {
        rules: { userAgent: "*", allow: "/" },
        sitemap: new URL("/sitemap.xml", siteUrl).toString(),
    };
}
