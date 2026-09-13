import type { Page } from "@playwright/test";

/**
 * Walk every element that owns text, resolve the nearest opaque painted ancestor, and report
 * anything under its WCAG AA threshold.
 *
 * Lifted out of release-closure.spec.ts so more than one suite can use it. A second copy
 * would drift: this one already encodes two decisions that took measurement to get right,
 * namely that the background has to be resolved by walking up rather than read off the
 * element, and that a translucent ancestor does not count as painted.
 */
export async function failingContrast(page: Page) {
    return page.evaluate(() => {
        const luminance = (colour: string) => {
            const parts = colour.match(/[\d.]+/g)!.map(Number);
            const linear = parts
                .slice(0, 3)
                .map((v) => v / 255)
                .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
            return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
        };
        const painted = (el: Element) => {
            for (let n: Element | null = el; n; n = n.parentElement) {
                const bg = getComputedStyle(n).backgroundColor;
                const parts = bg.match(/[\d.]+/g);
                if (parts && (parts.length < 4 || Number(parts[3]) >= 0.95)) return bg;
            }
            return "rgb(255, 255, 255)";
        };
        const ratio = (a: string, b: string) => {
            const [x, y] = [luminance(a), luminance(b)];
            return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
        };

        const failures: string[] = [];
        const root = document.querySelector("main") ?? document.body;
        for (const el of root.querySelectorAll("*")) {
            const owns = [...el.childNodes].some(
                (n) => n.nodeType === Node.TEXT_NODE && n.textContent!.trim().length > 1,
            );
            if (!owns) continue;
            const style = getComputedStyle(el);
            if (style.visibility === "hidden" || Number(style.opacity) < 0.5) continue;
            const box = el.getBoundingClientRect();
            if (!box.width || !box.height) continue;
            /*
             * Skip anything clipped out of sight.
             *
             * Visually hidden text is read by a screen reader, which has no interest in the
             * colour it was never going to paint. The homepage's constellation ships its whole
             * text alternative this way, and without this the walk reported twelve failures at
             * 1.04:1 for content nobody can see. The test is 1px in either dimension, which is
             * what every sr-only recipe collapses to and is also true of any other technique
             * that hides text by shrinking its box.
             */
            if (box.width <= 1 || box.height <= 1) continue;
            const size = parseFloat(style.fontSize);
            const large = size >= 24 || (size >= 18.66 && Number(style.fontWeight) >= 700);
            const got = ratio(style.color, painted(el));
            const need = large ? 3 : 4.5;
            if (got < need - 0.005) {
                failures.push(
                    `${el.tagName}.${String(el.className)} ${got.toFixed(2)}<${need} "${el.textContent!.trim().slice(0, 30)}"`,
                );
            }
        }
        return failures;
    });
}
