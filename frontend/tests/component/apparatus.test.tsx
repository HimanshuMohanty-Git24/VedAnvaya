import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Apparatus } from "@/components/reader/apparatus";
import { parallelFixture, readerFixture, vocabularyParallelFixture } from "../fixtures/reader";

/**
 * The apparatus rail.
 *
 * These assertions were previously made against `PassageKnowledge`, the tabbed sidebar the
 * reader used before Phase 4. That component is gone, but the distinctions it drew are the
 * product rather than the component: an ascription inherited from a hymn heading is not a
 * statement the verse makes, a named deity carries a referent certainty, a phenomenon that
 * shares a deity's name is not that deity, and shared vocabulary is not shared wording. Each
 * one survives here against the component that now draws it.
 *
 * One assertion is deliberately not carried over. The old suite opened a tab to reach each
 * group, which is exactly the behaviour Phase 4 removed, so the replacement asserts the
 * opposite: every group is present without any interaction at all.
 */

function renderApparatus(parallels = [parallelFixture, vocabularyParallelFixture]) {
    return render(
        <Apparatus reader={readerFixture} parallels={parallels} parallelsFailed={false} />,
    );
}

/** The group whose heading matches, so an assertion cannot drift into a neighbouring group. */
function group(name: RegExp) {
    return screen.getByRole("heading", { name }).closest("section") as HTMLElement;
}

describe("the apparatus rail", () => {
    it("shows every group without anything to open first", () => {
        renderApparatus();
        for (const heading of [
            /Ascribed in the apparatus/i,
            /Named inside this verse/i,
            /Ideas, acts and things/i,
            /Connected passages/i,
        ]) {
            expect(screen.getByRole("heading", { name: heading })).toBeVisible();
        }
        // The rail is read alongside the verse. Nothing in it sits behind a control.
        expect(screen.queryAllByRole("tab")).toHaveLength(0);
    });

    it("separates an inherited hymn heading from a statement inside the verse", () => {
        renderApparatus();
        const ascribed = group(/Ascribed in the apparatus/i);
        expect(
            within(ascribed).getByText(/not a statement inside the verse/i),
        ).toBeInTheDocument();
        /* Every ascription carries the precision it was recorded with, not a bare name. Both
           the deity and the seer here are inherited from the hymn heading, and each says so
           on its own row rather than the group carrying one note for all of them. */
        const inherited = within(ascribed).getAllByText(/Inherited from the hymn/i);
        expect(inherited).toHaveLength(2);

        // Agni is both ascribed by the apparatus and named in the verse. The two are
        // different claims, so the same deity appears under both headings.
        expect(within(ascribed).getByText("Agni")).toBeInTheDocument();
        expect(within(group(/Named inside this verse/i)).getByText("Agni")).toBeInTheDocument();
    });

    it("marks an ambiguous mention distinctly and says it is held back", () => {
        const { container } = renderApparatus();
        const ambiguous = container.querySelector('[data-certainty="ambiguous"]');
        const certain = container.querySelector('[data-certainty="certain"]');
        expect(ambiguous).toBeTruthy();
        expect(certain).toBeTruthy();
        expect(ambiguous).not.toBe(certain);

        expect(within(ambiguous as HTMLElement).getByText(/Ambiguous/i)).toBeInTheDocument();
        expect(
            within(ambiguous as HTMLElement).getByText(/Excluded from default deity analytics/i),
        ).toBeInTheDocument();
        // The certain mention carries no exclusion note.
        expect(
            within(certain as HTMLElement).queryByText(/Excluded from default/i),
        ).not.toBeInTheDocument();
        // And the count held back is stated rather than silently dropped.
        expect(screen.getByText(/held back as ambiguous/i)).toBeInTheDocument();
    });

    it("keeps a phenomenon and the deity that shares its name apart", () => {
        renderApparatus();
        const chip = screen.getByText("fire (agni)").closest("a");
        expect(chip).toHaveAttribute("href", expect.stringContaining("natural_phenomenon"));
        expect(chip).not.toHaveAttribute("href", expect.stringContaining("/devatas/"));
        expect(screen.getByText(/NOT the deity Agni/)).toBeInTheDocument();
    });

    it("does not list shared vocabulary among shared wording", () => {
        renderApparatus();
        const connected = group(/Connected passages/i);
        // The textual parallel is wording this verse shares.
        expect(within(connected).getByText("SV ARANYA 1.7")).toBeInTheDocument();
        /* The vocabulary overlap is not. Two passages naming the same deity is not evidence
           that either quotes the other, so it is never listed as a connected passage. */
        expect(within(connected).queryByText("RV 9.61.12")).not.toBeInTheDocument();
    });

    it("lists a passage connected twice once, carrying both kinds", () => {
        /* RV 1.1.1 and SV Aranya 1.7 are recorded as both a textual parallel and a text
           reuse. They are different claims so neither is dropped, but one pair is one row:
           printing two repeated the citation, and React saw two children under one key. */
        const secondKind = {
            ...parallelFixture,
            relation: "TEXTUAL_PARALLEL",
            relation_kind: "TEXTUAL_PARALLEL",
            parallel_id: "VG:ENRICH:PARALLEL:second",
        } as typeof parallelFixture;

        renderApparatus([parallelFixture, secondKind]);
        const connected = group(/Connected passages/i);
        const rows = within(connected).getAllByText("SV ARANYA 1.7");
        expect(rows).toHaveLength(1);

        // Both kinds are named on the single row rather than one winning.
        const kind = rows[0].closest("a")?.querySelector(".va-row-kind")?.textContent ?? "";
        expect(kind).toMatch(/·/);
    });

    it("reports an unreadable connection layer without implying the verse is affected", () => {
        render(
            <Apparatus reader={readerFixture} parallels={[]} parallelsFailed />,
        );
        const connected = group(/Connected passages/i);
        expect(within(connected).getByText(/could not be read just now/i)).toBeInTheDocument();
        expect(
            within(connected).getByText(/verse and its apparatus are unaffected/i),
        ).toBeInTheDocument();
        /* A failure to read the layer must never render as the sentence used for a real
           absence, which is a claim about the corpus rather than about the request. */
        expect(
            within(connected).queryByText(/No other passage in this corpus/i),
        ).not.toBeInTheDocument();
    });

    it("states an absence of parallels as a fact about this corpus only", () => {
        renderApparatus([]);
        const connected = group(/Connected passages/i);
        expect(
            within(connected).getByText(/not about the Vedas/i),
        ).toBeInTheDocument();
    });
});
