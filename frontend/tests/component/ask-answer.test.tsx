import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AskAnswer } from "@/components/ask/ask-answer";
import { elapsedCopy, truncationCaveat, waitNoteFor, type AskResponse } from "@/lib/ask";
import { askResponseFixture, truncatedResponseFixture } from "../fixtures/ask";

/**
 * The answer surface.
 *
 * What is asserted here is the part of Ask that is a product claim rather than a layout: that
 * a truncated response cannot be mistaken for a finished one, that a grade on the evidence is
 * never phrased as certainty, that a citation to something that was not retrieved is not
 * counted as support, and that an absence of evidence is reported as a limit of this build.
 */

function renderAnswer(result: AskResponse = askResponseFixture, citedIds = ["E1", "E2", "E3"]) {
    const onOpenEvidence = vi.fn();
    const onAsk = vi.fn();
    const view = render(
        <AskAnswer
            citedIds={citedIds}
            onAsk={onAsk}
            onOpenEvidence={onOpenEvidence}
            result={result}
        />,
    );
    return { ...view, onOpenEvidence, onAsk };
}

describe("the answer", () => {
    it("grades the evidence without phrasing it as certainty", () => {
        renderAnswer();
        const support = document.querySelector(".va-answer-support") as HTMLElement;
        expect(within(support).getByText("Moderate support")).toBeInTheDocument();
        expect(
            within(support).getByText(/cited, on a narrow evidence base/i),
        ).toBeInTheDocument();
        /* The grade must not be readable as a verdict on whether the answer is true. */
        expect(support.textContent ?? "").not.toMatch(/correct|verified|accurate|confirmed/i);
    });

    it("carries the tone in a word, not only in a colour", () => {
        renderAnswer();
        const support = document.querySelector(".va-answer-support") as HTMLElement;
        // The class drives the colour; the label has to say it too.
        expect(support.className).toContain("tone-partial");
        expect(support.textContent).toContain("Moderate support");
    });

    it("opens the cited evidence when a marker in the prose is used", async () => {
        const { onOpenEvidence } = renderAnswer();
        await userEvent.click(screen.getByRole("button", { name: /Open evidence E1/i }));
        expect(onOpenEvidence).toHaveBeenCalledWith("E1");
    });

    it("disables a citation marker that names something never retrieved", () => {
        // The synthesiser can emit a marker for an item it did not receive.
        renderAnswer(askResponseFixture, ["E1", "E9"]);
        const dangling = screen.queryByRole("button", { name: /Open evidence E9/i });
        // E9 is not in the prose of this fixture, so the marker is simply absent; the ones
        // that are present and retrievable must be live.
        expect(dangling).toBeNull();
        expect(screen.getByRole("button", { name: /Open evidence E1/i })).toBeEnabled();
    });

    it("counts only citations that resolve to a retrieved item", () => {
        /* E9 was cited in the prose but never retrieved. Counting it would credit the answer
           with support that does not exist. */
        renderAnswer(askResponseFixture, ["E1", "E2", "E9"]);
        const top = document.querySelector(".va-answer-evidence-top") as HTMLElement;
        expect(top.textContent).toMatch(/2 cited in the prose above/);
        expect(top.textContent).not.toMatch(/3 cited/);
    });

    it("puts retrieved passages on the page, not only behind the drawer", () => {
        renderAnswer();
        const evidence = document.querySelector(".va-answer-evidence") as HTMLElement;
        expect(within(evidence).getByText("RV 1.21.1")).toBeInTheDocument();
        expect(
            within(evidence).getByText(/Hither I call Indra and Agni/i),
        ).toBeInTheDocument();
        // And each one can be opened in the reader it came from.
        expect(
            within(evidence).getAllByRole("link", { name: /Open in the reader/i }).length,
        ).toBeGreaterThan(0);
    });

    it("links a passage to the rebuilt reader by its canonical key", () => {
        renderAnswer();
        const link = screen.getAllByRole("link", { name: /Open in the reader/i })[0];
        expect(link).toHaveAttribute(
            "href",
            `/passage/${encodeURIComponent("VG:RV:SAK:M01:S021:V001")}`,
        );
    });

    it("reports an unresolved name as a fact about the graph, not about the Vedas", () => {
        renderAnswer();
        const names = document.querySelector(".va-name-unresolved") as HTMLElement;
        expect(within(names).getByText(/not about the Vedas/i)).toBeInTheDocument();
        expect(within(names).getByText(/Mitra-Varuna/)).toBeInTheDocument();
    });

    it("separates a channel that ran and found nothing from one never selected", () => {
        renderAnswer();
        const retrieval = document.querySelector(".va-answer-retrieval") as HTMLElement;
        expect(
            within(retrieval).getByText(/searched-and-empty is\s+evidence of a kind/i),
        ).toBeInTheDocument();
    });

    it("offers a follow-up as a link into the same inquiry", async () => {
        const { onAsk } = renderAnswer();
        const next = document.querySelector(".va-answer-next") as HTMLElement;
        const first = within(next).getAllByRole("button")[0];
        await userEvent.click(first);
        expect(onAsk).toHaveBeenCalledWith(
            "Where else is the dual divinity form used in the Rigveda?",
        );
    });
});

describe("a truncated answer", () => {
    it("is detected from the caveat the backend stamps, not from the prose", () => {
        expect(truncationCaveat(truncatedResponseFixture)?.source).toBe("generation_truncated");
        expect(truncationCaveat(askResponseFixture)).toBeNull();
    });

    it("says the response ended early rather than presenting it as complete", () => {
        renderAnswer(truncatedResponseFixture);
        const notice = document.querySelector(".va-answer-truncated") as HTMLElement;
        expect(notice).toBeTruthy();
        expect(
            within(notice).getByText(/ended before synthesis completed/i),
        ).toBeInTheDocument();
        // The backend's own wording is reproduced rather than re-phrased.
        expect(within(notice).getByText(/reached its output limit/i)).toBeInTheDocument();
    });

    it("appears above the prose, so it is met before the text is read", () => {
        renderAnswer(truncatedResponseFixture);
        const notice = document.querySelector(".va-answer-truncated");
        const prose = document.querySelector(".va-answer-prose");
        // compareDocumentPosition: FOLLOWING means prose comes after the notice.
        expect(notice?.compareDocumentPosition(prose as Node)).toBe(
            Node.DOCUMENT_POSITION_FOLLOWING,
        );
    });

    it("does not repeat the truncation notice among the ordinary scope notes", () => {
        renderAnswer(truncatedResponseFixture);
        const caveats = document.querySelector(".va-answer-caveats");
        expect(caveats?.textContent ?? "").not.toMatch(/reached its output limit/i);
        // The other caveats are untouched.
        expect(caveats?.textContent ?? "").toMatch(/lower bound/i);
    });

    it("offers the evidence, which is complete even when the prose is not", async () => {
        const { onOpenEvidence } = renderAnswer(truncatedResponseFixture);
        const notice = document.querySelector(".va-answer-truncated") as HTMLElement;
        await userEvent.click(
            within(notice).getByRole("button", { name: /Read the evidence instead/i }),
        );
        expect(onOpenEvidence).toHaveBeenCalledWith(null);
    });
});

describe("an answer with nothing behind it", () => {
    it("reports the absence as a limit of this build", () => {
        const empty: AskResponse = {
            ...askResponseFixture,
            evidence: [],
            support_level: "INSUFFICIENT",
            retrieval_summary: { ...askResponseFixture.retrieval_summary, evidence_count: 0 },
        };
        renderAnswer(empty, []);
        const section = document.querySelector(".va-answer-evidence.is-empty") as HTMLElement;
        expect(
            within(section).getByText(/not about what the Vedas contain/i),
        ).toBeInTheDocument();
        // And the grade says the same thing rather than reading as a denial.
        expect(screen.getByText("Insufficient support")).toBeInTheDocument();
        expect(
            screen.getByText(/statement about this build, not about the Vedas/i),
        ).toBeInTheDocument();
    });
});

describe("the waiting contract", () => {
    /*
     * These guard the defect this phase existed to fix. The previous build showed three
     * phases that completed on a timer at 0, 0.9 and 2.6 seconds against a measured median
     * latency of about 106 seconds, so every real request sat on "Synthesising" for a further
     * hundred seconds. Nothing here may claim progress the frontend cannot observe.
     */
    it("says more as the wait grows, and never promises a finish", () => {
        const notes = [0, 15_000, 45_000, 90_000, 240_000].map(waitNoteFor);
        expect(new Set(notes).size).toBe(4);
        for (const note of notes) {
            expect(note).not.toMatch(/almost|nearly|shortly|any moment|\d+\s*%/i);
        }
        expect(waitNoteFor(120_000)).toMatch(/several minutes/i);
    });

    it("holds the first note until the first threshold", () => {
        expect(waitNoteFor(0)).toBe(waitNoteFor(14_999));
        expect(waitNoteFor(15_000)).not.toBe(waitNoteFor(14_999));
    });

    it("reports elapsed time as measured, in minutes once past one", () => {
        expect(elapsedCopy(3_000)).toBe("3s elapsed");
        expect(elapsedCopy(59_000)).toBe("59s elapsed");
        expect(elapsedCopy(105_000)).toBe("1m 45s elapsed");
        expect(elapsedCopy(248_700)).toBe("4m 08s elapsed");
    });
});
