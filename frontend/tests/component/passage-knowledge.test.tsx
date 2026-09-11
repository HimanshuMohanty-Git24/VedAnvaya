import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { EvidenceDrawer } from "@/components/evidence-drawer";
import { PassageKnowledge } from "@/components/passage-knowledge";
import {
    explanationFixture,
    parallelFixture,
    readerFixture,
    vocabularyParallelFixture,
} from "../fixtures/reader";

function renderKnowledge() {
    return render(
        <PassageKnowledge
            reader={readerFixture}
            parallels={[parallelFixture, vocabularyParallelFixture]}
            parallelsFailed={false}
        />,
    );
}

describe("passage knowledge sidebar", () => {
    it("offers context, entities, connections and evidence", () => {
        renderKnowledge();
        for (const tab of ["Context", "Entities", "Connections", "Evidence"]) {
            expect(screen.getByRole("tab", { name: new RegExp(tab) })).toBeInTheDocument();
        }
    });

    it("marks an ambiguous mention distinctly and says it is held back", () => {
        const { container } = renderKnowledge();
        const ambiguous = container.querySelector('[data-certainty="ambiguous"]');
        const certain = container.querySelector('[data-certainty="certain"]');
        expect(ambiguous).toBeTruthy();
        expect(certain).toBeTruthy();
        expect(ambiguous).not.toBe(certain);
        expect(within(ambiguous as HTMLElement).getByText("Ambiguous")).toBeInTheDocument();
        expect(
            within(ambiguous as HTMLElement).getByText(/Excluded from default deity analytics/i),
        ).toBeInTheDocument();
        // The certain mention carries no exclusion note.
        expect(
            within(certain as HTMLElement).queryByText(/Excluded from default/i),
        ).not.toBeInTheDocument();
        expect(screen.getByText(/held back as ambiguous/i)).toBeInTheDocument();
    });

    it("separates an inherited hymn heading from a statement inside the verse", () => {
        renderKnowledge();
        expect(screen.getByText("Ascribed in the apparatus")).toBeInTheDocument();
        expect(screen.getByText(/not a statement inside the verse/i)).toBeInTheDocument();
        expect(screen.getByText("Named inside this verse")).toBeInTheDocument();
        expect(screen.getAllByText("Inherited from the hymn").length).toBeGreaterThan(0);
    });

    it("keeps a phenomenon and the deity that shares its name apart", async () => {
        renderKnowledge();
        await userEvent.click(screen.getByRole("tab", { name: /Entities/ }));
        const chip = screen.getByText("fire (agni)").closest("a");
        expect(chip).toHaveAttribute("href", expect.stringContaining("natural_phenomenon"));
        expect(chip).not.toHaveAttribute("href", expect.stringContaining("/devatas/"));
        expect(screen.getByText(/NOT the deity Agni/)).toBeInTheDocument();
    });

    it("does not present shared vocabulary as shared wording", async () => {
        renderKnowledge();
        await userEvent.click(screen.getByRole("tab", { name: /Connections/ }));
        expect(screen.getByText("Shared wording")).toBeInTheDocument();
        const vocabularySection = screen.getByText("Shared vocabulary", {
            selector: "h2",
        }).parentElement as HTMLElement;
        expect(
            within(vocabularySection).getByText(/That is not shared wording/i),
        ).toBeInTheDocument();
    });

    it("reports an unbuilt audio layer as unbuilt rather than showing a player", async () => {
        renderKnowledge();
        await userEvent.click(screen.getByRole("tab", { name: /Evidence/ }));
        expect(screen.queryByRole("button", { name: /play/i })).not.toBeInTheDocument();
        expect(screen.getByText(/No recitation audio exists in this graph/)).toBeInTheDocument();
    });
});

describe("evidence drawer", () => {
    it("answers in plain language before showing any internal grade", () => {
        render(
            <EvidenceDrawer
                open
                loading={false}
                data={explanationFixture}
                onOpenChange={() => {}}
            />,
        );
        expect(screen.getByText("Why are these connected?")).toBeInTheDocument();
        expect(screen.getByText(/Indra performs the action POURS/)).toBeInTheDocument();
        expect(screen.getByText("Derived")).toBeInTheDocument();
        expect(screen.getByText("Inherited from the hymn")).toBeInTheDocument();
    });

    it("hides raw tier names behind Technical details", () => {
        render(
            <EvidenceDrawer
                open
                loading={false}
                data={explanationFixture}
                onOpenChange={() => {}}
            />,
        );
        const technical = document.querySelector("details.evidence-technical");
        expect(technical).toBeTruthy();
        expect(technical).not.toHaveAttribute("open");
        expect(within(technical as HTMLElement).getByText("TIER_B")).toBeInTheDocument();
        // TIER_B never appears outside the collapsed technical block.
        const outside = document.querySelectorAll(".evidence-content > *:not(.evidence-technical)");
        for (const node of outside) {
            expect(node.textContent ?? "").not.toMatch(/TIER_[A-D]/);
        }
    });

    it("says when no passage is attached rather than showing an empty list", () => {
        render(
            <EvidenceDrawer
                open
                loading={false}
                data={explanationFixture}
                onOpenChange={() => {}}
            />,
        );
        expect(screen.getByText(/No quoted passage is attached/i)).toBeInTheDocument();
    });

    it("does not claim a review happened when no review record exists", () => {
        render(
            <EvidenceDrawer
                open
                loading={false}
                data={explanationFixture}
                onOpenChange={() => {}}
            />,
        );
        expect(screen.getByText(/records no review at all/i)).toBeInTheDocument();
    });

    it("reports a missing explanation without turning it into an error", () => {
        render(<EvidenceDrawer open loading={false} data={null} onOpenChange={() => {}} />);
        expect(screen.getByText("Insufficient evidence")).toBeInTheDocument();
        expect(screen.getByText(/its derivation record does not/i)).toBeInTheDocument();
    });
});
