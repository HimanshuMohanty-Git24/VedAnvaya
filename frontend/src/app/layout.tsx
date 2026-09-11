import type { Metadata } from "next";
import { Geist, Noto_Sans_Devanagari, Newsreader } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";
import { SECONDARY_NAV } from "@/components/navigation";
import { ThemeProvider } from "@/components/theme-provider";

const geist = Geist({ variable: "--font-ui", subsets: ["latin"], display: "swap" });
const newsreader = Newsreader({ variable: "--font-reading", subsets: ["latin"], display: "swap" });
const devanagari = Noto_Sans_Devanagari({
    variable: "--font-devanagari",
    subsets: ["devanagari"],
    display: "swap",
});

export const metadata: Metadata = {
    title: { default: "VedaGraph — a digital atlas of the Vedas", template: "%s | VedaGraph" },
    description:
        "Read the four Vedic Samhitas as one connected corpus: mantras, deities, seers, rites and shared wording, with the evidence behind every connection.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
    return (
        <html
            lang="en"
            suppressHydrationWarning
            className={`${geist.variable} ${newsreader.variable} ${devanagari.variable}`}
        >
            <body>
                <ThemeProvider>
                    <a className="skip-link" href="#main">
                        Skip to content
                    </a>
                    <SiteHeader />
                    <main id="main">{children}</main>
                    <footer className="site-footer">
                        <div className="shell">
                            <div>
                                <span className="footer-brand">VedaGraph</span>
                                <p>
                                    Four Samhitas, read as one connected corpus. Every count on this
                                    site describes what this build holds, never what the Vedas
                                    contain.
                                </p>
                            </div>
                            <nav aria-label="About this atlas">
                                {SECONDARY_NAV.map((item) => (
                                    <Link href={item.href} key={item.href}>
                                        {item.label}
                                    </Link>
                                ))}
                            </nav>
                        </div>
                    </footer>
                </ThemeProvider>
            </body>
        </html>
    );
}
