import { expect, test } from "@playwright/test";
import { absentHere, atUrl } from "./guards";

/**
 * The recitation surface, at the two things a reader can actually be misled about:
 * what the audio covers, and whether it exists.
 *
 * These run against the live API and the real catalog, so they assert on the copy a reader
 * sees rather than on a fixture. That is the point: the label is composed server-side
 * precisely so it cannot drift from the catalog, and a test against a stub would not catch
 * it drifting.
 */

const RV_1_1_1 = encodeURIComponent("VG:RV:SAK:M01:S001:V001");
// Rigveda 8.71.1. Its recitation is the source's 8.60.1, because the source numbers
// Mandala 8 in Griffith's order with the Valakhilya at the end of the book. A key-for-key
// mapping would play the wrong hymn here.
const RV_8_71_1 = encodeURIComponent("VG:RV:SAK:M08:S071:V001");
// Rigveda 8.49.1, one of the eleven Valakhilya hymns the source does not publish at all.
const RV_8_49_1 = encodeURIComponent("VG:RV:SAK:M08:S049:V001");
// A Samavedic verse. No source publishes Kauthuma arcika audio per verse.
const SV_VERSE = encodeURIComponent("VG:SV:KAU:ARANYA:D01:V01");

test.describe("reader recitation", () => {
    test("a verse offers its own recitation and says so", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const recitation = page.locator("section.recitation");
        await expect(recitation).toBeVisible();

        // The server-composed label, rendered verbatim. "this verse" is the claim the
        // catalog can actually support, and the one the previous source could not.
        await expect(recitation).toContainText("Recitation of this verse");
        await expect(recitation).not.toContainText("whole sukta");
    });

    test("the play control has an accessible name naming what it plays", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const play = page.getByRole("button", { name: /^Play / });
        await expect(play).toBeVisible();
        await expect(play).toHaveAccessibleName(/recitation of this verse/i);
    });

    test("the play control is reachable by keyboard", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const play = page.getByRole("button", { name: /^Play / });
        await play.focus();
        await expect(play).toBeFocused();
    });

    test("the seek control is labelled and announces its position", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const seek = page.getByRole("slider", { name: /Seek within this recitation/ });
        await expect(seek).toBeVisible();
        await expect(seek).toHaveAttribute("aria-valuetext", /0:00/);
        // Disabled until playback establishes a duration. That is the visible consequence
        // of `preload="none"`, which exists so that opening a reader page does not fetch
        // audio the reader never asked for -- the streaming route pulls a whole file to
        // answer any request, metadata included.
        await expect(seek).toBeDisabled();
    });

    test("playback speed is offered as a labelled control", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const speed = page.getByRole("combobox", { name: /Playback speed/ });
        await expect(speed).toBeVisible();
        await expect(speed).toHaveValue("1");
    });

    test("provenance is available but secondary", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const disclosure = page.getByText("About this recording");
        await expect(disclosure).toBeVisible();
        await disclosure.click();

        const recitation = page.locator("section.recitation");
        await expect(recitation).toContainText("VedSearch");
        await expect(recitation).toContainText("one verse");
        // The mapping was checked against this corpus's own text, and says so.
        await expect(recitation).toContainText(/Confirmed/);
        // An unnamed reciter is stated as unstated, never invented.
        await expect(recitation).toContainText("Not stated by the source");
    });

    test("the source link opens in a new window", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        await page.getByText("About this recording").click();
        const link = page.getByRole("link", { name: /Open the original source/ });
        await expect(link).toHaveAttribute("target", "_blank");
        await expect(link).toHaveAttribute("rel", /noreferrer/);
    });

    test("the Sanskrit stays the primary object on the page", async ({ page }) => {
        await page.goto(`/passage/${RV_1_1_1}`);
        const sanskrit = page.locator(".sanskrit").first();
        const player = page.locator("section.recitation");
        const sanskritBox = await sanskrit.boundingBox();
        const playerBox = await player.boundingBox();
        expect(sanskritBox).not.toBeNull();
        expect(playerBox).not.toBeNull();
        // The reading surface comes first and the player sits beneath it.
        expect(sanskritBox!.y).toBeLessThan(playerBox!.y);
    });
});

test.describe("recitation across the Valakhilya boundary", () => {
    test("a hymn past the boundary still gets its own verse recitation", async ({ page }) => {
        await page.goto(`/passage/${RV_8_71_1}`);
        const recitation = page.locator("section.recitation");
        await expect(recitation).toBeVisible();
        await expect(recitation).toContainText("Recitation of this verse");
        await expect(page.getByRole("heading", { level: 1 })).toHaveText("RV 8.71.1");
    });

    test("a Valakhilya verse offers no player rather than the wrong one", async ({ page }) => {
        await page.goto(`/passage/${RV_8_49_1}`);
        await expect(page.getByRole("heading", { level: 1 })).toHaveText("RV 8.49.1");
        // The text is unaffected; only the player is absent.
        await expect(page.locator(".sanskrit").first()).toBeVisible();
        await absentHere(
            page,
            (scope) => scope.locator("section.recitation"),
            atUrl(`/passage/${RV_1_1_1}`, "RV 1.1.1, which does have a recitation"),
        );
    });
});

test.describe("absent recitation is not an error", () => {
    test("a Samavedic verse reads normally with no player", async ({ page }) => {
        await page.goto(`/passage/${SV_VERSE}`);
        await expect(page.locator(".sanskrit").first()).toBeVisible();
        await absentHere(
            page,
            (scope) => scope.locator("section.recitation"),
            atUrl(`/passage/${RV_1_1_1}`, "RV 1.1.1, which does have a recitation"),
        );
        // No broken control, and no claim that no recitation of this text exists.
        //
        // The play control has no text content at all: it is an icon whose name lives in
        // aria-label, so it has to be found by role. A first version of this guard used a CSS
        // text selector, which matched nothing even on the control, and the guard said so.
        await absentHere(
            page,
            (scope) => scope.getByRole("button", { name: /^Play / }),
            atUrl(`/passage/${RV_1_1_1}`, "RV 1.1.1, whose player offers a play button"),
        );
    });
});

test.describe("Veda page coverage figures", () => {
    test("the Rigveda states its coverage as a share, not a bare count", async ({ page }) => {
        await page.goto("/vedas/rigveda");
        const panel = page.locator(".panel", { hasText: "Recitation audio" });
        await expect(panel).toBeVisible();
        // A denominator is what stops "10,402 verses" reading as the whole collection.
        await expect(panel).toContainText(/of 10,552 verses/);
        await expect(panel).toContainText("one recording per verse");
    });

    test("the Samaveda explains its absence instead of showing a zero", async ({ page }) => {
        await page.goto("/vedas/samaveda");
        const panel = page.locator(".panel", { hasText: "Recitation audio" });
        await expect(panel).toBeVisible();
        await expect(panel).toContainText("Not available for this collection");
        // Whose absence it is: what has been published, not what the tradition holds.
        await expect(panel).toContainText(/not a statement about the tradition/);
        await expect(panel).not.toContainText("0 verses");
    });

    test("every Veda with audio names its source", async ({ page }) => {
        for (const veda of ["rigveda", "yajurveda", "atharvaveda"]) {
            await page.goto(`/vedas/${veda}`);
            const panel = page.locator(".panel", { hasText: "Recitation audio" });
            await expect(panel).toContainText("VedSearch");
        }
    });
});
