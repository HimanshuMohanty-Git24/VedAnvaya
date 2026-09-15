import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site";

/*
 * A deliberately bounded sitemap. These are the durable public entry points; individual
 * passages and entity records stay discoverable through their parent indexes and internal
 * links until a build-time record inventory can add them without making the sitemap a second
 * live API client.
 */
const PATHS = [
    "/",
    "/vedas",
    "/vedas/rigveda",
    "/vedas/samaveda",
    "/vedas/yajurveda",
    "/vedas/atharvaveda",
    "/ask",
    "/graph",
    "/visualizations",
    "/about",
    "/sources",
    "/search",
    "/explore",
    "/explore/atharvaveda",
    "/connections",
    "/devatas",
    "/entities",
    "/formulas",
    "/rituals",
    "/material-culture",
    "/insights",
    "/limits",
] as const;

export default function sitemap(): MetadataRoute.Sitemap {
    return PATHS.map((pathname) => ({
        url: new URL(pathname, siteUrl).toString(),
        changeFrequency: pathname === "/" ? "weekly" : "monthly",
        priority: pathname === "/" ? 1 : pathname === "/vedas" ? 0.9 : 0.8,
    }));
}
