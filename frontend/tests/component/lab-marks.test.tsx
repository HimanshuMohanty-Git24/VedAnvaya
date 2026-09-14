import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BarTable, CorpusStrip, ShareStrip, type Datum } from "@/components/lab/marks";
import { PlateLabel, PlateTakeaway } from "@/components/lab/plate";
import { PLATES_BY_SLUG } from "@/lib/lab";

/**
 * The marks, tested for the three things that would make them lie.
 *
 * A null drawn as a zero-length bar, a measured zero drawn as a visible tick, and a corpus
 * silently dropped from a four-corpus figure. Each of those is a figure that renders
 * beautifully and states something false, so none of them would be caught by a screenshot.
 */

const width = (node: Element | null) => (node as HTMLElement | null)?.style.width;

describe("BarTable", () => {
    const rows: Datum[] = [
        { key: "a", label: "Indra", value: 3566 },
        { key: "b", label: "Agni", value: 1708 },
        { key: "c", label: "Vata", value: null, absence: "no mention edge" },
        { key: "d", label: "Nobody", value: 0 },
    ];

    it("draws no bar for a row the layer did not reach, and says so in words", () => {
        const { container } = render(<BarTable caption="Deities" rows={rows} />);
        const vata = screen.getByRole("row", { name: /Vata/ });
        expect(within(vata).getByText("no mention edge")).toBeInTheDocument();
        expect(within(vata).getByText("not established")).toBeInTheDocument();
        expect(vata.querySelector(".va-rank-bar")).toBeNull();
        expect(container.querySelectorAll(".va-rank-bar")).toHaveLength(3);
    });

    it("draws a measured zero as no mark at all rather than as a hairline", () => {
        /* A 0.4% floor beside a 10,502 makes "none released" read as "almost none". A zero is
           the one value that must occupy no width. */
        render(<BarTable caption="Deities" rows={rows} />);
        const nobody = screen.getByRole("row", { name: /Nobody/ });
        expect(width(nobody.querySelector(".va-rank-bar"))).toBe("0%");
        expect(within(nobody).getByText("0")).toBeInTheDocument();
    });

    it("scales every bar against one ceiling, so two rows are comparable", () => {
        const { container } = render(<BarTable caption="Deities" rows={rows} />);
        const bars = [...container.querySelectorAll(".va-rank-bar")] as HTMLElement[];
        expect(bars[0].style.width).toBe("100%");
        expect(Number.parseFloat(bars[1].style.width)).toBeCloseTo((1708 / 3566) * 100, 1);
    });

    it("honours an explicit ceiling so two tables can share a scale", () => {
        const { container } = render(<BarTable caption="Deities" max={7132} rows={rows} />);
        const bars = [...container.querySelectorAll(".va-rank-bar")] as HTMLElement[];
        expect(bars[0].style.width).toBe("50%");
    });

    it("is a table before it is a chart, with a caption and row headers", () => {
        render(<BarTable caption="Verses naming each deity" rows={rows} />);
        expect(screen.getByRole("table", { name: /Verses naming each deity/ })).toBeInTheDocument();
        expect(screen.getByRole("rowheader", { name: /Indra/ })).toBeInTheDocument();
    });
});

describe("CorpusStrip", () => {
    const figures = {
        RV: { value: 10502 },
        SV: { value: 0 },
        YV: { value: 1903 },
        AV: { value: null, absence: "not reached" },
    };

    it("always shows all four collections, including the ones with nothing to show", () => {
        render(<CorpusStrip caption="Translations" figures={figures} />);
        for (const code of ["RV", "SV", "YV", "AV"]) {
            expect(screen.getByRole("rowheader", { name: new RegExp(code) })).toBeInTheDocument();
        }
    });

    it("separates a measured zero from a collection the layer did not reach", () => {
        const { container } = render(<CorpusStrip caption="Translations" figures={figures} />);
        const rows = [...container.querySelectorAll("tbody tr")];
        const sv = rows[1];
        const av = rows[3];
        // SV: a real zero. A bar of no width, and the figure printed as 0.
        expect(width(sv.querySelector(".va-strip-bar"))).toBe("0%");
        expect(within(sv as HTMLElement).getByText("0")).toBeInTheDocument();
        // AV: never reached. No bar at all, and a stated reason instead.
        expect(av.querySelector(".va-strip-bar")).toBeNull();
        expect(within(av as HTMLElement).getByText("not reached")).toBeInTheDocument();
    });

    it("prints a rate at the precision its counts can carry", () => {
        render(
            <CorpusStrip
                caption="Rates"
                figures={{
                    RV: { value: 218.44 },
                    SV: { value: 219.63 },
                    YV: { value: 9.5 },
                    AV: { value: null },
                }}
                perThousand
            />,
        );
        expect(screen.getByText("218.4")).toBeInTheDocument();
        expect(screen.getByText("9.50")).toBeInTheDocument();
    });
});

describe("ShareStrip", () => {
    it("names every collection it drew and every collection it did not", () => {
        render(
            <ShareStrip
                label="viśvā bhuvanā"
                shares={{ RV: 39, SV: 2, YV: 5, AV: 14 }}
                total={148}
            />,
        );
        expect(screen.getByText(/148 occurrences/)).toBeInTheDocument();
        expect(screen.getByText("39")).toBeInTheDocument();
    });

    it("says which collections a family is absent from rather than omitting them", () => {
        render(
            <ShareStrip
                label="a narrow family"
                shares={{ RV: 12, SV: 0, YV: null, AV: 0 }}
                total={12}
            />,
        );
        expect(screen.getByText(/not in\s+SV, YV, AV/)).toBeInTheDocument();
    });
});

describe("the wall label", () => {
    it("prints all five answers of the visualization standard", () => {
        render(<PlateLabel plate={PLATES_BY_SLUG.deities} />);
        for (const term of [
            "What is measured",
            "What one mark is",
            "What is in scope",
            "What is excluded",
            "What this does not show",
        ]) {
            expect(screen.getByText(term)).toBeInTheDocument();
        }
        expect(screen.getByText(PLATES_BY_SLUG.deities.label.notInfer)).toBeInTheDocument();
    });
});

describe("the takeaway", () => {
    it("marks an interpretation as an interpretation and not as a finding", () => {
        const { container } = render(
            <PlateTakeaway
                interpretation="One way to read it is that the layer follows what is easy to publish."
                observation="The Samaveda carries no translation."
            />,
        );
        const blocks = container.querySelectorAll("[data-knowledge-kind]");
        expect([...blocks].map((node) => node.getAttribute("data-knowledge-kind"))).toEqual([
            "derived-metric",
            "interpretation",
        ]);
        expect(screen.getByText("One way to read it")).toBeInTheDocument();
    });

    it("omits the interpretation block entirely when there is nothing to interpret", () => {
        const { container } = render(
            <PlateTakeaway observation="Twenty-five cells are measured." />,
        );
        expect(container.querySelectorAll('[data-knowledge-kind="interpretation"]')).toHaveLength(
            0,
        );
    });
});
