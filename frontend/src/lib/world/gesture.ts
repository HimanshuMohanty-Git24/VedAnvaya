/**
 * Was that a click, or the end of a drag?
 *
 * ## Why this is a module and not three copies
 *
 * Every canvas in this product is orbited by dragging it, and a mouse drag always ends by
 * dispatching `click`: OrbitControls captures the pointer but never calls `preventDefault` on
 * the press, and preventing the press would not suppress the click in any case. So a canvas
 * that acts on `click` acts on every orbit. The answer is to classify the gesture, and the
 * classification had been written three times:
 *
 *   - the homepage teaser      no threshold at all - it navigated on every orbit
 *   - the spatial graph view   3 px, per axis, from the press, cleared on `pointerleave`
 *   - the planar graph view    1 px, per axis, *between two moves*
 *
 * Each was wrong differently. The teaser released over empty space and pushed the reader to
 * the graph page. The planar test never latches during a slow pan, because a slow pan delivers
 * one pixel at a time, so the pan ended in a selection - and a selection of nothing, which is
 * how a reader looking at one subject was returned to the whole corpus. The spatial threshold
 * is below the platform floor for a finger, so an ordinary tap read as a drag and selected
 * nothing.
 *
 * That is not three bugs. It is one decision taken in three places, and it belongs in one.
 * The engine cannot own it outright, because the planar renderer is a 2D canvas with no
 * engine, so it is a module both of them install and the numbers below have exactly one home.
 *
 * ## Why `pointerup` and not `click`
 *
 * `click` cannot carry this. On a device without hover the compatibility mouse events arrive
 * *after* `pointerleave`, so a guard that a leave handler clears is already cleared by the time
 * the click reads it - which is how the spatial threshold came to be defeated on touch
 * specifically. `click` also carries no `pointerId`, so it cannot be attributed to one finger
 * of a pinch, and its target is the press/release common ancestor rather than the element
 * pressed. None of the three is fixable while `click` is the event.
 */

export type GesturePhase = "idle" | "pressed" | "dragging" | "multi";

export type PointerKind = "mouse" | "pen" | "touch";

/**
 * How far a pointer may travel and still have been held still.
 *
 * Taken from the platforms rather than chosen. 4 px is the Win32 `SM_CXDRAG` default and a
 * little more forgiving than Blink's own 3 px, which matters because a hand on a trackpad moves
 * two or three pixels during a deliberate click. 10 px clears both the 8 dp Android
 * `ViewConfiguration` touch slop - the boundary Chrome for Android uses to tell a tap from a
 * scroll - and the ten-odd points at which `UIPanGestureRecognizer` begins. A stylus sits
 * between a finger and a mouse in steadiness, so it gets a value between theirs.
 *
 * Measured from the press, never between two moves, and as a distance rather than per axis:
 * three pixels on each axis is four and a quarter pixels of travel, and a test that reads that
 * as stillness is the reason the planar view could be panned into a selection.
 *
 * There is deliberately no time ceiling. Android's tap timeout and iOS's minimum press
 * duration exist to tell a tap from a long press, and there is no long press here to tell it
 * from. A ceiling would only create a state in which a slow, careful, motionless press does
 * nothing, which penalises an unsteady hand for no gain: no movement is unambiguous intent
 * however long it took.
 */
export const GESTURE_SLOP: Record<PointerKind, number> = {
    mouse: 4,
    pen: 6,
    touch: 10,
};

export type GesturePoint = {
    /** Relative to the element's own box, which is what every picker here wants. */
    x: number;
    y: number;
    pointerType: PointerKind;
};

export type GestureHandlers = {
    /**
     * The pointer was pressed and released without travelling. The only event from which a
     * selection or a navigation may follow.
     */
    onTap?: (point: GesturePoint) => void;
    /** The pointer moved with no gesture in progress. Hover, and nothing else. */
    onHoverMove?: (point: GesturePoint) => void;
    /** The pointer left the element. Hover ends; a gesture in progress is not affected. */
    onHoverLeave?: () => void;
    /** Reported so a view can suppress hover work, and so a test can assert the phase. */
    onPhase?: (phase: GesturePhase) => void;
};

function kindOf(pointerType: string): PointerKind {
    return pointerType === "touch" || pointerType === "pen" ? pointerType : "mouse";
}

/**
 * Watch an element and report gestures. Returns the teardown.
 *
 * The phase is also written to `data-gesture` on the element. A test that asserts only the
 * absence of a navigation passes just as well when the canvas has stopped receiving events at
 * all, so the classification is made observable rather than inferred from an absence.
 */
export function installGestures(element: HTMLElement, handlers: GestureHandlers): () => void {
    /** Every pointer currently down on this element. */
    const active = new Set<number>();
    let primary: number | null = null;
    let startX = 0;
    let startY = 0;
    let kind: PointerKind = "mouse";
    /**
     * Set once this gesture can no longer be a tap, and not cleared until every pointer is up.
     *
     * The latch is the whole of the pinch argument. Without it the *second* finger to lift from
     * a two-finger gesture looks like a press and release that never moved, because by then the
     * first finger's travel has been forgotten - so a pinch would end in a tap.
     */
    let latched = false;
    let phase: GesturePhase = "idle";

    const setPhase = (next: GesturePhase) => {
        if (next === phase) return;
        phase = next;
        element.dataset.gesture = next;
        handlers.onPhase?.(next);
    };

    const pointOf = (event: PointerEvent): GesturePoint => {
        const box = element.getBoundingClientRect();
        return {
            x: event.clientX - box.left,
            y: event.clientY - box.top,
            pointerType: kindOf(event.pointerType),
        };
    };

    const endGesture = () => {
        if (active.size > 0) return;
        primary = null;
        latched = false;
        setPhase("idle");
    };

    const onPointerDown = (event: PointerEvent) => {
        active.add(event.pointerId);
        if (active.size > 1) {
            // A second pointer means a pinch or a two-finger pan. Nothing after it is a tap.
            latched = true;
            setPhase("multi");
            return;
        }
        primary = event.pointerId;
        startX = event.clientX;
        startY = event.clientY;
        kind = kindOf(event.pointerType);
        /* A secondary button is a dolly or a pan in every orbit control ever written, and in
           none of them is it a selection. */
        latched = event.button !== 0;
        setPhase("pressed");
    };

    const onPointerMove = (event: PointerEvent) => {
        if (active.size === 0) {
            handlers.onHoverMove?.(pointOf(event));
            return;
        }
        if (event.pointerId !== primary || latched) return;
        if (Math.hypot(event.clientX - startX, event.clientY - startY) > GESTURE_SLOP[kind]) {
            latched = true;
            setPhase("dragging");
        }
    };

    const onPointerUp = (event: PointerEvent) => {
        const wasPrimary = event.pointerId === primary;
        active.delete(event.pointerId);
        if (wasPrimary && !latched) handlers.onTap?.(pointOf(event));
        endGesture();
    };

    /*
     * A cancelled gesture produces nothing at all.
     *
     * Not a tap, not a selection, and above all not a selection of nothing. This is not a
     * corner case: once an element lets the page scroll under a finger, the browser cancels the
     * pointer every single time a reader scrolls past with a finger that happened to land
     * there. The planar view routed exactly this event into its release handler, where it could
     * reach a cleared selection.
     *
     * `lostpointercapture` is treated the same way. It fires when capture is taken away - a
     * browser gesture winning, or the element being removed - and in neither case did the
     * reader complete anything.
     */
    const onPointerCancel = (event: PointerEvent) => {
        latched = true;
        active.delete(event.pointerId);
        endGesture();
    };

    /*
     * Leaving ends hover and nothing else.
     *
     * The gesture record is deliberately untouched. OrbitControls captures the pointer on
     * press, so the browser retargets it here for the whole gesture and travel outside the box
     * is an ordinary orbit that latches on its own. Clearing the record here is what let a
     * touch-drag through the spatial view's threshold, because on touch the leave arrives
     * before the click.
     */
    const onPointerLeave = () => handlers.onHoverLeave?.();

    element.addEventListener("pointerdown", onPointerDown);
    element.addEventListener("pointermove", onPointerMove);
    element.addEventListener("pointerup", onPointerUp);
    element.addEventListener("pointercancel", onPointerCancel);
    element.addEventListener("lostpointercapture", onPointerCancel);
    element.addEventListener("pointerleave", onPointerLeave);
    element.dataset.gesture = "idle";

    return () => {
        element.removeEventListener("pointerdown", onPointerDown);
        element.removeEventListener("pointermove", onPointerMove);
        element.removeEventListener("pointerup", onPointerUp);
        element.removeEventListener("pointercancel", onPointerCancel);
        element.removeEventListener("lostpointercapture", onPointerCancel);
        element.removeEventListener("pointerleave", onPointerLeave);
        delete element.dataset.gesture;
    };
}
