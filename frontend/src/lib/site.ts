import type { Metadata } from "next";

/**
 * The one public origin used by metadata routes, canonical links and social cards.
 *
 * Deployments must set `VEDANVAYA_SITE_URL` to their public HTTPS origin. The localhost
 * fallback keeps development deterministic without accidentally presenting a made-up domain
 * as the product's canonical home.
 */
export const siteUrl = new URL(process.env.VEDANVAYA_SITE_URL ?? "http://localhost:3000");

export const socialImage = {
    url: "/brand/og.png",
    width: 1200,
    height: 630,
    alt: "VedAnvaya — The Vedas, connected",
};

type PageMetadata = {
    title: string;
    description: string;
    pathname: string;
};

/** A complete, route-specific metadata set for public editorial and product entry pages. */
export function pageMetadata({ title, description, pathname }: PageMetadata): Metadata {
    return {
        // The homepage is the product title itself; applying the root template to it would
        // repeat the brand name in the browser tab and social previews.
        title: pathname === "/" ? { absolute: title } : title,
        description,
        alternates: { canonical: pathname },
        openGraph: {
            type: "website",
            siteName: "VedAnvaya",
            title,
            description,
            url: pathname,
            images: [socialImage],
        },
        twitter: {
            card: "summary_large_image",
            title,
            description,
            images: [socialImage.url],
        },
    };
}
