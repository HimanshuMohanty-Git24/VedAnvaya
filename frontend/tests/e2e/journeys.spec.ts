import { expect, test, type Page } from "@playwright/test";
import { OFFLINE_BASE } from "../../playwright.config";
import { absentHere, textAbsentHere } from "./guards";

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
        await expect(page.getByRole("heading", { level: 1 })).toContainText(/four collections/i);

        await page.getByRole("link", { name: "Explore the Vedas" }).click();
        await expect(page).toHaveURL(/\/vedas$/);

        await page
            .getByRole("article")
            .filter({ hasText: "Rigveda Samhita" })
            .getByRole("link", { name: /Open collection/ })
            .click();
        await expect(page).toHaveURL(/\/vedas\/rigveda$/);

        // Native hierarchy, not a common template.
        await expect(page.getByRole("heading", { name: /Browse by Mandala/ })).toBeVisible();

        await page.getByRole("button", { name: /Expand RV 1$/ }).click();
        await page.getByRole("button", { name: /Expand RV 1\.1$/ }).click();
        await page.getByRole("link", { name: "RV 1.1.1", exact: true }).click();

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
        await expect(page.getByRole("heading", { level: 1 })).toContainText("Indra");
        await expect(page.getByRole("heading", { name: "Across the four Vedas" })).toBeVisible();

        await page.locator(".citation-list a").first().click();
        await expect(page).toHaveURL(/\/passage\//);
        await expect(page.locator(".sanskrit").first()).toBeVisible();
    });
});

test.describe("journey 3 — graph to evidence", () => {
    test("select a relationship and read why it exists", async ({ page }) => {
        await page.goto(`/graph?node=${INDRA}`);
        await expect(page.locator(".graph-canvas canvas").first()).toBeVisible();
        await expect(page.locator(".graph-legend .legend-chip").first()).toBeVisible();

        // Every edge is reachable from the node list without clicking the canvas.
        await page.getByRole("group", { name: /Show or hide entity kinds/ }).waitFor();

        // Drive the evidence panel through a real relationship id from the API.
        const edgeId = await page.evaluate(async () => {
            const response = await fetch(
                `/backend/graph/neighborhood/${encodeURIComponent("VG:DEVATA:INDRAH")}?depth=1&limit_per_type=4`,
            );
            const data = await response.json();
            return data.edges[0].id as string;
        });
        expect(edgeId).toBeTruthy();

        const explanation = await page.evaluate(async (id: string) => {
            const response = await fetch(`/backend/graph/relationships/${encodeURIComponent(id)}`);
            return response.json();
        }, edgeId);
        expect(explanation.why).toBeTruthy();

        // The canvas renders the same edges the API returned.
        const nodeCount = await page.locator(".graph-node-list li").count();
        expect(nodeCount).toBeGreaterThan(0);
    });

    test("the evidence panel is reachable without touching the canvas", async ({ page }) => {
        await page.goto(`/graph?node=${INDRA}`);
        const relationship = page.locator(".selected-relationships button").first();
        await expect(relationship).toBeVisible();
        await relationship.click();

        const drawer = page.getByRole("dialog");
        await expect(drawer).toBeVisible();
        await expect(drawer.getByText("Why are these connected?")).toBeVisible();
        await expect(drawer.getByRole("heading", { name: "Why" })).toBeVisible();
        await expect(drawer.getByText("How it was established")).toBeVisible();

        // Internal grades stay behind progressive disclosure.
        const technical = drawer.locator("details.evidence-technical");
        await expect(technical).toBeVisible();
        await expect(technical).not.toHaveAttribute("open", "");

        await drawer.getByRole("button", { name: "Close the evidence panel" }).click();
        await expect(page.getByRole("dialog")).toHaveCount(0);
    });

    test("an ascription descriptor is never presented as a deity", async ({ page }) => {
        await page.goto(`/graph?node=${encodeURIComponent("VG:DEVATA:ASAMATIH")}`);
        const nodeType = page.locator(".node-type");
        await expect(nodeType).toBeVisible();
        await expect(nodeType).not.toHaveText("deity");
        await expect(
            page.getByText(/was not resolved as a deity|excluded from deity analytics/i),
        ).toBeVisible();
    });

    test("the graph never renders internal bookkeeping nodes", async ({ page }) => {
        await page.goto(`/graph?node=${INDRA}`);
        await page.locator(".graph-node-list summary").click();
        const labels = await page.locator(".graph-node-list li span").allTextContents();
        for (const label of labels) {
            expect(label.toLowerCase()).not.toMatch(
                /qaissue|qa issue|source artifact|text version|internal/,
            );
        }
    });

    test("expansion stays bounded and says what it held back", async ({ page }) => {
        await page.goto(`/graph?node=${INDRA}`);
        const bounds = page.locator(".graph-bounds");
        await expect(bounds).toContainText(/shown of \d+ loaded/);
        await expect(bounds).toContainText(/Only a bounded sample is drawn/);
        await expect(
            page.getByRole("heading", { name: /Held back to keep this readable/ }),
        ).toBeVisible();
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
        await expect(page.getByRole("heading", { level: 1 })).toHaveText("Agni");
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
        await expect(page.getByRole("heading", { level: 1 })).toContainText(/fever/i);
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

        // No fake musical notation anywhere on a Samaveda surface.
        //
        // This was written as `svg.notation, .musical-notation` and had never once run: no
        // such class exists in the stylesheet, so the guard matched nothing whatever the page
        // did. What it is actually for is the claim that the Samaveda's sung dimension is not
        // held, and the honest way to check that is to look for the claim rather than for
        // markup nobody writes.
        await expect(page.getByText(/gana|sung|musical/i)).toHaveCount(0);
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
        await textAbsentHere(page, /Insufficient evidence/i, {
            controlUrl: "/limits",
            controlHint: "the limits page, which names the evidence states in full",
        });
    });

    test("the shell still navigates while the API is down", async ({ page }) => {
        await page.goto(`${OFFLINE_BASE}/devatas`);
        await expect(page.getByRole("link", { name: "VedAnvaya, home" })).toBeVisible();
        await page.getByRole("link", { name: "Explore", exact: true }).click();
        await expect(page.getByRole("heading", { level: 1 })).toContainText("Lenses");
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
        await expect(row).toContainText(/not included|not held/i);

        await page.goto("/vedas/samaveda");
        await expect(page.getByText("Gana collections are not included")).toBeVisible();
        await expect(
            page.getByText(/nothing in this product shows, notates or infers/i),
        ).toBeVisible();
    });

    test("default deity analytics exclude ambiguous mentions", async ({ page }) => {
        await page.goto(`/devatas/${AGNI}`);
        const chart = page.locator("figure.measure", { hasText: "Named in the text" });
        await expect(chart).toContainText(/Certain and probable mentions are included/);
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
        await page.goto(`/graph?node=${INDRA}`);
        const canvas = page.getByRole("img", { name: /Knowledge graph showing/ });
        await expect(canvas).toBeVisible();
        await expect(canvas).toHaveAttribute("aria-label", /textual list of the same nodes/);
    });
});

test.describe("search behaviour", () => {
    test("slow search is not reported as an error", async ({ page }) => {
        await page.goto("/search?q=agni");
        await expect(page.locator(".search-results li").first()).toBeVisible({ timeout: 20_000 });
        await absentHere(page, ".search-error", {
            controlUrl: `${OFFLINE_BASE}/search?q=agni`,
            controlHint: "a search against the offline backend, which does report an error",
        });
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
