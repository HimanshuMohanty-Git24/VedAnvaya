import { expect, test, type Page } from "@playwright/test";

const READER = "/passage/VG%3ARV%3ASAK%3AM01%3AS001%3AV001";

for (const width of [1440, 1024, 390]) {
    test.describe(`release closure at ${width}px`, () => {
        test.use({ viewport: { width, height: 900 } });

        test("hierarchy controls remain large enough when branches expand", async ({ page }) => {
            await page.goto("/vedas/rigveda");
            const expand = page.getByRole("button", { name: "Expand RV 1", exact: true });
            const box = await expand.boundingBox();
            expect(box!.width).toBeGreaterThanOrEqual(44);
            expect(box!.height).toBeGreaterThanOrEqual(44);
            await expand.focus();
            await page.keyboard.press("Enter");
            await page.getByRole("button", { name: "Expand RV 1.1", exact: true }).click();
            await expect(page.getByRole("link", { name: "RV 1.1.1", exact: true })).toBeVisible();
            expect(
                await page.evaluate(() => document.documentElement.scrollWidth),
            ).toBeLessThanOrEqual(width);
        });

        test("Ask mode explanation stays readable outside the native select", async ({ page }) => {
            await page.goto("/ask");
            const mode = page.getByRole("combobox", { name: /Retrieval mode/ });
            await expect(mode).toHaveAccessibleDescription("Let the planner choose the channels");
            await expect(mode.locator("option:checked")).toHaveText("Automatic");
            await mode.selectOption("GRAPH");
            await expect(mode).toHaveAccessibleDescription(
                "Favour recorded connections between entities",
            );
            const note = page.locator("#ask-mode-note");
            await expect(note).toBeVisible();
            expect(await note.evaluate((e) => e.scrollWidth <= e.clientWidth)).toBe(true);
        });

        test("formula status keeps the shared badge typography", async ({ page }) => {
            await page.goto(READER);
            const normalSize = await page
                .locator(".knowledge-status strong")
                .first()
                .evaluate((e) => getComputedStyle(e).fontSize);
            await page.goto("/formulas");
            await page.locator(".formula-list a").first().click();
            const status = page.locator(".formula-stats .knowledge-status strong");
            await expect(status).toBeVisible();
            expect(await status.evaluate((e) => getComputedStyle(e).fontSize)).toBe(normalSize);
        });

        test("audio controls and supporting text stay accessible in both themes", async ({
            page,
        }) => {
            await page.goto(READER);
            for (const selector of [
                ".recitation-play",
                ".recitation-seek",
                ".recitation-speed select",
            ]) {
                const box = await page.locator(selector).boundingBox();
                expect(box!.height).toBeGreaterThanOrEqual(44);
                expect(box!.width).toBeGreaterThanOrEqual(44);
            }
            for (const dark of [false, true]) {
                await setTheme(page, dark);
                expect(await failingContrast(page)).toEqual([]);
            }
        });
    });
}

/**
 * Several surfaces transition `background` over 0.16s, so a measurement taken straight
 * after the class flips samples the half-way colour and reports contrast failures the
 * settled page does not have. An earlier pass of this work read those artifacts as real
 * dark-mode defects on two pages; waiting past the longest transition is what made the
 * numbers mean anything.
 */
async function setTheme(page: Page, dark: boolean) {
    await page.evaluate((d) => document.documentElement.classList.toggle("dark", d), dark);
    await page.waitForTimeout(600);
}

/**
 * Contrast measured against the background actually painted behind the text, rather than
 * against a pair of tokens picked in advance. A token-pair check asserts a pairing that
 * may never occur in the DOM, and misses every pairing nobody thought to list.
 */
async function failingContrast(page: Page) {
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

/**
 * The legend only renders the groups the current neighbourhood happens to contain, so
 * reading the rendered chips certifies only the colours that were on screen. Two of the
 * six failed AA while rendering nothing at the default root. Each class is measured on a
 * chip of its own so absence from one graph cannot pass for absence of the defect.
 */
test("every graph legend colour meets AA, not only the ones this root renders", async ({
    page,
}) => {
    await page.goto("/graph");
    await expect(page.locator(".legend-chip").first()).toBeVisible();
    for (const dark of [false, true]) {
        await setTheme(page, dark);
        const failures = await page.evaluate(() => {
            const groups = [
                "deity",
                "passage",
                "person",
                "idea",
                "rite",
                "thing",
                "wording",
                "other",
            ];
            const host = document.querySelector(".graph-legend")!;
            const probes = groups.map((group) => {
                const chip = document.createElement("button");
                chip.className = `legend-chip group-${group}`;
                chip.textContent = group;
                host.append(chip);
                return [group, chip] as const;
            });
            const luminance = (colour: string) => {
                const parts = colour.match(/[\d.]+/g)!.map(Number);
                const linear = parts
                    .slice(0, 3)
                    .map((v) => v / 255)
                    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
                return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
            };
            // The chip paints its own surface, so the background has to be read by
            // walking up from the chip until something opaque is found. Reading the
            // legend container instead measures a colour nothing is drawn on.
            const painted = (el: Element) => {
                for (let n: Element | null = el; n; n = n.parentElement) {
                    const bg = getComputedStyle(n).backgroundColor;
                    const parts = bg.match(/[\d.]+/g);
                    if (parts && (parts.length < 4 || Number(parts[3]) >= 0.95)) return bg;
                }
                return "rgb(255, 255, 255)";
            };
            const out: string[] = [];
            for (const [group, chip] of probes) {
                const [a, b] = [luminance(getComputedStyle(chip).color), luminance(painted(chip))];
                const got = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
                if (got < 4.495) out.push(`${group} ${got.toFixed(2)}`);
                chip.remove();
            }
            return out;
        });
        expect(failures).toEqual([]);
    }
});

test("incomplete Rigveda translation coverage is not rounded to 100 percent", async ({ page }) => {
    await page.goto("/vedas");
    const rigveda = page.getByRole("article").filter({ hasText: "Rigveda Samhita" });
    await expect(rigveda).toContainText("10,502 translated (99.5%)");
    await expect(rigveda).not.toContainText("(100%)");
});
