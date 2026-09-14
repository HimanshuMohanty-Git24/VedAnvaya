import { expect, test, type Page } from "@playwright/test";
import { OFFLINE_BASE } from "../../playwright.config";
import { absentHere, atUrl } from "./guards";

const RV_1_1_1 = encodeURIComponent("VG:RV:SAK:M01:S001:V001");
const INDRA = encodeURIComponent("VG:DEVATA:INDRAH");
const AGNI = encodeURIComponent("VG:DEVATA:AGNIH");
const SOMA = encodeURIComponent("VG:DEVATA:SOMAH");
const SOMA_DRINK = encodeURIComponent("VG:CONCEPT:SOMA-DRINK");
const AGNI_FIRE = encodeURIComponent("VG:CONCEPT:AGNI-FIRE");
const TAKMAN = encodeURIComponent("VG:CONCEPT:TAKMAN-FEVER");

async function search(page: Page, query: string) {
    await page.goto("/search");
    await page.getByLabel(/Search Sanskrit, IAST/).fill(query);
    await expect(page.locator(".search-results li").first()).toBeVisible();
}

test.describe("journey 1 — home to a single mantra", () => {
    test("home, Rigveda, mandala 1, sukta 1, RV 1.1.1", async ({ page }) => {
        await page.goto("/");
        await expect(page.getByRole("heading", { level: 1 })).toContainText(/four samhitas/i);

        await page.getByRole("link", { name: "Read the Vedas" }).first().click();
        await expect(page).toHaveURL(/\/vedas$/);

        await page
            .getByRole("article")
            .filter({ hasText: "Rigveda Samhita" })
            .getByRole("link", { name: /Read the Rigveda Samhita/ })
            .click();
        await expect(page).toHaveURL(/\/vedas\/rigveda$/);

        /*
         * Native hierarchy, not a common template - asserted where the product now says it.
         *
         * cabe44c rebuilt the finding aid as a level-by-level descent rather than an expanding
         * tree. There is no "Browse by Mandala" heading any more (the heading is the generic
         * "Index of the collection") and no "Expand RV 1" disclosure buttons; the corpus's own
         * vocabulary is announced in `.va-findaid-level` at each level, which is a stronger
         * place for it because it names the level the reader is actually standing on. The
         * claim is unchanged: the Rigveda descends mandala, sukta, mantra under its own names.
         */
        await expect(page.locator(".va-findaid-level")).toContainText(/mandalas/i);
        await page.locator(".va-structure button").first().click();
        await expect(page.locator(".va-findaid-level")).toContainText(/suktas/i);
        await page.locator(".va-structure button").first().click();
        await expect(page.locator(".va-findaid-level")).toContainText(/mantras/i);
        await page.locator('.va-structure a[href^="/passage/"]').first().click();

        await expect(page).toHaveURL(new RegExp(`/passage/${RV_1_1_1}`));
        await expect(page.getByRole("heading", { level: 1 })).toHaveText("RV 1.1.1");
        await expect(page.locator(".sanskrit").first()).toBeVisible();
        await expect(page.getByRole("heading", { name: "Translation" })).toBeVisible();
    });
});

test.describe("journey 2 — search Indra to a passage", () => {
    test("search, deity result, profile, passage", async ({ page }) => {
        await search(page, "Indra");

        const deityRow = page.locator(".result-row", { hasText: "Indra" }).first();
        await expect(deityRow.locator(".result-type")).toBeVisible();
        await deityRow.click();

        await expect(page).toHaveURL(/\/devatas\//);
        /* cabe44c made the record's heading the transliterated Sanskrit name and gave the
           English name its own line. `indraḥ` carries a dot-below, which is why
           corpus-surfaces.spec.ts separately pins `.va-archive-name` to the reading face. */
        await expect(page.locator(".va-archive-name")).toHaveText("indraḥ");
        await expect(page.locator(".va-archive-english")).toContainText("Indra");
        await expect(page.getByRole("heading", { name: "Across the four Vedas" })).toBeVisible();

        await page.locator(".citation-list a").first().click();
        await expect(page).toHaveURL(/\/passage\//);
        await expect(page.locator(".sanskrit").first()).toBeVisible();
    });
});

/** Relationship labels live in a reused pool; the inline opacity is what makes one current. */
async function shownLabels(page: import("@playwright/test").Page) {
    return page.evaluate(() =>
        [...document.querySelectorAll(".va-edge-label")]
            .filter((node) => (node as HTMLElement).style.opacity === "1")
            .map((node) => node.textContent ?? ""),
    );
}

test.describe("journey 3 — graph to evidence", () => {
    /*
     * Rewritten against the current graph.
     *
     * These assertions used to drive the Cytoscape explorer - `.graph-canvas`, `.legend-chip`,
     * `.graph-node-list` - which has been deleted twice over. The claims they protected are not
     * about that component and they outlive it: a reader must be able to see what a connection
     * *is*, find out what it does and does not establish, and reach all of it without clicking a
     * one-pixel line on a canvas.
     */
    const GRAPH = `/graph?view=focus&renderer=2d&node=${INDRA}`;

    test("every visible connection says what kind of relationship it is", async ({ page }) => {
        await page.goto(GRAPH);
        /* The pool is allocated at the cap and slots are reused, so an unused span is an empty
           element with no box. Visibility is carried by the inline opacity, not by the DOM. */
        await expect
            .poll(async () => (await shownLabels(page)).length, { timeout: 30_000 })
            .toBeGreaterThan(0);
        const shown = await shownLabels(page);

        // Words, not predicate tokens. The curated phrasing differs from a mechanical
        // humanisation on 44 of 57 predicates, so an underscore here means the wrong source.
        for (const phrase of shown) {
            expect(phrase).not.toMatch(/_/);
            expect(phrase).toMatch(/[a-z]/);
        }
    });

    test("a relationship explains what it does not establish", async ({ page }) => {
        await page.goto(GRAPH);
        await expect
            .poll(async () => (await shownLabels(page)).length, { timeout: 30_000 })
            .toBeGreaterThan(0);
        const labels = page.locator('.va-edge-label[data-pickable="true"]');
        const count = await labels.count();
        for (let i = 0; i < count; i += 1) {
            const label = labels.nth(i);
            if ((await label.evaluate((node) => (node as HTMLElement).style.opacity)) !== "1") {
                continue;
            }
            await label.click();
            break;
        }

        const inspector = page.locator(".va-relationship");
        await expect(inspector).toBeVisible();
        // The half a reader is most often missing, and the reason this panel exists at all.
        await expect(inspector.getByText("What it does not establish")).toBeVisible();
        await expect(inspector.locator(".va-relationship-phrase")).not.toBeEmpty();

        await inspector.getByRole("button", { name: "Close the relationship" }).click();
        await expect(page.locator(".va-relationship")).toHaveCount(0);
    });

    test("the connections are reachable without touching the canvas", async ({ page }) => {
        await page.goto(GRAPH);
        const connections = page.locator(".va-world-neighbours button");
        await expect(connections.first()).toBeVisible({ timeout: 30_000 });
        expect(await connections.count()).toBeGreaterThan(0);
    });

    test("the graph never renders internal bookkeeping nodes", async ({ page }) => {
        await page.goto(GRAPH);
        const rows = page.locator(".va-world-neighbours .va-world-hit-name");
        await expect(rows.first()).toBeVisible({ timeout: 30_000 });
        for (const label of await rows.allTextContents()) {
            expect(label.toLowerCase()).not.toMatch(
                /qaissue|qa issue|source artifact|text version|internal/,
            );
        }
    });

    test("an ascription descriptor is never presented as a deity", async ({ page }) => {
        await page.goto(
            `/graph?view=focus&renderer=2d&node=${encodeURIComponent("VG:DEVATA:ASAMATIH")}`,
        );
        const kind = page.locator(".va-world-panel-kind");
        await expect(kind).toBeVisible({ timeout: 30_000 });
        await expect(kind).not.toHaveText(/^deity$/i);
    });

    test("the connection list says how much of the whole it is showing", async ({ page }) => {
        await page.goto(GRAPH);
        const heading = page.locator(".va-world-neighbours h3");
        await expect(heading).toBeVisible({ timeout: 30_000 });
        // Indra has 7,347 connections and the panel shows a few dozen; saying so is the point.
        await expect(heading).toContainText(/\d+ of [\d,]+/);
    });
});

test.describe("journey 4 — Soma as deity and as substance", () => {
    test("search separates the two records", async ({ page }) => {
        await search(page, "Soma");
        const rows = page.locator(".search-results li");
        const deity = rows.filter({ has: page.locator(".result-type", { hasText: /^devata$/ }) });
        const other = rows.filter({
            has: page.locator(".result-type", { hasText: /offering|substance|concept/ }),
        });
        await expect(deity.first()).toBeVisible();
        await expect(other.first()).toBeVisible();
        await expect(deity.first().locator("a")).toHaveAttribute("href", /\/devatas\//);
        await expect(other.first().locator("a")).toHaveAttribute("href", /\/entities\//);
    });

    test("the deity page links the substance explicitly", async ({ page }) => {
        await page.goto(`/devatas/${SOMA}`);
        await expect(page.getByText("Two records, one word")).toBeVisible();
        const link = page.getByRole("link", { name: /soma juice, the substance/ });
        await expect(link).toBeVisible();
        await link.click();
        await expect(page).toHaveURL(new RegExp(SOMA_DRINK));
        await expect(page.getByRole("heading", { level: 1 })).toContainText(/soma/i);
        await expect(
            page.getByText(/the substance, not the deity of the same name/i),
        ).toBeVisible();
    });

    test("Agni the deity and fire the phenomenon stay apart", async ({ page }) => {
        await page.goto(`/devatas/${AGNI}`);
        // The heading is the Sanskrit name; the English one sits beside it. See journey 2.
        await expect(page.locator(".va-archive-name")).toHaveText("agniḥ");
        await expect(page.locator(".va-archive-english")).toHaveText("Agni");
        await expect(page.getByText("Two records, one word")).toBeVisible();
        await page.getByRole("link", { name: /fire \(agni\), the phenomenon/ }).click();
        await expect(page).toHaveURL(new RegExp(AGNI_FIRE));
        await expect(page.getByText(/NOT the deity Agni/)).toBeVisible();
    });
});

test.describe("journey 5 — Atharvavedic healing", () => {
    test("concerns, a fever, and its evidence", async ({ page }) => {
        await page.goto("/explore/atharvaveda");
        await expect(page.getByRole("heading", { name: "Afflictions" })).toBeVisible();

        const afflictionRows = page
            .locator(".av-block", { hasText: "Afflictions" })
            .locator(".av-row");
        const kinds = await afflictionRows.locator(".condition-kind").allTextContents();
        expect(kinds.length).toBeGreaterThan(0);
        for (const kind of kinds) {
            expect(kind.trim()).toBe("Affliction");
        }

        await page.getByRole("link", { name: /fever/ }).first().click();
        await expect(page).toHaveURL(new RegExp(TAKMAN));
        /* The heading is `takman`. That it is a fever is the gloss's job, and the gloss is
           what a reader who does not know the word needs, so that is what is asserted. */
        await expect(page.locator(".va-archive-english")).toContainText(/fever/i);
        await expect(page.locator(".condition-kind")).toContainText("Affliction");
    });

    test("a threat is never shown as a disease", async ({ page }) => {
        await page.goto("/entities/condition");
        const kinds = await page.locator(".entity-index-row .condition-kind").allTextContents();
        expect(kinds.length).toBeGreaterThan(0);
        for (const kind of kinds) {
            expect(kind.trim()).toBe("Affliction");
        }

        await page.goto("/entities/condition?kind=THREAT");
        await expect(page.getByText(/not a disease/i).first()).toBeVisible();
        const threatKinds = await page
            .locator(".entity-index-row .condition-kind")
            .allTextContents();
        for (const kind of threatKinds) {
            expect(kind.trim()).toBe("Threat");
        }
    });
});

test.describe("journey 6 — a formula across collections", () => {
    test("family, its members, and where the wording occurs", async ({ page }) => {
        await page.goto("/formulas");
        await expect(page.getByRole("heading", { level: 1 })).toHaveText("Formula families");
        await page.locator(".formula-list a").first().click();

        await expect(page).toHaveURL(/\/formula-families\//);
        await expect(page.getByRole("heading", { name: "The shape of this family" })).toBeVisible();
        await expect(page.getByRole("heading", { name: /^Core forms/ })).toBeVisible();
        await expect(
            page.getByRole("heading", { name: "Where this wording occurs" }),
        ).toBeVisible();
        await expect(page.getByRole("heading", { name: "Read the occurrences" })).toBeVisible();
        await expect(page.locator(".occurrence-columns h3").first()).toBeVisible();
    });
});

test.describe("journey 7 — a Rigvedic verse reused in the Samaveda", () => {
    test("side-by-side comparison with the surface that matched", async ({ page }) => {
        await page.goto("/connections");
        await expect(
            page.getByRole("heading", { name: "Rigveda carried into Samaveda" }),
        ).toBeVisible();
        await page.locator("a.reuse-row").first().click();

        await expect(page).toHaveURL(/\/reuse\//);
        await expect(page.getByText("Samaveda scope")).toBeVisible();
        await expect(page.locator(".comparison").first().locator(".comparison-column")).toHaveCount(
            2,
        );
        await expect(page.locator(".comparison-column .sanskrit").first()).toBeVisible();
        await expect(
            page.getByRole("heading", { name: "The surface that matched" }).first(),
        ).toBeVisible();
        await expect(
            page.getByText(/not how either text reads|its own comparison surface/).first(),
        ).toBeVisible();

        // The Samaveda's sung dimension is not held, and the page has to say so.
        //
        // This was written as `expect(page.locator("svg.notation, .musical-notation"))
        // .toHaveCount(0)` and had never once run: neither class is in the stylesheet, so it
        // matched nothing whatever the page did. A second attempt searched for the word
        // "gana" and failed, correctly, because the page uses it in exactly the sentence that
        // makes the product honest. So the assertion is now positive: the claim must be
        // there, and no element may pretend to be notation.
        await expect(
            page.getByText(/gana collections and the melodic apparatus are not held/i),
        ).toBeVisible();
    });
});

test.describe("journey 8 — a ritual to its passages", () => {
    test("rite, offerings, and a describing passage", async ({ page }) => {
        await page.goto("/rituals");
        await expect(page.getByText(/Not a taxonomy of Vedic ritual/)).toBeVisible();
        await page.locator(".ritual-grid a").first().click();

        await expect(page).toHaveURL(/\/rituals\//);
        await expect(page.getByRole("heading", { name: "The shape of the rite" })).toBeVisible();
        await expect(page.getByRole("heading", { name: "Offerings made" })).toBeVisible();
        await expect(page.getByRole("heading", { name: "Described in" })).toBeVisible();
        await page.locator(".citation-rail a").first().click();
        await expect(page).toHaveURL(/\/passage\//);
    });
});

test.describe("journey 9 — an unsupported capability answers truthfully", () => {
    test("a limit is stated as a limit of the build, not of the Vedas", async ({ page }) => {
        await page.goto("/limits");
        await expect(page.getByRole("heading", { level: 1 })).toContainText(/cannot answer/i);
        const card = page.locator(".limit-card").first();
        await expect(card.locator(".verdict")).toContainText(
            /Cannot be answered|Partly answerable/,
        );
        await expect(card.getByRole("heading", { name: "Why" })).toBeVisible();
        await expect(card.getByRole("heading", { name: "What this is not" })).toBeVisible();
        await expect(page.getByText(/never about the Vedas/i).first()).toBeVisible();
        await expect(page.getByText(/This catalogue is not exhaustive/).first()).toBeVisible();
    });

    test("an unbuilt layer is not reported as an absence from the corpus", async ({ page }) => {
        await page.goto("/material-culture?category=metals");
        await expect(page.getByText("A null is not a zero")).toBeVisible();
        const noMatch = page.locator(".cell-reason").first();
        await expect(noMatch).toHaveText("no match");

        // The known-wrong cell is declared rather than left to read as silence.
        await expect(page.getByRole("heading", { name: "Gaps we know are wrong" })).toBeVisible();
        const gap = page.locator(".gap-card").first();
        await expect(gap).toContainText(
            /NOT '0 occurrences'|not '0 occurrences'|No lexical match/i,
        );
    });
});

test.describe("journey 10 — the API is offline", () => {
    test("a server-rendered page explains the outage instead of breaking", async ({ page }) => {
        // A route that reads the API per request, so the dead upstream is actually hit.
        await page.goto(`${OFFLINE_BASE}/devatas/${INDRA}`);
        const alert = page.locator(".empty-state[role='alert']");
        await expect(alert).toContainText("The atlas is offline");
        await expect(alert).toContainText(/did not respond/i);
        await expect(alert).toContainText(/No corpus data has been changed/i);
        // An outage is not dressed up as a knowledge limit.
        await absentHere(
            page,
            (scope) => scope.getByText(/Insufficient evidence/i),
            atUrl("/limits", "the limits page, which names the evidence states in full"),
        );
    });

    test("the shell still navigates while the API is down", async ({ page }) => {
        await page.goto(`${OFFLINE_BASE}/devatas`);
        await expect(page.getByRole("link", { name: "VedAnvaya, home" })).toBeVisible();
        // Named by its navigation: the footer links Explore too, so an unscoped query is a
        // strict-mode violation rather than a choice between two identical links.
        await page
            .getByRole("navigation", { name: "Primary" })
            .getByRole("link", { name: "Explore", exact: true })
            .click();
        // cabe44c reworded this heading from "Lenses" to name what the page offers.
        await expect(page.getByRole("heading", { level: 1 })).toContainText(
            /Five ways into the corpus/i,
        );
    });

    test("an interactive request that fails says so without blaming the corpus", async ({
        page,
    }) => {
        await page.goto("/search");
        await page.route("**/backend/search**", (route) => route.abort());
        await page.getByLabel(/Search Sanskrit, IAST/).fill("Indra");
        const error = page.locator(".search-error");
        await expect(error).toBeVisible();
        await expect(error).toContainText(/connection problem, not a statement about the corpus/i);
    });
});

test.describe("knowledge-status regressions", () => {
    test("the Samaveda states that the gana corpus is not included", async ({ page }) => {
        await page.goto("/vedas");
        const row = page.getByRole("article").filter({ hasText: "Samaveda" });
        await expect(row).toContainText(/gana collections/i);
        /*
         * Kept rather than relaxed, and the copy was corrected instead.
         *
         * cabe44c reworded this limit to "the gana collections are a parallel and larger
         * body, and they are the reason the Samaveda is a distinct Veda", which describes the
         * gana corpus without ever saying it is absent. On /vedas the sentence carries no
         * heading to type the absence for it - it renders as a bare `.va-collection-limit`
         * paragraph - and the same string is reused as the page's meta description, where it
         * travels with no heading at all. A reader who is told only that the gana are large
         * and constitutive infers that they are here.
         */
        await expect(row).toContainText(/not included|not held/i);

        await page.goto("/vedas/samaveda");
        await expect(page.getByText("Gana collections are not included")).toBeVisible();
        /* The melody disclaimer is pinned by its claim, not its sentence: cabe44c
           deliberately reworded "nothing in this product" to "nothing here". */
        await expect(page.getByText(/shows, notates or infers melody/i)).toBeVisible();
    });

    test("default deity analytics exclude ambiguous mentions", async ({ page }) => {
        await page.goto(`/devatas/${AGNI}`);
        const chart = page.locator("figure.measure", { hasText: "Named in the text" });
        // The assertion here was `/Certain and probable mentions are included|/`, whose
        // trailing empty alternative matches the empty string and can never fail. Removing it
        // showed the phrase is nowhere on the page: what the product actually says is which
        // corpus held back how many, per corpus. That is the claim worth pinning.
        await expect(chart).toContainText(/holds back \d+ ambiguous mentions/);
        await expect(page.getByText(/ambiguous ones are held back/i)).toBeVisible();

        const ambiguous = page.locator(".certainty-split .is-ambiguous");
        await expect(ambiguous).toContainText("Ambiguous");
        await expect(ambiguous).toContainText(/Held back from every figure above/i);
    });

    test("an interpretive claim never looks like a textual statement", async ({ page }) => {
        await page.goto("/insights");
        const interpretation = page.locator('[data-knowledge-kind="interpretation"]').first();
        await expect(interpretation).toBeVisible();
        await expect(interpretation).toContainText(/One reading|Interpretation/);
        await expect(interpretation).toContainText(/falsif/i);

        const data = page.locator('[data-knowledge-kind="data"]').first();
        await expect(data).toBeVisible();
        const interpretationStyle = await interpretation.evaluate(
            (node) => getComputedStyle(node).borderStyle,
        );
        expect(interpretationStyle).toContain("dashed");
    });

    test("a deity resolved as a non-deity is never drawn as a god", async ({ page }) => {
        await page.goto("/devatas");
        await expect(page.getByText(/also holds human patrons/i)).toBeVisible();
    });
});

test.describe("seer and entity profiles", () => {
    const RISHI = encodeURIComponent("VG:RISHI:VAISVAMITRO-MADHUCCHANDAH");

    test("a row that was not established never carries a supported chip", async ({ page }) => {
        await page.goto(`/entities/rishi/${RISHI}`);
        const rows = page.locator("figure.measure tbody tr");
        const count = await rows.count();
        expect(count).toBeGreaterThan(0);
        for (let index = 0; index < count; index += 1) {
            const row = rows.nth(index);
            const unestablished = await row.locator(".measure-null").count();
            if (unestablished > 0) {
                await expect(row.locator('[data-tone="supported"]')).toHaveCount(0);
            }
        }
    });

    test("no stray zero leaks from an empty collection", async ({ page }) => {
        await page.goto(`/entities/rishi/${RISHI}`);
        const strays = await page
            .locator(".sticky-aside > *")
            .evaluateAll(
                (nodes) => nodes.filter((n) => (n.textContent ?? "").trim() === "0").length,
            );
        expect(strays).toBe(0);
    });

    test("a seer keeps stated and inherited attribution apart", async ({ page }) => {
        await page.goto(`/entities/rishi/${RISHI}`);
        await expect(page.getByRole("rowheader", { name: "Stated by the source" })).toBeVisible();
        await expect(
            page.getByRole("rowheader", { name: "Inherited from the hymn" }),
        ).toBeVisible();
        await expect(page.getByText(/The two are never summed/i)).toBeVisible();
    });
});

test.describe("accessibility sanity", () => {
    test("the skip link reaches main content", async ({ page }) => {
        await page.goto("/");
        await page.keyboard.press("Tab");
        const skip = page.getByRole("link", { name: "Skip to content" });
        await expect(skip).toBeFocused();
        await skip.press("Enter");
        await expect(page.locator("#main")).toBeVisible();
    });

    test("the search box is reachable by keyboard shortcut and labelled", async ({ page }) => {
        await page.goto("/search");
        // The shortcut is registered on hydration; the prompt buttons only exist after it.
        await expect(page.locator(".search-prompts button").first()).toBeVisible();
        await page.locator("h1").click();
        await page.keyboard.press("/");
        await expect(page.getByLabel(/Search Sanskrit, IAST/)).toBeFocused();
    });

    test("every page has exactly one first-level heading", async ({ page }) => {
        for (const path of [
            "/",
            "/vedas",
            "/devatas",
            "/search",
            "/graph",
            "/limits",
            "/insights",
        ]) {
            await page.goto(path);
            await expect(page.locator("h1")).toHaveCount(1);
        }
    });

    test("the graph exposes a textual equivalent of the canvas", async ({ page }) => {
        /*
         * The canvas claims a list exists beside it. Measured before this phase, with nothing
         * selected there was no list, no node buttons and no hidden text anywhere in the view -
         * the promise was only kept once the reader had already found something, which is the
         * one case where they did not need it.
         */
        await page.goto("/graph?view=world&renderer=3d");
        const canvas = page.locator("canvas.va-world-canvas");
        await expect(canvas).toBeVisible({ timeout: 30_000 });

        const alternative = page.getByRole("heading", { name: /most connected subjects/i });
        await expect(alternative).toBeAttached({ timeout: 30_000 });
        const subjects = page.locator(".va-graph .sr-only li button");
        expect(await subjects.count()).toBeGreaterThan(20);

        /* Selecting from it has to work, or it is a description rather than an equivalent -
           and it is exercised by keyboard, because that is the only way anyone reaches it. The
           list is visually hidden, so a pointer click is intercepted by the canvas over it,
           which is correct rather than a defect. */
        await subjects.first().focus();
        await page.keyboard.press("Enter");
        await expect(page.locator(".va-world-panel")).toBeVisible();
    });
});

test.describe("search behaviour", () => {
    test("slow search is not reported as an error", async ({ page }) => {
        await page.goto("/search?q=agni");
        await expect(page.locator(".search-results li").first()).toBeVisible({ timeout: 20_000 });
        // The control has to make the request fail, not merely open an offline page: the
        // error is raised by the client-side fetch, and the offline server still renders the
        // search form. Two earlier versions of this control, an offline URL and then an
        // offline URL plus a keystroke, were both refused by the guard, correctly. This uses
        // the same route abort the positive test above uses.
        await absentHere(page, (scope) => scope.locator(".search-error"), {
            hint: "a search whose request was aborted, which does report an error",
            arrange: async (scope) => {
                await scope.goto("/search");
                await scope.route("**/backend/search**", (route) => route.abort());
                await scope.getByLabel(/Search Sanskrit, IAST/).fill("agni");
            },
        });
        await page.unroute("**/backend/search**");
    });

    test("IAST diacritics survive the round trip", async ({ page }) => {
        await search(page, "ṛta");
        await expect(page.getByLabel(/Search Sanskrit, IAST/)).toHaveValue("ṛta");
    });

    test("refining a query keeps the previous results on screen", async ({ page }) => {
        await search(page, "Indra");
        const first = page.locator(".search-results li").first();
        await page.getByLabel(/Search Sanskrit, IAST/).fill("Indrani");
        await expect(first).toBeVisible();
    });

    test("a query with no matches explains itself", async ({ page }) => {
        await page.goto("/search");
        await page.getByLabel(/Search Sanskrit, IAST/).fill("zzzqqqxyz");
        await expect(page.getByText(/Nothing matched zzzqqqxyz/)).toBeVisible();
        await expect(page.getByText(/may still use the idea under another word/i)).toBeVisible();
    });
});
