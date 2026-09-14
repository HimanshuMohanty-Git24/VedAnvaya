import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidenceDrawer } from "@/components/evidence-drawer";
import { explanationFixture } from "../fixtures/reader";

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
