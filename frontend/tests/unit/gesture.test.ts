/**
 * The click-versus-drag classifier, on its own.
 *
 * This file exists because the defect it guards was reported from a product review rather than
 * found by a test: the homepage teaser navigated to the graph on every orbit, because a canvas
 * that acts on `click` acts on the end of every drag. There are end-to-end tests that drag the
 * real canvases and assert the URL, and they are the ones that prove the wiring - but they cost
 * a browser, a two-megabyte artifact and a settling layout each, so the *rule* is measured here
 * where a case costs nothing and the awkward ones can all be written down.
 *
 * `PointerEvent` is not implemented in jsdom, so each event is a `MouseEvent` with `pointerId`
 * and `pointerType` defined on it. That is enough: the classifier reads exactly those two, plus
 * `clientX`, `clientY` and `button`, and nothing about pointer capture - which is deliberate,
 * because capture is the browser's business and a classifier that depended on it could not be
 * measured outside one.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { GESTURE_SLOP, installGestures, type GesturePoint } from "@/lib/world/gesture";

type Init = {
    id?: number;
    x?: number;
    y?: number;
    kind?: string;
    button?: number;
};

function pointer(type: string, init: Init = {}) {
    const event = new MouseEvent(type, {
        bubbles: true,
        clientX: init.x ?? 0,
        clientY: init.y ?? 0,
        button: init.button ?? 0,
    });
    Object.defineProperty(event, "pointerId", { value: init.id ?? 1 });
    Object.defineProperty(event, "pointerType", { value: init.kind ?? "mouse" });
    return event;
}

let element: HTMLElement;

function handlers() {
    const onTap = vi.fn<(point: GesturePoint) => void>();
    const onHoverMove = vi.fn();
    const onHoverLeave = vi.fn();
    const onPhase = vi.fn();
    const onGrabCheck = vi.fn<(point: GesturePoint) => boolean>(() => false);
    const onGrabMove = vi.fn();
    const onGrabEnd = vi.fn();
    const record = { onTap, onHoverMove, onHoverLeave, onPhase, onGrabCheck, onGrabMove, onGrabEnd };
    const release = installGestures(element, record);
    return { ...record, release };
}

beforeEach(() => {
    element = document.createElement("div");
    document.body.append(element);
});

describe("a press and a release", () => {
    it("is a tap when the pointer did not travel", () => {
        const h = handlers();
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointerup", { x: 100, y: 100 }));
        expect(h.onTap).toHaveBeenCalledTimes(1);
        h.release();
    });

    it("is a tap when the pointer travelled less than the slop for its kind", () => {
        const h = handlers();
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointermove", { x: 102, y: 102 }));
        element.dispatchEvent(pointer("pointerup", { x: 102, y: 102 }));
        /* 2.83 px of travel, under the mouse slop of 4. A trackpad hand moves about this far
           during a deliberate click, which is the whole reason the threshold is not lower. */
        expect(h.onTap).toHaveBeenCalledTimes(1);
        h.release();
    });

    it("is not a tap once the pointer has travelled past the slop", () => {
        const h = handlers();
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointermove", { x: 140, y: 100 }));
        element.dispatchEvent(pointer("pointerup", { x: 140, y: 100 }));
        expect(h.onTap).not.toHaveBeenCalled();
        h.release();
    });

    it("reports the position in the element's own box", () => {
        /* jsdom lays nothing out, so the box is at the origin and the offset is the client
           position. The assertion that matters is that the point is *derived* from the box at
           all: an earlier version of the graph view passed client coordinates to a picker that
           expected canvas ones, and picked the wrong node by the height of the header. */
        const h = handlers();
        element.dispatchEvent(pointer("pointerdown", { x: 37, y: 91 }));
        element.dispatchEvent(pointer("pointerup", { x: 37, y: 91 }));
        expect(h.onTap.mock.calls[0][0]).toMatchObject({ x: 37, y: 91, pointerType: "mouse" });
        h.release();
    });

    it("measures the travel from the press and not between two moves", () => {
        /* The defect this replaces: the planar view compared each move against the previous one,
           so a slow pan - which arrives one pixel at a time - never latched, and the pan ended
           in a selection. Of nothing, because the release was over empty space. */
        const h = handlers();
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        for (let i = 1; i <= 40; i += 1) {
            element.dispatchEvent(pointer("pointermove", { x: 100 + i, y: 100 }));
        }
        element.dispatchEvent(pointer("pointerup", { x: 140, y: 100 }));
        expect(h.onTap).not.toHaveBeenCalled();
        h.release();
    });

    it("gives a finger a wider allowance than a mouse", () => {
        expect(GESTURE_SLOP.touch).toBeGreaterThan(GESTURE_SLOP.pen);
        expect(GESTURE_SLOP.pen).toBeGreaterThan(GESTURE_SLOP.mouse);
        const h = handlers();
        /* 7 px: past the mouse threshold, inside the touch one. The same journey has to be a
           drag from a mouse and a tap from a finger, which is why the slop is per kind and not
           a constant. */
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100, kind: "touch" }));
        element.dispatchEvent(pointer("pointermove", { x: 107, y: 100, kind: "touch" }));
        element.dispatchEvent(pointer("pointerup", { x: 107, y: 100, kind: "touch" }));
        expect(h.onTap).toHaveBeenCalledTimes(1);
        h.release();
    });

    it("is never a tap from a secondary button", () => {
        const h = handlers();
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100, button: 2 }));
        element.dispatchEvent(pointer("pointerup", { x: 100, y: 100, button: 2 }));
        expect(h.onTap).not.toHaveBeenCalled();
        h.release();
    });
});

describe("the gestures that are not a release", () => {
    it("produces nothing at all from a cancelled pointer", () => {
        /* Not a tap, and above all not a tap over empty space that clears the reader's
           selection. The browser cancels the pointer every time a finger that landed on a
           scrollable canvas is used to scroll the page past it. */
        const h = handlers();
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100, kind: "touch" }));
        element.dispatchEvent(pointer("pointercancel", { x: 100, y: 100, kind: "touch" }));
        element.dispatchEvent(pointer("pointerup", { x: 100, y: 100, kind: "touch" }));
        expect(h.onTap).not.toHaveBeenCalled();
        h.release();
    });

    it("produces nothing when pointer capture is taken away", () => {
        const h = handlers();
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("lostpointercapture", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointerup", { x: 100, y: 100 }));
        expect(h.onTap).not.toHaveBeenCalled();
        h.release();
    });

    it("keeps the record of a drag that left the element", () => {
        /* `pointerleave` ends hover and nothing else. Clearing the gesture there is how the
           spatial view's threshold came to be defeated on touch specifically: on a device with
           no hover the compatibility events arrive after the leave, so the guard the leave
           handler cleared was already clear by the time the release read it. */
        const h = handlers();
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointermove", { x: 400, y: 400 }));
        element.dispatchEvent(pointer("pointerleave", { x: 400, y: 400 }));
        element.dispatchEvent(pointer("pointerup", { x: 100, y: 100 }));
        expect(h.onHoverLeave).toHaveBeenCalledTimes(1);
        expect(h.onTap).not.toHaveBeenCalled();
        h.release();
    });

    it("does not end a pinch in a tap", () => {
        /* The second finger to lift has itself pressed and released without travelling, and by
           then the first finger's travel has been forgotten. Without a latch that survives
           until every pointer is up, a pinch ends in a selection. */
        const h = handlers();
        element.dispatchEvent(pointer("pointerdown", { id: 1, x: 100, y: 100, kind: "touch" }));
        element.dispatchEvent(pointer("pointerdown", { id: 2, x: 200, y: 200, kind: "touch" }));
        element.dispatchEvent(pointer("pointermove", { id: 1, x: 60, y: 60, kind: "touch" }));
        element.dispatchEvent(pointer("pointerup", { id: 1, x: 60, y: 60, kind: "touch" }));
        element.dispatchEvent(pointer("pointerup", { id: 2, x: 200, y: 200, kind: "touch" }));
        expect(h.onTap).not.toHaveBeenCalled();
        h.release();
    });

    it("reports hover only while no pointer is down", () => {
        const h = handlers();
        element.dispatchEvent(pointer("pointermove", { x: 10, y: 10 }));
        element.dispatchEvent(pointer("pointerdown", { x: 10, y: 10 }));
        element.dispatchEvent(pointer("pointermove", { x: 90, y: 90 }));
        element.dispatchEvent(pointer("pointerup", { x: 90, y: 90 }));
        expect(h.onHoverMove).toHaveBeenCalledTimes(1);
        h.release();
    });
});

describe("the phase, which a test can read off the element", () => {
    it("is published so that an absent navigation can be told from an absent event", () => {
        /* A test that asserts only that no navigation happened passes just as well when the
           canvas has stopped receiving events at all. */
        const h = handlers();
        expect(element.dataset.gesture).toBe("idle");
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        expect(element.dataset.gesture).toBe("pressed");
        element.dispatchEvent(pointer("pointermove", { x: 140, y: 100 }));
        expect(element.dataset.gesture).toBe("dragging");
        element.dispatchEvent(pointer("pointerup", { x: 140, y: 100 }));
        expect(element.dataset.gesture).toBe("idle");
        expect(h.onPhase.mock.calls.map((call) => call[0])).toEqual([
            "pressed",
            "dragging",
            "idle",
        ]);
        h.release();
    });

    it("is removed with the listeners", () => {
        const h = handlers();
        h.release();
        expect(element.dataset.gesture).toBeUndefined();
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointerup", { x: 100, y: 100 }));
        expect(h.onTap).not.toHaveBeenCalled();
    });
});

describe("taking hold of something", () => {
    it("asks once, on the press, and not again during the gesture", () => {
        /* Once, because the answer decides what the travel means and the camera has already
           moved by the time a drag is recognisable. Asking again mid-drag would let the answer
           change under the reader's finger. */
        const h = handlers();
        h.onGrabCheck.mockReturnValue(true);
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointermove", { x: 140, y: 100 }));
        element.dispatchEvent(pointer("pointermove", { x: 180, y: 100 }));
        element.dispatchEvent(pointer("pointerup", { x: 180, y: 100 }));
        expect(h.onGrabCheck).toHaveBeenCalledTimes(1);
        expect(h.onGrabCheck.mock.calls[0][0]).toMatchObject({ x: 100, y: 100 });
        h.release();
    });

    it("delivers the moves that follow the latch, and none before it", () => {
        const h = handlers();
        h.onGrabCheck.mockReturnValue(true);
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointermove", { x: 102, y: 100 }));
        expect(h.onGrabMove).not.toHaveBeenCalled();
        element.dispatchEvent(pointer("pointermove", { x: 140, y: 100 }));
        element.dispatchEvent(pointer("pointermove", { x: 180, y: 120 }));
        element.dispatchEvent(pointer("pointerup", { x: 180, y: 120 }));
        expect(h.onGrabMove.mock.calls.map((call) => call[0].x)).toEqual([140, 180]);
        h.release();
    });

    it("leaves a press that answered false to the camera", () => {
        const h = handlers();
        h.onGrabCheck.mockReturnValue(false);
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointermove", { x: 140, y: 100 }));
        element.dispatchEvent(pointer("pointerup", { x: 140, y: 100 }));
        expect(h.onGrabMove).not.toHaveBeenCalled();
        expect(h.onGrabEnd).not.toHaveBeenCalled();
        h.release();
    });

    it("is still a tap when the press never travelled", () => {
        /* Pressing an object and letting go of it selects it. A hold that consumed the gesture
           would mean the orbs a reader can move are the orbs they cannot open. */
        const h = handlers();
        h.onGrabCheck.mockReturnValue(true);
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointerup", { x: 100, y: 100 }));
        expect(h.onTap).toHaveBeenCalledTimes(1);
        expect(h.onGrabMove).not.toHaveBeenCalled();
        h.release();
    });

    it("lets go on the release even when it never moved", () => {
        /* `onGrabCheck` is where the consumer turns its camera off, so an end that only fired
           after a real drag would leave a view that could no longer be orbited. */
        const h = handlers();
        h.onGrabCheck.mockReturnValue(true);
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointerup", { x: 100, y: 100 }));
        expect(h.onGrabEnd).toHaveBeenCalledTimes(1);
        h.release();
    });

    it("lets go on a cancel", () => {
        const h = handlers();
        h.onGrabCheck.mockReturnValue(true);
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100, kind: "touch" }));
        element.dispatchEvent(pointer("pointermove", { x: 140, y: 100, kind: "touch" }));
        element.dispatchEvent(pointer("pointercancel", { x: 140, y: 100, kind: "touch" }));
        expect(h.onGrabEnd).toHaveBeenCalledTimes(1);
        expect(h.onTap).not.toHaveBeenCalled();
        h.release();
    });

    it("lets go when a second finger arrives", () => {
        /* A second finger means the reader has stopped addressing the object and started
           addressing the view, and the view cannot be addressed while its camera is off. */
        const h = handlers();
        h.onGrabCheck.mockReturnValue(true);
        element.dispatchEvent(pointer("pointerdown", { id: 1, x: 100, y: 100, kind: "touch" }));
        element.dispatchEvent(pointer("pointermove", { id: 1, x: 140, y: 100, kind: "touch" }));
        element.dispatchEvent(pointer("pointerdown", { id: 2, x: 300, y: 300, kind: "touch" }));
        expect(h.onGrabEnd).toHaveBeenCalledTimes(1);
        element.dispatchEvent(pointer("pointermove", { id: 1, x: 200, y: 100, kind: "touch" }));
        expect(h.onGrabMove).toHaveBeenCalledTimes(1);
        h.release();
    });

    it("lets go exactly once, however the gesture ended", () => {
        const h = handlers();
        h.onGrabCheck.mockReturnValue(true);
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100 }));
        element.dispatchEvent(pointer("pointermove", { x: 140, y: 100 }));
        element.dispatchEvent(pointer("pointerup", { x: 140, y: 100 }));
        element.dispatchEvent(pointer("lostpointercapture", { x: 140, y: 100 }));
        expect(h.onGrabEnd).toHaveBeenCalledTimes(1);
        h.release();
    });

    it("never takes hold from a secondary button", () => {
        const h = handlers();
        h.onGrabCheck.mockReturnValue(true);
        element.dispatchEvent(pointer("pointerdown", { x: 100, y: 100, button: 2 }));
        element.dispatchEvent(pointer("pointermove", { x: 140, y: 100, button: 2 }));
        element.dispatchEvent(pointer("pointerup", { x: 140, y: 100, button: 2 }));
        expect(h.onGrabCheck).not.toHaveBeenCalled();
        expect(h.onGrabMove).not.toHaveBeenCalled();
        h.release();
    });
});
