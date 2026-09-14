"use client";

import { useEffect, useRef, useState } from "react";
import type { World } from "@/lib/world/artifact";
import type { WorldEngine } from "@/lib/world/engine";

/**
 * Names on the map.
 *
 * ## Why these are DOM nodes and not sprites
 *
 * The rule everyone quotes is that you must never render one HTML element per graph node, and
 * it is correct: 35,370 absolutely-positioned spans would be unusable. But that rule is about
 * *count*, not about technique, and the count here is at most a few dozen. At that size the
 * DOM is the better tool - it gets the project's actual typefaces, its diacritics, its
 * theme-aware colours and its text selection for nothing, where an SDF or canvas-texture
 * atlas would have to reproduce all four and would still render Charis SIL's combining marks
 * worse than the browser does.
 *
 * ## Which names
 *
 * Never everything. The artifact ships a hub index: the six hundred most connected subjects
 * that are not passages or reified records, most connected first. From that the visible set
 * is chosen per frame by three rules - it must be on screen, it must not collide with a label
 * already placed, and there is a hard ceiling. Degree order means the ceiling cuts the least
 * important names rather than an arbitrary ones.
 */

export type LabelPlacement = {
    index: number;
    text: string;
    x: number;
    y: number;
    strong: boolean;
};

/** The most names the world tier will ever show at once. */
const WORLD_LABEL_LIMIT = 22;
/** Rectangles this far apart, in pixels, are treated as colliding. */
const COLLIDE_X = 132;
const COLLIDE_Y = 20;

export function WorldLabels({
    engine,
    world,
    labels,
    selected,
    neighbours,
}: {
    engine: WorldEngine | null;
    world: World | null;
    labels: string[] | null;
    selected: number | null;
    neighbours: number[];
}) {
    const [placements, setPlacements] = useState<LabelPlacement[]>([]);
    const frame = useRef(0);

    useEffect(() => {
        if (!engine || !world || !labels) return;
        let stopped = false;

        /*
         * Placement runs on a timer rather than inside the render loop.
         *
         * Labels are React state, and putting a setState on every frame would put React's
         * reconciler back into the frame budget - the single thing the engine is built to
         * keep it out of. Names do not need to move at sixty hertz to look attached; they
         * need to be in the right place once the camera has stopped somewhere.
         */
        const place = () => {
            if (stopped) return;
            const shown: LabelPlacement[] = [];
            const taken: Array<[number, number]> = [];

            const consider = (index: number, strong: boolean) => {
                if (shown.length >= (selected === null ? WORLD_LABEL_LIMIT : 40)) return;
                const at = engine.screenPositionOf(index);
                if (!at) return;
                for (const [x, y] of taken) {
                    if (Math.abs(x - at.x) < COLLIDE_X && Math.abs(y - at.y) < COLLIDE_Y) return;
                }
                const text = labels[index];
                if (!text) return;
                taken.push([at.x, at.y]);
                shown.push({ index, text, x: at.x, y: at.y, strong });
            };

            // The chosen subject and its neighbours come first and always win a place.
            if (selected !== null) {
                consider(selected, true);
                for (const neighbour of neighbours.slice(0, 60)) consider(neighbour, false);
            }
            for (const hub of world.manifest.hubs) consider(hub, false);

            setPlacements(shown);
            frame.current = window.setTimeout(place, 160);
        };

        place();
        return () => {
            stopped = true;
            window.clearTimeout(frame.current);
        };
    }, [engine, world, labels, selected, neighbours]);

    if (!placements.length) return null;

    return (
        <div aria-hidden="true" className="va-world-labels">
            {placements.map((placement) => (
                <span
                    className={placement.strong ? "va-world-label is-strong" : "va-world-label"}
                    key={placement.index}
                    style={{ transform: `translate3d(${placement.x}px, ${placement.y}px, 0)` }}
                >
                    {placement.text}
                </span>
            ))}
        </div>
    );
}
