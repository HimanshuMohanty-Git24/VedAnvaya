import type { Metadata, Viewport } from "next";
import { Fraunces, Inter, Noto_Serif_Devanagari } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";
import { SiteFooter } from "@/components/shell/site-footer";
import { SiteHeader } from "@/components/shell/site-header";
import { ThemeProvider } from "@/components/theme-provider";

/**
 * Fraunces sets English display type. Its optical-size axis is requested so the browser can
 * apply `font-optical-sizing: auto` from the rendered size, which is the difference between a
 * 64px hero that looks drawn for 64px and one that looks like body copy enlarged.
 *
 * SOFT and WONK are not requested. Both default to 0, which is the institutional end of the
 * family, and naming an axis by hand in `font-variation-settings` is what would stop the
 * optical sizing working.
 */
const fraunces = Fraunces({
    variable: "--font-fraunces",
    subsets: ["latin", "latin-ext"],
    /* No `weight` here: next/font only allows `axes` on a font left variable, and the
       variable range is what we want anyway. The system uses 400, 500 and 600 and refuses
       700, which is a rule in tokens.css rather than a restriction on the file. */
    axes: ["opsz"],
    display: "swap",
});

const inter = Inter({
    variable: "--font-inter",
    subsets: ["latin", "latin-ext"],
    display: "swap",
});

/** Devanagari verse, which is the Samaveda and the Yajurveda. */
const notoDevanagari = Noto_Serif_Devanagari({
    variable: "--font-noto-deva",
    subsets: ["devanagari"],
    weight: ["400", "500"],
    display: "swap",
});

/**
 * IAST verse, which is the Rigveda and the Atharvaveda, and therefore four fifths of the
 * corpus's Sanskrit.
 *
 * Self-hosted because it has to be. The Google Fonts CDN serves none of U+0331, U+030D or
 * U+0325 for any Latin font, and those are the combining marks this corpus writes its Vedic
 * accents with. Vendored and subsetted by `scripts/build_web_fonts.py`: 3,857 glyphs to
 * 1,381, 293 KB to 78 KB, with the `mark` and `mkmk` tables kept so a mark landing on a
 * letter that already carries one is placed rather than stacked at the origin. Rasterised
 * against the upstream release on RV 1.1.1 the subset differs by zero pixels.
 */
const charis = localFont({
    variable: "--font-charis",
    display: "swap",
    /*
     * Regular only. The italic was vendored alongside it and measured 82 KB downloaded on
     * every page and used on none: next/font preloads a declared face whether or not
     * anything asks for it, and no surface sets Sanskrit in italic. It is still produced by
     * scripts/build_web_fonts.py, so adding it back is one line if a surface ever needs it.
     */
    src: [{ path: "../fonts/charis-regular.woff2", weight: "400", style: "normal" }],
});

/**
 * The browser identity.
 *
 * Next's App Router picks up `favicon.ico`, `icon.png` and `apple-icon.png` from this
 * directory by convention and emits the link tags itself, so the only things declared here
 * are the ones convention cannot infer: the manifest, the theme colour and the social card.
 *
 * `metadataBase` is required for the OpenGraph image to resolve to an absolute URL. Without
 * it Next warns and emits a relative path, which every social scraper ignores.
 */
export const metadata: Metadata = {
    metadataBase: new URL(process.env.VEDANVAYA_SITE_URL ?? "http://localhost:3000"),
    title: {
        default: "VedAnvaya: the Vedas, connected",
        template: "%s | VedAnvaya",
    },
    description:
        "Read the four Vedic Samhitas as one connected corpus. Mantras, deities, seers, rites and shared wording, with the evidence behind every connection and a plain statement of what is not held.",
    applicationName: "VedAnvaya",
    manifest: "/manifest.webmanifest",
    openGraph: {
        type: "website",
        siteName: "VedAnvaya",
        title: "VedAnvaya: the Vedas, connected",
        description:
            "Four Samhitas, one corpus, and the evidence behind every connection.",
        images: [{ url: "/brand/og.png", width: 1200, height: 630, alt: "VedAnvaya" }],
    },
    twitter: { card: "summary_large_image" },
};

export const viewport: Viewport = {
    /*
     * Two colours, because the browser chrome should match the page it is framing rather than
     * always the light one. Declared here rather than in metadata: Next moved themeColor to
     * the viewport export and warns on the old location.
     */
    themeColor: [
        { media: "(prefers-color-scheme: light)", color: "#F4F0E7" },
        { media: "(prefers-color-scheme: dark)", color: "#131410" },
    ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
    return (
        <html
            lang="en"
            suppressHydrationWarning
            className={`${fraunces.variable} ${inter.variable} ${notoDevanagari.variable} ${charis.variable}`}
        >
            <body>
                <ThemeProvider>
                    <a className="va-skip-link" href="#main">
                        Skip to content
                    </a>
                    <SiteHeader />
                    <main id="main">{children}</main>
                    <SiteFooter />
                </ThemeProvider>
            </body>
        </html>
    );
}
