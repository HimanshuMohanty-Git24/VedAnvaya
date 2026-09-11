import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MeasureChart } from "@/components/measure";
import { SeerPanel } from "@/components/seer-panel";
import { Caveat, InterpretationFrame, KnowledgeStatus } from "@/components/status";
import { seerWithoutFamilyFixture } from "../fixtures/reader";

describe("KnowledgeStatus", () => {
    it("carries its status and tone as data attributes so styling is not the only signal", () => {
        const { container } = render(<KnowledgeStatus status="INSUFFICIENT_EVIDENCE" />);
        const node = container.querySelector(".knowledge-status");
        expect(node).toHaveAttribute("data-status", "INSUFFICIENT_EVIDENCE");
        expect(node).toHaveAttribute("data-tone", "insufficient");
        expect(node).toHaveTextContent("Insufficient evidence");
    });

    it("explains a missing layer without claiming the corpus is silent", () => {
        render(<KnowledgeStatus status="NOT_BUILT" />);
        expect(screen.getByText(/Not yet modelled/)).toBeInTheDocument();
        expect(screen.getByText(/has not been built/i)).toBeInTheDocument();
        expect(screen.queryByText(/does not occur/i)).not.toBeInTheDocument();
    });

    it("prefers a supplied note over the generic description", () => {
        render(
            <KnowledgeStatus
                status="PARTIAL"
                note="The ascription apparatus exists for the Rigveda only."
            />,
        );
        expect(
            screen.getByText(/ascription apparatus exists for the Rigveda only/),
        ).toBeInTheDocument();
    });
});

describe("Caveat", () => {
    it("keeps a short scope note open", () => {
        render(<Caveat title="Samaveda scope">Gana collections are not included.</Caveat>);
        expect(screen.getByText("Samaveda scope")).toBeInTheDocument();
        expect(screen.getByText(/Gana collections are not included/)).toBeVisible();
    });

    it("collapses a long scholarly caveat behind a summary", () => {
        const long = "A ".repeat(200);
        const { container } = render(<Caveat title="How this was measured">{long}</Caveat>);
        expect(container.querySelector("details.caveat")).toBeTruthy();
        expect(screen.getByText("How this was measured")).toBeInTheDocument();
    });
});

describe("InterpretationFrame", () => {
    it("marks interpretation as a different kind of knowledge from a corpus fact", () => {
        const { container } = render(
            <InterpretationFrame>
                <blockquote>The corpus does not lexically distinguish Agni from agni.</blockquote>
            </InterpretationFrame>,
        );
        const frame = container.querySelector("[data-knowledge-kind]");
        expect(frame).toHaveAttribute("data-knowledge-kind", "interpretation");
        expect(screen.getByText("Interpretation")).toBeInTheDocument();
        expect(screen.getByText(/not a statement the texts make/i)).toBeInTheDocument();
    });
});

describe("MeasureChart", () => {
    const rows = [
        { key: "RV", label: "Rigveda", value: 1359 },
        { key: "SV", label: "Samaveda", value: null, status: "NO_LEXICAL_MATCH" },
    ];

    it("states what it counts and over what scope", () => {
        render(
            <MeasureChart
                id="t"
                title="Named in the text"
                definition="Passages in which a registered form occurs."
                scope="Measured over RV, SV, YV, AV."
                caveat="Counts are lower bounds."
                rows={rows}
            />,
        );
        expect(screen.getByText("Named in the text")).toBeInTheDocument();
        expect(
            screen.getAllByText(/Passages in which a registered form occurs/).length,
        ).toBeGreaterThan(0);
        expect(screen.getByText(/Measured over RV, SV, YV, AV/)).toBeInTheDocument();
        expect(screen.getByText(/Counts are lower bounds/)).toBeInTheDocument();
    });

    it("renders a null as an explained absence, never as a zero", () => {
        const { container } = render(
            <MeasureChart id="t" title="Named" definition="d" rows={rows} />,
        );
        const samaveda = screen.getByRole("row", { name: /Samaveda/ });
        expect(within(samaveda).getByText("not established")).toBeInTheDocument();
        expect(within(samaveda).queryByText("0")).not.toBeInTheDocument();
        expect(within(samaveda).getByText("No lexical match")).toBeInTheDocument();
        // A null row draws no bar at all: only the Rigveda row gets one.
        expect(samaveda.querySelector(".measure-bar")).toBeNull();
        expect(container.querySelectorAll(".measure-bar")).toHaveLength(1);
    });

    it("is readable as a table for assistive technology", () => {
        render(<MeasureChart id="t" title="Named" definition="d" rows={rows} unit="passages" />);
        expect(screen.getByRole("table")).toBeInTheDocument();
        expect(screen.getByRole("rowheader", { name: "Rigveda" })).toBeInTheDocument();
        expect(screen.getByText("1,359")).toBeInTheDocument();
    });
});

describe("SeerPanel", () => {
    it("says a missing family is not established rather than leaving it blank", () => {
        render(<SeerPanel seer={seerWithoutFamilyFixture} />);
        expect(screen.getByText(/Not established from current evidence/i)).toBeInTheDocument();
    });

    it("explains a name that sits in the seer slot but is not a seer", () => {
        render(<SeerPanel seer={seerWithoutFamilyFixture} />);
        expect(screen.getByText(/occupies a traditional seer slot/i)).toBeInTheDocument();
        expect(screen.getByText(/not presented here as a composer of hymns/i)).toBeInTheDocument();
    });

    it("keeps source-stated and inherited attribution apart", () => {
        render(<SeerPanel seer={seerWithoutFamilyFixture} />);
        expect(screen.getByRole("rowheader", { name: "Stated by the source" })).toBeInTheDocument();
        expect(
            screen.getByRole("rowheader", { name: "Inherited from the hymn" }),
        ).toBeInTheDocument();
        expect(screen.getByText(/never summed/i)).toBeInTheDocument();
    });
});
