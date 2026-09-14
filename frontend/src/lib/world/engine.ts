import {
    BufferAttribute,
    BufferGeometry,
    Color,
    LineBasicMaterial,
    LineSegments,
    PerspectiveCamera,
    Points,
    Scene,
    ShaderMaterial,
    Vector2,
    Vector3,
    WebGLRenderer,
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { edgesOf, otherEnd, type World } from "./artifact";
import { LABEL_FRACTIONS, LABEL_STRIDE } from "./edge-labels";
import {
    SLAB_AZIMUTH_DEFAULT,
    SLAB_ELEVATION,
    layoutFocusSlab,
    slabRadiusFor,
    slabSpreadGain,
    type FocusSlab,
    type SlabMember,
    type SlabSpread,
} from "./focus-layout";
import { installGestures } from "./gesture";
import {
    createField,
    fieldAtRest,
    stepField,
    tuningFor,
    type Field,
} from "./local-physics";
import {
    STAGE_A_MS,
    itemWeight,
    transitionWeights,
    type TransitionDirection,
    type TransitionWeights,
} from "./transition";

/**
 * The world engine.
 *
 * Deliberately not a React component and deliberately not a force-graph wrapper.
 *
 * The wrappers were measured out of contention rather than dismissed: `three-forcegraph`,
 * which is what `react-force-graph-3d` runs on, creates one `THREE.Mesh` per node and adds
 * each to the scene - its published source contains no `InstancedMesh` and no `BatchedMesh` -
 * so a graph this size is 35,370 draw calls. Its own issue tracker records 117,927 nodes
 * exhausting WebGL memory "after the first few seconds", and that is almost exactly the size
 * of this corpus. It also welds layout to rendering in a single rAF, which forecloses moving
 * the simulation off the main thread.
 *
 * React is not in the frame loop either. The scene holds four objects, so a reconciler would
 * cost nothing, but it would also buy nothing, and `@react-three/fiber` pins `react >=19
 * <19.3` against the 19.2.8 this project runs. React owns selection, mode and filters; this
 * class owns transforms, buffers and ticks. Nothing crosses that line per frame.
 *
 * ## What is drawn
 *
 * Two objects carry the whole graph. Nodes are a single `Points` with a custom shader, which
 * is the cheapest node primitive there is - one vertex each, no index buffer - and comfortably
 * holds hundreds of thousands. Edges are a single `LineSegments` over one `BufferGeometry`,
 * which is one draw call for all 185,693 of them. Line width is ignored by nearly every
 * driver, so weight is carried in per-vertex alpha instead, which reads correctly at this
 * scale and stays inside the single-draw-call regime.
 */

export type WorldMode = "WORLD" | "FOCUS" | "PATH";

const DEG = Math.PI / 180;

/**
 * How many edges the world tier draws before anything is selected.
 *
 * Chosen from the sweep in `scripts/bench-world.mjs --sweep`, which varies this number and
 * measures the resulting frame interval on the machine it runs on. The value here is the one
 * that held a frame inside the refresh budget on the development machine's integrated GPU
 * with headroom left for a camera move, which is when the scene is at its most expensive.
 */
const WORLD_EDGE_BUDGET = 24_000;

/**
 * How far the whole world is framed from.
 *
 * ## Why it moved, and why not as far as the composition wanted
 *
 * At 2600 the world filled 42% of the frame height with the camera 2,065 units outside a
 * 535-unit cloud - measured, not estimated - and the result reads as looking at a marble on a
 * table. The manifest's 1000-unit extent is set by the 1,311 *unattached* nodes on their shell
 * rather than by the structure, whose attached radius is 237 at the median and 535 at the 99th
 * percentile, so the frame was being sized by the part of the artifact that carries the least.
 *
 * The composition pass concluded 1200, where the world fills 91%. That was measured for legibility
 * and not for cost, and the cost is the whole argument: this scene is fill-rate bound, coverage
 * goes as 1/d squared, so halving the distance quadruples the pixels 35,370 orbs and the backbone
 * cover. Swept on the development GPU at 1440x900, with the edge budget already scaling:
 *
 *     d=1200  fill 91%  draw 15.4 ms      d=2100  fill 52%  draw  6.4 ms
 *     d=1500  fill 73%  draw 10.5 ms      d=2400  fill 46%  draw  6.3 ms
 *     d=1800  fill 61%  draw  7.5 ms      d=2600  fill 42%  draw  5.2 ms
 *
 * 1200 is a three-fold draw-cost increase on the *default* view to make the marble bigger, and
 * the brief for this phase says in terms not to overspend on World while Focus is unreadable.
 * 1800 takes the world from 42% of the frame to 61% - a median constellation silhouette from 92
 * px to about 61, with 33 px gutters, still a region rather than texture - for 1.44 times the
 * draw. That is the trade, and the sweep is here so that anyone who wants a different point on
 * it can take one without re-deriving the curve.
 */
const WORLD_DISTANCE = 1800;

/**
 * The camera distance the world edge budget was measured at.
 *
 * 2600, which is where the world used to be framed from, because that is the distance at which
 * 24,000 was the number that held a frame. Anchoring it at the *new* 1200 framing instead was a
 * real defect and a measured one: it left the full budget in force with the world twice as close,
 * and the world draw went from 3.1 ms to 39.3 ms - the backbone alone 29.9 of it. The budget is a
 * pixel budget, so its anchor has to be the distance the pixels were counted at.
 *
 * The budget is scaled by the square of the distance below this, and the reason is a measurement
 * rather than a theory. This scene is fill-rate bound - screen coverage is the variable, not edge
 * count - and a hairline's coverage goes as 1/d, so a fixed set of lines seen from half as far
 * costs four times as much. Measured on Indra at degree 7,347 the draw was 5.9 ms; Sarasvati at
 * degree 298 drew at **8.2 ms with 7,049 fewer lines**, purely because `focusNode` frames a
 * smaller neighbourhood closer and every line then spans more of the viewport. Pinning the camera
 * at 700 units widened the backbone's share from 4.7 ms to 23.9 ms.
 *
 * This decides how many pixels a constant set of lines is allowed to cover. It decides nothing
 * about what the reader is exploring - World against Focus is a semantic question answered by the
 * state model and never by a camera position - which is the line the state model draws and this
 * stays on the level-of-detail side of it.
 */
const EDGE_BUDGET_DISTANCE = 2600;

/** What stays drawn behind a traced route: enough for context, not enough to obscure it. */
const PATH_EDGE_BUDGET = 1_200;

/**
 * The world backbone draws nothing behind a curated Focus. Nothing at all.
 *
 * This is the one place where the engine's long-standing "selection is emphasis, never isolation"
 * rule is deliberately set aside, so it is worth saying why rather than leaving it to be
 * rediscovered. That rule earns its keep while the neighbourhood is drawn *at its world
 * coordinates*: the backbone is then the answer to "where does this sit", and deleting it would
 * leave the subject floating in nothing.
 *
 * A curated Focus is not that. Its orbs have been lifted out of their world positions onto a slab
 * anchored at the subject, so the backbone behind them joins nodes that are no longer where the
 * lines say they are - it would be a wash of hairlines asserting a geometry that has been
 * replaced. The same reasoning already retired the backbone for a traced route, which held four
 * frames a second with it.
 *
 * What is given up is stated in text instead of in geometry, which is also where the region
 * evidence says it belongs: encoding group membership over a node-link diagram was measured to
 * cost about 25% accuracy on network tasks. And the whole world is one gesture away.
 */
const FOCUS_EDGE_BUDGET = 0;

/**
 * The framebuffer this scene can afford, in device pixels.
 *
 * From the measurement that set the old pixel-ratio cap: at DPR 2 a 1440x836 viewport is 4.82
 * Mpx and at 1.5 it is 2.71 Mpx, and 1.5 was the ratio that held a frame. The reasoning was
 * right and the parameter was wrong - it budgets an *area* while being expressed as a *ratio*,
 * so the same constant lands in two different places on two different viewports. See
 * `pixelRatioFor`.
 */
const FRAMEBUFFER_BUDGET = 2_700_000;

/** How many orbs the curated object can hold: the expansion ceiling, its root, and headroom. */
const CURATED_CAPACITY = 208;

/** Field of view, degrees, for the whole world. */
const WORLD_FOV = 52;

/**
 * Field of view for a curated Focus, and the distance it is framed from.
 *
 * Narrower than the world's 52 degrees, and the reason is the separation guarantee rather than
 * taste. The slab has to fill about ninety per cent of the frame height to be worth looking at,
 * and at a fixed on-screen size the ratio of the slab's radius to the camera distance is fixed by
 * the field of view alone: 0.44 at 52 degrees, 0.28 at 34. That ratio is how much the depth of a
 * rim node differs from the depth of the hub, so it is exactly how far perspective can pull the
 * projected separation away from the orthographic bound the arbitration proves. Narrowing the
 * lens halves the error, and a curated arrangement wants a flatter lens anyway - a wide one
 * reads as a fisheye of a diagram rather than a view of a place.
 */
const FOCUS_FOV = 34;
const FOCUS_DISTANCE = 900;

/**
 * How far the reader may pull back inside Focus.
 *
 * The separation bound is stated at the framing distance and scales inversely with it, so an
 * unbounded zoom-out is an unbounded loss of the guarantee. At 1.5x the bound at the desktop
 * budget of forty orbs falls from 44 px to 29 px, which is still over an orb diameter; past that
 * it is not, and a reader who wants the whole corpus has a control that says so.
 */
const FOCUS_ZOOM_OUT = 1.5;
const FOCUS_ZOOM_IN = 0.45;

/**
 * How far a dragged neighbourhood may leave its seats, as a share of the in-plane pitch.
 *
 * This is a decision about the separation guarantee and not about feel. `local-physics` clamps a
 * body to its anchor plus this, so the floor after a drag is `pitch - 2 * slack` - 76% of the
 * settled bound at 0.12, which at the desktop budget of forty orbs is 33 px against 44. Raising
 * it loosens the drag and lowers the floor in exactly that proportion.
 */
const DRAG_SLACK = 0.12;

/**
 * How large an orb is allowed to be, per level, in CSS pixels.
 *
 * One ceiling for every node in the graph was the previous rule, and it was wrong in both
 * directions at once. The number was 30 - in *framebuffer* pixels, which is 20 CSS px at the
 * capped ratio - and it was set to stop 35,370 discs from covering the viewport several times
 * over. Applied to a curated scene of forty-one orbs it forbids the size that scene needs: at
 * 26 CSS px those forty-one orbs cover 1.8% of the framebuffer, against 9x overdraw for the
 * whole graph at the old ceiling. The constraint is a count, so the ceiling has to be one too.
 *
 * `gamma` softens the perspective attenuation. At 1 it is the true 1/z, which is correct for a
 * world seen from outside; inside a curated scene the near and far rims differ by about 30% of
 * the framing distance, and full attenuation makes the far half of a deliberate arrangement look
 * like a mistake. 0.65 keeps the ordering visible and the far orbs readable, which is what the
 * evidence on depth-scaled marks asks for - the cue helps, and it helps only while everything
 * stays legible.
 */
type NodeLevel = { minPx: number; maxPx: number; gamma: number };
const NODE_LEVELS: Record<"WORLD" | "PATH" | "NEIGHBOUR" | "ROOT", NodeLevel> = {
    WORLD: { minPx: 1.2, maxPx: 16, gamma: 1 },
    PATH: { minPx: 2.4, maxPx: 22, gamma: 1 },
    NEIGHBOUR: { minPx: 9, maxPx: 26, gamma: 0.65 },
    ROOT: { minPx: 16, maxPx: 40, gamma: 0.65 },
};

/**
 * The resting alpha of a node. 0.85, and a note about why it is not 0.92.
 *
 * ## A retracted measurement, kept because the mistake is instructive
 *
 * This was raised to 0.92 on the finding that six of the nine light-mode group fills fall below
 * 3:1 when composited over ivory at 0.85 - idea and person at 2.74, passage and quiet at 2.75,
 * rite 2.87, deity 2.96. Those figures are reproducible and they are wrong, because they come
 * from compositing in **linear light** and this renderer does not.
 *
 * Both fragment shaders run `colorspace_fragment` before they write, the drawing buffer is RGBA8
 * with no hardware encode, and a non-premultiplied material blends `SRC_ALPHA /
 * ONE_MINUS_SRC_ALPHA`. GL blending therefore operates on the *encoded* bytes the shader wrote,
 * not on linear values. Under that pipeline the same nine fills measure 3.09 to 3.77 at 0.85 -
 * worst case idea at **3.093** - so every one of them clears the threshold and there was never a
 * defect here to fix.
 *
 * What made the error convincing is that the linear model is self-consistent and reproduces its
 * own six numbers exactly. A contrast figure is only meaningful together with the stage of the
 * pipeline it was taken at, and the stage that matters is the one the hardware blends in.
 *
 * So the value goes back. The margin at 0.85 is thin - 0.093 over an unrounded threshold - and
 * that is worth knowing, but it is a palette observation and not a reason for the renderer to
 * quietly redefine a shipped weight.
 */
const NODE_ALPHA_REST = 0.85;

/**
 * Curated orbs are the thing the reader asked for, and are drawn at nearly full strength.
 *
 * Not a contrast fix - they clear 3:1 comfortably at any of these weights. A Focus scene holds
 * forty orbs rather than 35,370, so there is no density for translucency to accumulate into and
 * nothing for it to buy; what it costs is the solidity that makes an orb read as a body rather
 * than as a stain, which is the whole point of the level.
 */
const NODE_ALPHA_CURATED = 0.98;

/** Relative luminance of a linear-light triple, per WCAG. */
function luminance(r: number, g: number, b: number) {
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/* sRGB transfer, both directions. Needed because the fog mixes in one space and the hardware
   blends in the other; see `fogCeiling`. */
const encodeSrgb = (v: number) =>
    v <= 0.0031308 ? v * 12.92 : 1.055 * v ** (1 / 2.4) - 0.055;
const decodeSrgb = (v: number) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);

/**
 * How much a node may be fogged toward the page before it stops clearing 3:1 against it.
 *
 * Aerial perspective toward the paper is the manuscript-correct depth cue and the arbitration
 * requires it clamped so that the farthest node still measures 3:1 at the far plane. That clamp
 * is computable rather than a matter of judgement: the shader mixes in linear light, luminance is
 * linear in the components, and the composite a reader actually sees is
 *
 *     page + alpha * (1 - fog) * (fill - page)
 *
 * so this solves that for the fog at which the worst group in the palette reaches exactly 3:1 and
 * returns the smallest answer over all of them. Conservative on purpose: one fill at the floor
 * sets the ceiling for every fill, because the alternative is a per-group fog that makes depth
 * mean something different for each colour.
 *
 * The measured consequence is worth recording, because it is large and it is not a defect. On the
 * light palette at alpha 0.92 the answer is **3.0%** - the ink is already close to the paper, so
 * there is almost no room between the fill and the page for aerial perspective to use. On the
 * dark palette it is **49%**. Fog is a dark-mode cue in this product, and in light mode the depth
 * has to come from occlusion, size and parallax instead.
 */
function fogCeiling(groupColours: Float32Array, background: Color, alpha: number) {
    const pageLinear = [background.r, background.g, background.b];
    /* What the clear colour actually leaves in the buffer, which is what the fill blends over. */
    const pageEncoded = pageLinear.map(encodeSrgb);
    const page = luminance(pageLinear[0], pageLinear[1], pageLinear[2]);

    /*
     * Two spaces, in the order the hardware uses them.
     *
     * The fog mixes inside the shader, so it mixes in linear light. The alpha blend happens
     * afterwards against bytes already in the framebuffer, and by then `colorspace_fragment` has
     * encoded what the shader wrote - so that half is an encoded-space blend. An earlier version
     * of this function folded both into one linear step and produced an answer that was wrong in
     * the same direction as the retracted note on NODE_ALPHA_REST: it under-reported every
     * contrast ratio and so under-reported the fog this palette can afford.
     */
    const contrastAt = (offset: number, fog: number) => {
        let r = 0;
        let g = 0;
        let b = 0;
        for (let axis = 0; axis < 3; axis += 1) {
            const linear = groupColours[offset + axis];
            const fogged = linear * (1 - fog) + pageLinear[axis] * fog;
            const blended =
                encodeSrgb(fogged) * alpha + pageEncoded[axis] * (1 - alpha);
            const back = decodeSrgb(blended);
            if (axis === 0) r = back;
            else if (axis === 1) g = back;
            else b = back;
        }
        const value = luminance(r, g, b);
        return (Math.max(value, page) + 0.05) / (Math.min(value, page) + 0.05);
    };

    /* Half is a cosmetic ceiling on top of the contrast one: past it the far orbs stop reading as
       receding and start reading as absent, whatever the ratio says. */
    let ceiling = 0.5;
    for (let i = 0; i * 3 + 2 < groupColours.length; i += 1) {
        const offset = i * 3;
        /* A fill that does not clear the gate unfogged cannot be fogged at all, and the answer
           for the whole palette is then no fog rather than a per-group fog - depth that means a
           different distance for each colour is not a depth cue. */
        if (contrastAt(offset, 0) < 3) return 0;
        /* Bisected rather than solved. The encode is not invertible in one step, and 24 halvings
           over eleven groups is a few hundred evaluations on a human action. */
        let lo = 0;
        let hi = ceiling;
        for (let step = 0; step < 24; step += 1) {
            const mid = (lo + hi) / 2;
            if (contrastAt(offset, mid) >= 3) lo = mid;
            else hi = mid;
        }
        ceiling = Math.min(ceiling, lo);
    }
    return Math.max(0, ceiling);
}

export type EngineEvents = {
    onHover?: (node: number | null) => void;
    /**
     * The reader pressed and released without dragging, and this is what was under them.
     *
     * This replaced `onSelect`, and the rename is the fix rather than a tidy-up. `onSelect` was
     * emitted from the `select()` *command*, so a consumer that both listened for a selection
     * and commanded one had a loop, and the only way out of it was for the consumer that owned
     * the state to stop listening - which is exactly what the graph page did. It wired the
     * canvas to a local `useState` and never told the state model a subject had been chosen at
     * all, so the reader was looking at Indra while the application believed it was showing the
     * whole corpus. Everything downstream of that - a renderer switch that lost the subject, a
     * view control that read World, a panel that vanished on a click into empty space - was one
     * missing write.
     *
     * So the two directions are now separate and named for what they are. `select()` is a
     * command travelling down and emits nothing. This is an event travelling up, raised only
     * from a real tap, classified by `installGestures` rather than by `click`.
     *
     * Null means the reader tapped the background. That is a legitimate thing to do and each
     * consumer decides what it means; the engine does not decide for them.
     */
    onTap?: (node: number | null) => void;
    /** Called after each rendered frame, once the camera matrices are current. */
    onFrame?: () => void;
    /**
     * The renderer has genuinely stopped working.
     *
     * Raised only from a lost WebGL context - never from a slow frame. A frame-rate sample is
     * not a failure, and treating one as a failure is how a product starts changing modes
     * underneath a reader who is only orbiting.
     */
    onLost?: (detail: string) => void;
    /** Emitted about once a second with measured frame cost, for the HUD and the benchmark. */
    onStats?: (stats: EngineStats) => void;
};

/**
 * A curated neighbourhood, as the engine needs it.
 *
 * Structural on purpose. Choosing *which* neighbours are worth drawing is a substantial piece of
 * work with its own vocabulary - relationship families, coverage rounds, salience, bridges - and
 * none of it belongs in a renderer. This type names only what has to be drawn, so the engine
 * depends on no selection module and the selection module can be replaced without touching a
 * buffer. The objects the selection module already produces satisfy it as they are.
 *
 * The order of `members` is the caller's salience order and it is load-bearing three times over:
 * it sets the slab offset, it decides which seat inside a family sector a member takes, and it
 * is the order the transition staggers in. It is also the only identity the transition has -
 * every mark is keyed on `node`, never on a slot in these arrays, because a mark that is reused
 * to depict a different subject across a transition destroys the one question an animated
 * transition exists to answer.
 */
export type FocusScene = {
    root: number;
    members: ReadonlyArray<{
        node: number;
        /** Which relationship family sectors this member. An index; the engine holds no vocabulary. */
        family: number;
    }>;
    /** Every root-to-neighbour line to draw. */
    spokes: ReadonlyArray<{ edge: number; node: number }>;
    /** Every neighbour-to-neighbour line to draw. */
    between: ReadonlyArray<{ edge: number; a: number; b: number }>;
};

export type EngineStats = {
    /** Derived from the real frame interval, not from how long `render` took to return. */
    fps: number;
    frameMs: number;
    /** 95th percentile frame interval over the sampling window. */
    p95Ms: number;
    /** The JavaScript half of the frame. Its distance from `frameMs` is the GPU and vsync. */
    jsMs: number;
    /** Nodes that survive the shader's alpha discard. Not the size of the buffer. */
    drawnNodes: number;
    drawnEdges: number;
};

/* --------------------------------------------------------------- shaders - */

/*
 * Size is by degree, not by importance, and the mapping is a cube root.
 *
 * Degree in this graph runs from 0 to 7,347 and is very long-tailed: the median is 7 and the
 * 99th percentile is 49. Linear sizing makes Indra a disc and everything else a speck; a cube
 * root compresses that into a range the eye can still read as an ordering.
 */
const NODE_VERTEX = /* glsl */ `
    attribute float aSize;
    attribute vec3 aColour;
    attribute float aAlpha;
    /** 1 on the subject of a curated scene, 0 on everything else. Selects the clamp. */
    attribute float aRoot;
    uniform float uScale;
    /**
     * A whole-object opacity multiplier.
     *
     * Here rather than in the per-vertex alpha because the transition fades 35,370 nodes out,
     * and rewriting that many floats sixty times a second to do it is a pass over 141 KB per
     * frame for a value that is the same everywhere. One uniform write does the same thing.
     */
    uniform float uAlpha;
    uniform float uGamma;
    uniform float uRefDepth;
    uniform vec2 uClamp;
    uniform vec2 uRootClamp;
    uniform float uFogNear;
    uniform float uFogFar;
    varying vec3 vColour;
    varying float vAlpha;
    varying float vFog;
    void main() {
        vColour = aColour;
        vAlpha = aAlpha * uAlpha;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        float depth = max(-mv.z, 1.0);
        /*
         * Perspective size attenuation, softened by uGamma and clamped per level.
         *
         * A node twice as far is half as wide, which is what makes depth readable without fog
         * or glow. Unclamped, though, the division by view depth is unbounded: fly the camera
         * up to a hub and its disc grows without limit, and a node with 7,347 edges seen from
         * close range covers a large part of the viewport. Measured, that is not a cosmetic
         * problem - the same scene that holds 60 fps at world distance fell to 10 fps with the
         * camera brought in, because a handful of discs were each filling millions of pixels.
         *
         * At uGamma = 1 this is exactly the 1/z it has always been, whatever uRefDepth says.
         * Below 1 the attenuation is flattened about uRefDepth, which is what a curated scene
         * needs: its far rim is about 30% further away than its hub, and full attenuation there
         * makes a deliberate arrangement look like an accident of distance.
         *
         * The clamp arrives as a uniform pair rather than as the old literal 30. That number was
         * in framebuffer pixels and applied to every node in the graph at once, which is both
         * why it exists - 35,370 discs at that size cover the viewport nine times over - and why
         * it was wrong for a scene of forty-one. See NODE_LEVELS.
         */
        float size = aSize * uScale * pow(uRefDepth, uGamma - 1.0) / pow(depth, uGamma);
        vec2 limits = mix(uClamp, uRootClamp, aRoot);
        gl_PointSize = clamp(size, limits.x, limits.y);
        vFog = clamp((depth - uFogNear) / max(uFogFar - uFogNear, 1.0), 0.0, 1.0);
        gl_Position = projectionMatrix * mv;
    }
`;

/*
 * A matte disc with a soft edge, not a glowing ball.
 *
 * The default reach here would be an additive sprite with a bloom pass, which is the house
 * style of every crypto network visualisation and reads as decoration rather than as data.
 * This is a flat fill with one pixel of antialiasing at the rim, so a dense region reads as
 * dense because there are more discs in it, not because it is brighter.
 */
const NODE_FRAGMENT = /* glsl */ `
    varying vec3 vColour;
    varying float vAlpha;
    varying float vFog;
    uniform vec3 uFog;
    uniform float uFogMax;
    uniform vec3 uKeyTint;
    /** 0 shades the unlit side, 1 lights the lit side. See uKeyAmount. */
    uniform float uKeyShape;
    uniform float uKeyAmount;
    uniform vec3 uLight;
    void main() {
        /*
         * A node dimmed out of the current focus is discarded, not faded.
         *
         * Shading a fragment at alpha 0.08 costs exactly what shading it at 1.0 costs, and
         * with a node selected there are 35,000 of them between the camera and the thing the
         * reader asked to look at. Measured, that was the difference between four frames a
         * second and sixty. It is also the better picture: the neighbourhood was legible
         * only in the sense that it was drawn, because it sat behind a wash of everything
         * else. The backbone edges stay drawn, so the focused subject keeps a visible
         * position in the whole rather than floating in nothing.
         */
        if (vAlpha < 0.14) discard;
        vec2 d = gl_PointCoord - vec2(0.5);
        float r = dot(d, d);
        if (r > 0.25) discard;
        float edge = smoothstep(0.25, 0.19, r);
        /*
         * One soft key light, from the disc's own coordinates.
         *
         * The hemisphere is free: a unit normal over a point sprite is the point coordinate and
         * the height that makes it unit length, so this is three instructions and no texture, no
         * second pass and no geometry. It is the cheapest thing in the depth-cue ranking that
         * makes a flat fill read as a body.
         *
         * The direction it shades in is not free, though, and the choice here is the one that
         * cannot cost contrast. The fills are measured against the page at 3:1 with very little
         * headroom, so shading is applied only *towards* the high-contrast side: the unlit half
         * darkens on an ivory page and the lit half lightens on a carbon one. The alternative -
         * a symmetric light that brightens one side and darkens the other - would have lifted
         * half of every orb towards the paper it has to be distinguishable from.
         */
        /*
         * Both cues are behind a uniform test, and it is worth 1.7 ms of the world frame.
         *
         * The key light is applied only to the curated object - at world scale an orb is two to
         * four pixels across and a hemisphere on it is invisible - and the fog ceiling in light
         * mode is 1.3% at the resting alpha. Measured, executing the shading and the mix anyway cost the
         * WORLD draw 4.8 ms against 3.1, because 35,370 discs at the closer framing cover the
         * framebuffer twice over and every covered pixel paid for a sqrt, a dot and two mixes it
         * then discarded. A uniform branch is the same value for every fragment in the draw, so
         * it is perfectly coherent and costs nothing.
         */
        vec3 colour = vColour;
        if (uKeyAmount > 0.0) {
            vec3 normal = vec3(d * 2.0, sqrt(max(0.0, 1.0 - 4.0 * r)));
            float lit = clamp(dot(normal, uLight), 0.0, 1.0);
            colour = mix(colour, uKeyTint, uKeyAmount * mix(1.0 - lit, lit, uKeyShape));
        }
        /* Aerial perspective toward the paper, not fog toward black. uFogMax is solved against
           the 3:1 gate rather than chosen; see fogCeiling. */
        if (uFogMax > 0.0) colour = mix(colour, uFog, vFog * uFogMax);
        gl_FragColor = vec4(colour, vAlpha * edge);
        /*
         * Encoded on the way out, like every stock material in the library.
         *
         * This line was missing, and its absence was a real defect rather than a nicety. The
         * palette hands these shaders linear-light triples - toLinearTriple in palette.ts for
         * the group fills, and Color.r/g/b for the edge ink, which Three keeps linear by design
         * - and a shader that writes a linear value into an 8-bit sRGB framebuffer without
         * encoding it publishes a colour darker than the one it was given. Light-mode deity
         * bd4f32 was reaching the screen as 821408.
         *
         * Which is what made the graph muddy, and why recolouring would not have fixed it. It
         * also inverted by theme: darkening everything happens to raise contrast against ivory
         * and destroys it against carbon, where the focus edges were landing darker than the
         * page they were drawn on - the relations a reader selected a subject to see, rendered
         * invisible.
         *
         * The tell was that the selection overlay looked right while everything around it did
         * not: that object is a LineBasicMaterial, and Three own basic shader carries this
         * include. One canvas was running two colour pipelines.
         */
        #include <colorspace_fragment>
    }
`;

const EDGE_VERTEX = /* glsl */ `
    attribute float aAlpha;
    attribute vec3 aColour;
    varying float vAlpha;
    varying vec3 vColour;
    void main() {
        vAlpha = aAlpha;
        vColour = aColour;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
`;

const EDGE_FRAGMENT = /* glsl */ `
    varying float vAlpha;
    varying vec3 vColour;
    void main() {
        if (vAlpha <= 0.004) discard;
        gl_FragColor = vec4(vColour, vAlpha);
        #include <colorspace_fragment>
    }
`;

/* ------------------------------------------------------------ the engine - */

export type EngineOptions = {
    canvas: HTMLCanvasElement;
    world: World;
    /** One rgb triple per semantic group, read from the token layer at mount. */
    groupColours: Float32Array;
    background: Color;
    edgeColour: Color;
    /** Rubric red, reserved for the selected node's own connections. */
    accentColour: Color;
    reducedMotion: boolean;
    events?: EngineEvents;
    /**
     * What the reader may do to the camera. Defaults to everything, which is right for the
     * graph page, where the canvas is the page.
     *
     * The homepage is the reason this is an option. A preview of the world sits inside a
     * document that scrolls, and OrbitControls consumes the wheel to zoom - so a reader
     * scrolling past the hero would find the page stuck while the graph crept closer. Turning
     * zoom off hands the wheel back to the document. `autoRotate` gives that same preview its
     * slow drift without a second animation loop competing with this one.
     */
    controls?: { zoom?: boolean; pan?: boolean; autoRotate?: number };
    /**
     * Multiplies the resting weight of every edge. One is the world's own setting.
     *
     * The resting alpha is 0.05, which is correct for 185,693 lines whose crossings accumulate
     * into visible structure and useless for a small graph, where a hundred lines at 0.05 are
     * simply not there. The homepage preview draws fifty nodes and needs its connections to be
     * connections; it is the same ink, applied at a weight that suits the number of strokes.
     */
    edgeWeight?: number;
    /**
     * An upper bound on frames per second. Unset means every frame the display offers.
     *
     * The graph page takes every frame, because a reader dragging the world is judging it on
     * exactly that. The homepage preview does not: it drifts slowly under no one's hand, and
     * measured, rendering it at the display rate cost 431 ms of main thread per five seconds
     * against a 275 ms budget for the whole page. Half the frames of a slow rotation is a cost
     * halved and a difference nobody can see.
     */
    maxFps?: number;
    /**
     * What the browser keeps of a touch on this canvas.
     *
     * Unset leaves OrbitControls' own `none`, which is right where the canvas is the page. The
     * homepage sets `pan-y pinch-zoom` so a finger can still scroll and still pinch: a preview
     * is not entitled to take a third of the fold and refuse both.
     */
    touchAction?: string;
};

export class WorldEngine {
    private readonly renderer: WebGLRenderer;
    private readonly scene = new Scene();
    private readonly camera: PerspectiveCamera;
    private readonly controls: OrbitControls;
    private readonly world: World;
    private readonly events: EngineEvents;

    private nodes!: Points;
    private edges!: LineSegments;
    private selectionEdges!: LineSegments;
    private selectionPositions!: Float32Array;
    private accent: Color;
    private background: Color;
    private nodeAlpha!: Float32Array;
    private nodeColour!: Float32Array;
    private nodeSize!: Float32Array;
    private nodeRoot!: Float32Array;
    private edgeAlpha!: Float32Array;
    private edgeColour!: Float32Array;

    /**
     * Where every node is *drawn*, which is not where the artifact says it is.
     *
     * The engine used to hand `world.positions` straight into a `BufferAttribute`, by reference.
     * Nothing was written through it, so nothing was wrong - and the first animated position
     * would have been. That array is the canonical layout: the planar renderer reads it, the pick
     * index projects it, the label layer interpolates along it, and any future re-read of the
     * artifact expects it unchanged. Moving a node for a transition would have silently rewritten
     * the world for every one of them, in place, with no way back.
     *
     * So the engine owns a copy and every consumer of a position inside this class reads it:
     * `updateSelectionEdges`, `rebuildPickIndex`, `projectSegmentPoints`, `screenPositionOf` and
     * `positionOf`. Missing one would put labels or hit targets on the pre-animation positions,
     * which is a defect that looks like a rounding error and is not one.
     */
    private drawPositions!: Float32Array;

    /**
     * The curated set, as its own small `Points` object.
     *
     * Two sets need two objects because they need opposite settings. The world draws 35,370
     * translucent discs that are meant to accumulate into density, so it writes no depth and
     * clamps small. Forty-one curated orbs are meant to be bodies in a place, so they write depth
     * - which is what makes one occlude another, the strongest static depth cue there is and the
     * single biggest available win here - and clamp large. One object cannot do both, and trying
     * to was what made the previous Focus read as a flat wash.
     */
    private curated!: Points;
    private curatedPositions!: Float32Array;
    private curatedColour!: Float32Array;
    private curatedSize!: Float32Array;
    private curatedAlpha!: Float32Array;
    private curatedRoot!: Float32Array;
    /** Node index per curated slot. The identity a transition keys on. */
    private curatedNodes: number[] = [];
    private curatedSlot = new Map<number, number>();
    /** Where each curated slot started and where it is going, in world units. */
    private curatedFrom!: Float32Array;
    private curatedTo!: Float32Array;

    private focusScene: FocusScene | null = null;
    private focusSlab: FocusSlab | null = null;
    private focusSpread: SlabSpread = "compact";
    /** A live 3D relaxation over the curated set, while a reader is pulling one of them about. */
    private field: Field | null = null;
    private heldSlot: number | null = null;
    /** Picked on the press, promoted to a hold on the first travel. See `offerGrab`. */
    private pendingGrab: number | null = null;
    /** True while the curated object is the thing being drawn. */
    private focusActive = false;
    /**
     * A running World <-> Focus transition. Null when nothing is in flight.
     *
     * `scope` is the correction to a real defect rather than a generalisation. A re-space reuses
     * this machinery to move orbs to new seats, and reusing all of it meant replaying the whole
     * schedule - including the context weight, which starts at 1. So pressing re-space inside
     * Focus flashed the entire 35,370-node world back into view for 400 ms and then faded it out
     * again, over a scene that had deliberately hidden it. A travel-only stage moves geometry and
     * touches nothing else.
     */
    private stage: {
        started: number;
        direction: TransitionDirection;
        scope: "full" | "travel";
    } | null = null;
    private weights: TransitionWeights | null = null;

    private groupColours: Float32Array;
    private edgeBase: Color;
    private reducedMotion: boolean;

    private frame = 0;
    private disposed = false;
    private readonly releaseGestures: () => void;
    /**
     * Frames actually rendered. Only ever increases.
     *
     * Exposed because "the renderer stopped when it left the screen" is not provable from the
     * HUD - which keeps its last text after the loop stops and looks identical either way - and
     * not reliably provable from `renderer.info`, which three resets each frame. A test reads
     * this before and after and asserts they are *equal*, which is an exact claim rather than a
     * small-enough one.
     */
    private drawn = 0;
    private selected: number | null = null;
    private path: number[] = [];
    private hovered: number | null = null;
    /** Hovered, and drawn as such. Never dims the world; see `setEmphasis`. */
    private emphasis: number | null = null;
    private readonly edgeWeight: number;
    /** Minimum milliseconds between rendered frames, from `maxFps`. Zero means no limit. */
    private readonly frameInterval: number;
    private lastDrawn = 0;
    /** Edges of the canvas covered by chrome, in CSS pixels. See `setSafeArea`. */
    private safeArea = { top: 0, right: 0, bottom: 0, left: 0 };
    private mode: WorldMode = "WORLD";

    /** Screen-space buckets, rebuilt when the camera settles. Picking reads these. */
    private pickCell = 24;
    private pickBuckets = new Map<number, number[]>();
    private pickDirty = true;
    private readonly projected: Float32Array;

    private frameTimes: number[] = [];
    private jsTimes: number[] = [];
    private lastFrame = 0;
    private lastStats = 0;
    private drawnEdges = 0;
    private drawnNodes = 0;
    private edgeBudgetOverride: number | null = null;
    private paused = false;
    private readonly onContextLost: (event: Event) => void;

    /** Set while a scripted camera move is running; any user input clears it. */
    private flight: {
        from: Vector3;
        to: Vector3;
        fromTarget: Vector3;
        toTarget: Vector3;
        started: number;
        ms: number;
    } | null = null;

    constructor(options: EngineOptions) {
        this.world = options.world;
        this.events = options.events ?? {};
        this.groupColours = options.groupColours;
        this.edgeBase = options.edgeColour;
        this.accent = options.accentColour;
        this.background = options.background;
        this.reducedMotion = options.reducedMotion;
        this.edgeWeight = options.edgeWeight ?? 1;
        this.frameInterval = options.maxFps ? 1000 / options.maxFps : 0;
        this.projected = new Float32Array(options.world.manifest.counts.nodes * 3);

        /*
         * Renderer construction is isolated in one place so a WebGPU backend can be swapped in
         * without touching anything else. Three ships `WebGPURenderer` and it falls back to
         * WebGL 2 on its own, but the WebGPU build is several times larger and the API is not
         * yet available by default in every major browser, so WebGL is what ships.
         */
        this.renderer = new WebGLRenderer({
            canvas: options.canvas,
            antialias: true,
            alpha: false,
            powerPreference: "high-performance",
        });
        const { clientWidth, clientHeight } = options.canvas;
        this.renderer.setPixelRatio(this.pixelRatioFor(clientWidth, clientHeight));
        this.renderer.setClearColor(options.background, 1);
        this.scene.background = options.background;

        this.camera = new PerspectiveCamera(
            WORLD_FOV,
            Math.max(clientWidth, 1) / Math.max(clientHeight, 1),
            1,
            20000,
        );
        this.camera.position.set(0, 0, WORLD_DISTANCE);

        this.controls = new OrbitControls(this.camera, options.canvas);
        this.controls.enableDamping = !options.reducedMotion;
        this.controls.dampingFactor = 0.08;
        this.controls.rotateSpeed = 0.55;
        this.controls.zoomSpeed = 0.9;
        this.controls.panSpeed = 0.7;
        this.controls.minDistance = 40;
        this.controls.maxDistance = 6000;
        this.controls.enableZoom = options.controls?.zoom ?? true;
        this.controls.enablePan = options.controls?.pan ?? true;
        // A drift is motion, so it is refused outright where motion has been declined rather
        // than merely slowed: `reducedMotion` means still, not gentler.
        const drift = options.reducedMotion ? 0 : (options.controls?.autoRotate ?? 0);
        this.controls.autoRotate = drift > 0;
        this.controls.autoRotateSpeed = drift;
        // Any real input cancels a scripted move rather than fighting it.
        this.controls.addEventListener("start", () => {
            this.flight = null;
        });
        this.controls.addEventListener("change", () => {
            this.pickDirty = true;
        });

        /*
         * Gestures, here, once, for everything that draws with this engine.
         *
         * OrbitControls is constructed three lines above, and it is the whole reason a `click`
         * on this canvas cannot be trusted: it captures the pointer to orbit and the release
         * still dispatches a click. Each consumer used to answer that for itself, with a
         * different threshold, and two of the three answers were wrong - the homepage navigated
         * on every orbit, and the planar view could be panned into clearing the reader's
         * selection. The discrimination belongs next to the thing that makes it necessary.
         *
         * Hover is routed through the same place for the same reason: during a drag there is no
         * hover, and a view that has to remember to suppress it will one day forget.
         */
        this.releaseGestures = installGestures(options.canvas, {
            onTap: (point) => this.events.onTap?.(this.pick(point.x, point.y)),
            onHoverMove: (point) => this.hover(point.x, point.y),
            onHoverLeave: () => {
                this.hovered = null;
                this.events.onHover?.(null);
                this.setEmphasis(null);
            },
            onGrabCheck: (point) => this.offerGrab(this.pick(point.x, point.y)),
            onGrabMove: (point) => this.moveGrab(point.x, point.y),
            onGrabEnd: () => this.releaseGrab(),
        });

        /*
         * What the browser may do with a touch here.
         *
         * `OrbitControls.connect` sets `touch-action: none` on its element unconditionally -
         * it does not consult `enablePan` or `enableZoom` - and inline style beats any
         * stylesheet. On a full-screen graph that is right: vertical orbit is the point and the
         * canvas is the page. On the homepage it meant a finger landing in the hero could
         * neither scroll the page nor pinch to zoom it, on a panel taking about a third of the
         * fold. Applied after the controls, because `connect` would otherwise overwrite it.
         */
        if (options.touchAction) options.canvas.style.touchAction = options.touchAction;

        this.onContextLost = (event: Event) => {
            event.preventDefault();
            this.disposed = true;
            cancelAnimationFrame(this.frame);
            this.events.onLost?.("the graphics context was lost");
        };
        options.canvas.addEventListener("webglcontextlost", this.onContextLost);

        this.buildEdges();
        this.buildSelectionEdges();
        // Nodes last, so their translucent discs blend over the lines rather than under them.
        this.buildNodes();
        this.buildCurated();
        /*
         * The depth cues are derived here as well as in `setPalette`, and the duplication is the
         * fix rather than an oversight.
         *
         * `setPalette` is called from an effect that watches the palette, and the engine is built
         * asynchronously after the artifact loads - long after that effect first runs. So the
         * effect finds no engine, does nothing, and never fires again, because the palette does
         * not change. Measured: the fog ceiling stayed at its initial 0 and the key light at no
         * tint for the whole session, so two of the five ranked depth cues were silently absent
         * and nothing in the scene said so.
         *
         * This is the same shape as the defect already recorded against `setPaused` a few lines
         * below, which is why it is worth naming: an engine built after first render cannot be
         * configured only by effects that run before it exists.
         */
        this.applyDepthCues();
        this.resize();
    }

    /**
     * The device pixel ratio this canvas can afford.
     *
     * The old rule was `min(devicePixelRatio, 1.5)`, and its comment did the arithmetic for a
     * 1440x836 desktop correctly: 4.82 Mpx at DPR 2 against 2.71 Mpx at 1.5, and 1.5 was the
     * ratio that held a frame. The defect is that it reasons about a *ratio* while the thing it
     * budgets is an *area*, so the same constant lands somewhere quite different on a different
     * viewport. On a 390x780 phone the cap produced a 0.68 Mpx framebuffer - a quarter of what
     * the engine had decided it could afford - and upscaled it to fill the screen. The scene was
     * blurred to save a budget that was not being spent.
     *
     * Expressed as an area it lands in the same place everywhere: 1440x836 gets 1.4976 rather
     * than 1.5, which is the same framebuffer to within 0.03%, and the phone gets its native 2.
     *
     * Floored at 1 so a large viewport is never rendered below native and upscaled, which is a
     * worse trade than a slow frame. Capped at 2 because a point sprite and a hairline have no
     * fine detail for a third sample to resolve.
     *
     * ## The large-desktop arm is deliberately unchanged
     *
     * On a 2560x1400 viewport the area rule asks for 1, which would cut the framebuffer from
     * 8.06 Mpx to 3.58 - a 2.25x reduction on a class of machine this phase has not measured,
     * and a visible softening if the frame did not need it. A plausible improvement that has not
     * been measured is not an improvement, so above the budget the ratio is floored at the old
     * 1.5 and the cut waits for a number. The defect being fixed here is the small and medium
     * case, where the direction is not in doubt.
     */
    private pixelRatioFor(width: number, height: number) {
        const css = Math.max(width * height, 1);
        const byArea = Math.sqrt(FRAMEBUFFER_BUDGET / css);
        const floor = css > FRAMEBUFFER_BUDGET ? 1.5 : 1;
        return Math.min(window.devicePixelRatio, Math.max(floor, Math.min(2, byArea)));
    }

    /* ---------------------------------------------------------- geometry - */

    private buildNodes() {
        const { positions, nodeGroup, nodeDegree, manifest } = this.world;
        const count = manifest.counts.nodes;

        this.drawPositions = positions.slice();
        this.nodeColour = new Float32Array(count * 3);
        this.nodeSize = new Float32Array(count);
        this.nodeAlpha = new Float32Array(count);
        /* Nothing in the world buffer is ever a curated root; the attribute exists so both node
           objects can share one shader rather than forking it for one `mix`. */
        this.nodeRoot = new Float32Array(count);

        for (let i = 0; i < count; i += 1) {
            const group = nodeGroup[i];
            this.nodeColour[i * 3] = this.groupColours[group * 3];
            this.nodeColour[i * 3 + 1] = this.groupColours[group * 3 + 1];
            this.nodeColour[i * 3 + 2] = this.groupColours[group * 3 + 2];
            /*
             * Sizes in world units, chosen so the on-screen result is a few pixels.
             *
             * `gl_PointSize` is in pixels after the shader divides by view depth, so these
             * numbers are only meaningful together with the distance the world is viewed
             * from. The first version used 90 + cbrt(degree) * 105, which at the default
             * camera distance made an unconnected node 30 pixels across and Indra roughly
             * 700 - and 35,370 discs of that size cover a 1440-pixel viewport many times
             * over. It was the whole frame budget, and it was invisible as a cause because
             * the picture looked approximately right.
             *
             * Measured: with those sizes, removing 98.6% of the edges moved the frame
             * interval from 66.6 ms only to 50.2 ms. Fill from the nodes was the floor.
             */
            this.nodeSize[i] = 9 + Math.cbrt(nodeDegree[i]) * 2.6;
            this.nodeAlpha[i] = NODE_ALPHA_REST;
        }
        this.drawnNodes = count;

        const geometry = new BufferGeometry();
        geometry.setAttribute("position", new BufferAttribute(this.drawPositions, 3));
        geometry.setAttribute("aColour", new BufferAttribute(this.nodeColour, 3));
        geometry.setAttribute("aSize", new BufferAttribute(this.nodeSize, 1));
        geometry.setAttribute("aAlpha", new BufferAttribute(this.nodeAlpha, 1));
        geometry.setAttribute("aRoot", new BufferAttribute(this.nodeRoot, 1));

        const material = new ShaderMaterial({
            vertexShader: NODE_VERTEX,
            fragmentShader: NODE_FRAGMENT,
            uniforms: this.nodeUniforms("WORLD", 0),
            transparent: true,
            // Depth writing off, so a node behind another does not punch a hole in it; the
            // discs are translucent and are meant to accumulate into density. That is right
            // here and wrong for the curated set, which is why they are two objects.
            depthWrite: false,
        });
        this.nodes = new Points(geometry, material);
        // One object for the whole graph means frustum culling is all-or-nothing, and since
        // the camera is usually inside the cloud it would never cull anything anyway.
        this.nodes.frustumCulled = false;
        this.scene.add(this.nodes);
    }

    /**
     * The curated object: opaque, large, few.
     *
     * Allocated once at the expansion ceiling and redrawn by moving the draw range, so choosing a
     * subject never allocates - the same arrangement the selection overlay already uses and for
     * the same reason.
     *
     * `depthWrite` is the point of it existing. An orb that writes depth occludes the one behind
     * it and occludes the lines that pass behind it, which is the strongest static depth cue
     * available and the reason additive-blended graphs read flat. The rim's antialiasing writes
     * depth too, so there is a pixel of halo where two orbs touch; at the guaranteed separation
     * they never do.
     */
    private buildCurated() {
        this.curatedPositions = new Float32Array(CURATED_CAPACITY * 3);
        this.curatedColour = new Float32Array(CURATED_CAPACITY * 3);
        this.curatedSize = new Float32Array(CURATED_CAPACITY);
        this.curatedAlpha = new Float32Array(CURATED_CAPACITY);
        this.curatedRoot = new Float32Array(CURATED_CAPACITY);
        this.curatedFrom = new Float32Array(CURATED_CAPACITY * 3);
        this.curatedTo = new Float32Array(CURATED_CAPACITY * 3);

        const geometry = new BufferGeometry();
        geometry.setAttribute("position", new BufferAttribute(this.curatedPositions, 3));
        geometry.setAttribute("aColour", new BufferAttribute(this.curatedColour, 3));
        geometry.setAttribute("aSize", new BufferAttribute(this.curatedSize, 1));
        geometry.setAttribute("aAlpha", new BufferAttribute(this.curatedAlpha, 1));
        geometry.setAttribute("aRoot", new BufferAttribute(this.curatedRoot, 1));
        geometry.setDrawRange(0, 0);

        const material = new ShaderMaterial({
            vertexShader: NODE_VERTEX,
            fragmentShader: NODE_FRAGMENT,
            uniforms: this.nodeUniforms("NEIGHBOUR", 0.18),
            transparent: true,
            depthWrite: true,
        });
        this.curated = new Points(geometry, material);
        this.curated.frustumCulled = false;
        /* Before the lines, so the lines are depth-tested against orbs that have already written
           depth. Three sorts transparent objects by distance, which for two objects sharing a
           centre is not an order anybody should rely on. */
        this.curated.renderOrder = 1;
        this.selectionEdges.renderOrder = 2;
        this.scene.add(this.curated);
    }

    /**
     * The uniform block for a node object at a given level.
     *
     * One function so the two objects cannot drift, which is the failure mode this whole phase
     * has been repairing elsewhere in the graph code.
     */
    private nodeUniforms(level: keyof typeof NODE_LEVELS, key: number) {
        return {
            uScale: { value: 1 },
            uAlpha: { value: 1 },
            uGamma: { value: NODE_LEVELS[level].gamma },
            uRefDepth: { value: 1200 },
            uClamp: { value: new Vector2(1, 30) },
            uRootClamp: { value: new Vector2(1, 30) },
            uFogNear: { value: 400 },
            uFogFar: { value: 2600 },
            uFog: { value: new Vector3(1, 1, 1) },
            uFogMax: { value: 0 },
            uKeyTint: { value: new Vector3(0, 0, 0) },
            uKeyShape: { value: 0 },
            uKeyAmount: { value: key },
            /* From the upper left, which is where every reader expects a light to be. Unit
               length, so the shader can dot it against the hemisphere normal directly. */
            uLight: { value: new Vector3(-0.48, -0.62, 0.62).normalize() },
        };
    }

    private buildEdges() {
        const { positions, edgePairs, manifest } = this.world;
        const edgeCount = manifest.counts.edges;
        const vertices = new Float32Array(edgeCount * 6);
        this.edgeAlpha = new Float32Array(edgeCount * 2);
        this.edgeColour = new Float32Array(edgeCount * 6);

        for (let i = 0; i < edgeCount; i += 1) {
            const a = edgePairs[i * 2];
            const b = edgePairs[i * 2 + 1];
            vertices[i * 6] = positions[a * 3];
            vertices[i * 6 + 1] = positions[a * 3 + 1];
            vertices[i * 6 + 2] = positions[a * 3 + 2];
            vertices[i * 6 + 3] = positions[b * 3];
            vertices[i * 6 + 4] = positions[b * 3 + 1];
            vertices[i * 6 + 5] = positions[b * 3 + 2];
            for (let v = 0; v < 2; v += 1) {
                this.edgeColour[i * 6 + v * 3] = this.edgeBase.r;
                this.edgeColour[i * 6 + v * 3 + 1] = this.edgeBase.g;
                this.edgeColour[i * 6 + v * 3 + 2] = this.edgeBase.b;
            }
        }
        this.restEdges();

        const geometry = new BufferGeometry();
        geometry.setAttribute("position", new BufferAttribute(vertices, 3));
        geometry.setAttribute("aAlpha", new BufferAttribute(this.edgeAlpha, 1));
        geometry.setAttribute("aColour", new BufferAttribute(this.edgeColour, 3));

        const material = new ShaderMaterial({
            vertexShader: EDGE_VERTEX,
            fragmentShader: EDGE_FRAGMENT,
            transparent: true,
            depthWrite: false,
            /*
             * Normal alpha blending, not additive.
             *
             * Additive is what makes a graph look like a nebula, and where lines cross it
             * accumulates toward white, so the densest regions - the ones carrying the most
             * information - are the ones that blow out. It is also the more expensive blend.
             * On paper, ink gets darker where it overlaps, not brighter.
             */
        });
        this.edges = new LineSegments(geometry, material);
        this.edges.frustumCulled = false;
        this.scene.add(this.edges);
        this.applyEdgeRange();
    }

    /* ------------------------------------------------------------- state - */

    /**
     * The resting weight of every edge.
     *
     * Very quiet, and quieter still for the structural relationships. `CONTAINS` and
     * `HAS_TEXT_VERSION` join a verse to the thing that holds it; there are tens of thousands
     * of them and they say nothing a reader came here to find. Drawn at the same weight as an
     * ascription they are the only thing visible.
     */
    private restEdges() {
        const { edgeType, manifest } = this.world;
        const structural = new Set(
            ["CONTAINS", "HAS_TEXT_VERSION", "HAS_TRANSLATION", "HAS_CHANDAS"]
                .map((name) => manifest.edgeTypes.indexOf(name))
                .filter((index) => index >= 0),
        );
        for (let i = 0; i < manifest.counts.edges; i += 1) {
            const weight = (structural.has(edgeType[i]) ? 0.012 : 0.05) * this.edgeWeight;
            this.edgeAlpha[i * 2] = weight;
            this.edgeAlpha[i * 2 + 1] = weight;
        }
    }

    /**
     * How much of the edge array is drawn.
     *
     * The artifact sorts edges so the semantically loaded ones come first and the structural
     * ones - containment and metre, 38,794 of them - come last. With nothing selected only
     * the first run is drawn. That is not a cosmetic filter: a fragment shaded at alpha 0.012
     * costs exactly what one shaded at alpha 1.0 costs, so leaving them in the draw call was
     * paying full price for something invisible, and it was most of the reason an Intel Iris
     * Xe held 15 fps here.
     *
     * Everything comes back on selection, when a verse's container is a real answer to
     * "what is this attached to" rather than noise behind 35,000 other verses.
     */
    /**
     * The selected node's own edges, drawn as a separate small object.
     *
     * The obvious way to show a neighbourhood is to widen the main draw range until it
     * includes the chosen node's edges, but the array is sorted by structural importance, so
     * one verse's three edges can sit anywhere in 185,693 and reaching them means drawing all
     * of it. Measured, that is 83 ms a frame with the camera in close.
     *
     * A second `LineSegments` sized to the largest degree in the graph solves it exactly: the
     * backbone stays at its budget as context, and the neighbourhood is a few hundred lines
     * on top. The buffer is allocated once at the maximum and redrawn by moving the draw
     * range, so selecting never allocates.
     */
    private buildSelectionEdges() {
        const capacity = Math.min(this.world.manifest.maxDegree + 1, 8192);
        this.selectionPositions = new Float32Array(capacity * 6);
        const geometry = new BufferGeometry();
        geometry.setAttribute("position", new BufferAttribute(this.selectionPositions, 3));
        geometry.setDrawRange(0, 0);
        const material = new LineBasicMaterial({
            color: this.accent,
            transparent: true,
            opacity: 0.75,
            depthWrite: false,
        });
        this.selectionEdges = new LineSegments(geometry, material);
        this.selectionEdges.frustumCulled = false;
        this.scene.add(this.selectionEdges);
    }

    private updateSelectionEdges() {
        const geometry = this.selectionEdges.geometry;
        const positions = this.drawPositions;

        /*
         * A curated Focus draws exactly the lines that were curated, and nothing else.
         *
         * This replaced the full incident set, and the difference is the complaint this phase
         * exists to answer. Selecting Indra used to put 7,347 accent lines on this object, over
         * 24,000 world lines, with all 5,544 of its distinct neighbours brightened - which is
         * the hairball, drawn deliberately and at some expense. What a reader asked for was to
         * see what Indra is attached to, and forty-one orbs with their own lines is that.
         */
        const scene =
            this.path.length <= 1 && this.focusScene && this.focusScene.root === this.selected
                ? this.focusScene
                : null;
        if (scene) {
            const capacity = this.selectionPositions.length / 6;
            let at = 0;
            const write = (a: number, b: number) => {
                if (at >= capacity) return;
                this.selectionPositions[at * 6] = positions[a * 3];
                this.selectionPositions[at * 6 + 1] = positions[a * 3 + 1];
                this.selectionPositions[at * 6 + 2] = positions[a * 3 + 2];
                this.selectionPositions[at * 6 + 3] = positions[b * 3];
                this.selectionPositions[at * 6 + 4] = positions[b * 3 + 1];
                this.selectionPositions[at * 6 + 5] = positions[b * 3 + 2];
                at += 1;
            };
            for (const spoke of scene.spokes) write(scene.root, spoke.node);
            for (const edge of scene.between) write(edge.a, edge.b);
            (geometry.getAttribute("position") as BufferAttribute).needsUpdate = true;
            geometry.setDrawRange(0, at * 2);
            return;
        }

        /* A traced route draws its own steps: the segment between each consecutive pair, in
           order, rather than every edge touching either end of it. */
        if (this.path.length > 1) {
            const steps = Math.min(this.path.length - 1, this.selectionPositions.length / 6);
            for (let i = 0; i < steps; i += 1) {
                const a = this.path[i];
                const b = this.path[i + 1];
                this.selectionPositions[i * 6] = positions[a * 3];
                this.selectionPositions[i * 6 + 1] = positions[a * 3 + 1];
                this.selectionPositions[i * 6 + 2] = positions[a * 3 + 2];
                this.selectionPositions[i * 6 + 3] = positions[b * 3];
                this.selectionPositions[i * 6 + 4] = positions[b * 3 + 1];
                this.selectionPositions[i * 6 + 5] = positions[b * 3 + 2];
            }
            (geometry.getAttribute("position") as BufferAttribute).needsUpdate = true;
            geometry.setDrawRange(0, steps * 2);
            return;
        }

        /* A selection wins over a hover: the reader has committed to one subject, and having
           the overlay jump to whatever the pointer grazes on the way to the panel would undo
           the commitment. */
        const focus = this.selected ?? this.emphasis;
        if (focus === null) {
            geometry.setDrawRange(0, 0);
            return;
        }
        const touching = edgesOf(this.world, focus);
        const capacity = this.selectionPositions.length / 6;
        const count = Math.min(touching.length, capacity);
        for (let i = 0; i < count; i += 1) {
            const a = this.world.edgePairs[touching[i] * 2];
            const b = this.world.edgePairs[touching[i] * 2 + 1];
            this.selectionPositions[i * 6] = positions[a * 3];
            this.selectionPositions[i * 6 + 1] = positions[a * 3 + 1];
            this.selectionPositions[i * 6 + 2] = positions[a * 3 + 2];
            this.selectionPositions[i * 6 + 3] = positions[b * 3];
            this.selectionPositions[i * 6 + 4] = positions[b * 3 + 1];
            this.selectionPositions[i * 6 + 5] = positions[b * 3 + 2];
        }
        (geometry.getAttribute("position") as BufferAttribute).needsUpdate = true;
        geometry.setDrawRange(0, count * 2);
    }

    private applyEdgeRange() {
        const semantic =
            this.world.manifest.semanticEdges ?? this.world.manifest.counts.edges;
        /*
         * A budget, not a filter.
         *
         * Measured on an Intel Iris Xe at 1440x836: drawing all 146,899 semantic edges held
         * 15 fps, and the cost is overdraw rather than geometry - a hairline crossing three
         * hundred pixels is three hundred blended fragments, and at this count the screen is
         * covered many times over. Cutting the draw to the backbone is the only lever that
         * moves it, and it costs nothing legible: at world scale an individual edge among a
         * hundred thousand is not a line anyone can follow, it is texture.
         *
         * The artifact has already sorted edges so that taking a prefix takes the structure
         * between well-connected subjects first, so this is a range and not a scan.
         */
        /*
         * The backbone budget holds whether or not something is selected. Widening it on
         * selection was the first design and it was backwards: the neighbourhood arrives on
         * its own object above, so the main draw's job is unchanged context, and drawing
         * eight times more of it at the exact moment the camera is closest - when every line
         * spans more of the viewport - was the worst possible time to do it.
         */
        /*
         * A traced route draws almost no context.
         *
         * The route is the answer, and with the camera brought in to frame two subjects the
         * backbone is not structure any more - it is a wash of hairlines across the whole
         * viewport, each one crossing hundreds of pixels. Measured, it held four frames a
         * second. A thousand edges is enough to say the route runs through something rather
         * than through nothing; the steps themselves are on the overlay and unaffected.
         */
        /*
         * The budget holds whether or not something is selected - but it is scaled by how close
         * the camera is, which it was not.
         *
         * Holding the full 24,000 on selection was a deliberate choice and its reasoning was
         * sound as far as it went: the neighbourhood arrives on its own object, so the main
         * draw's job is unchanged context, and widening it at the moment the camera is closest
         * would be the worst possible time. That argued against widening. It never argued for
         * holding the whole budget, and measurement says the backbone is **77% of the frame** in
         * a selected 3D scene - 4.1 ms of 5.3 net of the empty-scene floor, against 1.2 ms for
         * the selection overlay and 0.1 ms for all 35,370 nodes. It was the dominant cost of the
         * view, hidden behind an argument about a different change.
         */
        const distance = this.camera.position.distanceTo(this.controls.target);
        const coverage = Math.min(1, (distance / EDGE_BUDGET_DISTANCE) ** 2);
        const base =
            this.focusActive || this.curatedNodes.length > 0
                ? FOCUS_EDGE_BUDGET
                : this.path.length > 1
                  ? PATH_EDGE_BUDGET
                  : Math.round(WORLD_EDGE_BUDGET * Math.max(0.05, coverage));
        const drawn = Math.min(semantic, this.edgeBudgetOverride ?? base);
        this.edges.geometry.setDrawRange(0, drawn * 2);
        this.drawnEdges = drawn;
    }

    /**
     * Re-read the palette after a theme change.
     *
     * Colours are baked into vertex attributes and into the clear colour, which is the right
     * thing for a scene drawn thirty-five thousand times a second and the wrong thing for a
     * scene that has to change theme. Before this the engine read its tokens once at mount
     * and never again, so switching to dark left a full-viewport ivory rectangle sitting
     * inside a carbon page with the DOM labels above it correctly re-themed - the canvas and
     * the page visibly disagreeing.
     *
     * Rewriting the buffers is cheap and happens on a human action, not on a frame: one pass
     * over the node colours, one over the edge colours, and two flags.
     */
    setPalette(palette: {
        groupColours: Float32Array;
        background: Color;
        edgeColour: Color;
        accentColour: Color;
    }) {
        this.groupColours = palette.groupColours;
        this.edgeBase = palette.edgeColour;
        this.accent = palette.accentColour;
        this.background = palette.background;

        this.renderer.setClearColor(palette.background, 1);
        this.scene.background = palette.background;

        const { nodeGroup, manifest } = this.world;
        for (let i = 0; i < manifest.counts.nodes; i += 1) {
            const group = nodeGroup[i];
            this.nodeColour[i * 3] = this.groupColours[group * 3];
            this.nodeColour[i * 3 + 1] = this.groupColours[group * 3 + 1];
            this.nodeColour[i * 3 + 2] = this.groupColours[group * 3 + 2];
        }
        for (let i = 0; i < manifest.counts.edges; i += 1) {
            for (let v = 0; v < 2; v += 1) {
                this.edgeColour[i * 6 + v * 3] = this.edgeBase.r;
                this.edgeColour[i * 6 + v * 3 + 1] = this.edgeBase.g;
                this.edgeColour[i * 6 + v * 3 + 2] = this.edgeBase.b;
            }
        }
        (this.selectionEdges.material as LineBasicMaterial).color.copy(this.accent);
        (this.nodes.geometry.getAttribute("aColour") as BufferAttribute).needsUpdate = true;
        (this.edges.geometry.getAttribute("aColour") as BufferAttribute).needsUpdate = true;
        this.applyDepthCues();
        /* The curated orbs carry their own copy of the colour, so a theme change has to reach
           them too. Cheap - at most 208 triples - and forgetting it would leave the one object
           the reader is actually looking at in the outgoing palette. */
        if (this.curatedNodes.length > 0) this.paintCurated();
    }

    /**
     * The depth cues that depend on the palette: aerial perspective, and the key light's sense.
     *
     * Both are re-derived from the page colour rather than configured, because both have to move
     * when the theme does and neither has a safe default. The fog ceiling is solved against the
     * 3:1 gate - see `fogCeiling` - and the key light is applied only towards the high-contrast
     * side of the page, so it can add form without ever spending contrast the palette does not
     * have.
     */
    private applyDepthCues() {
        const page = luminance(this.background.r, this.background.g, this.background.b);
        const light = page > 0.18;
        const apply = (material: ShaderMaterial, alpha: number) => {
            const u = material.uniforms;
            (u.uFog.value as Vector3).set(
                this.background.r,
                this.background.g,
                this.background.b,
            );
            u.uFogMax.value = fogCeiling(this.groupColours, this.background, alpha);
            (u.uKeyTint.value as Vector3).setScalar(light ? 0 : 1);
            u.uKeyShape.value = light ? 0 : 1;
        };
        apply(this.nodes.material as ShaderMaterial, NODE_ALPHA_REST);
        apply(this.curated.material as ShaderMaterial, NODE_ALPHA_CURATED);
    }

    /**
     * Stop drawing while this renderer is not the visible one.
     *
     * The spatial stage stays mounted across a renderer switch, because tearing down a WebGL
     * context would drop the camera, the buffers and a two-megabyte artifact with it. Staying
     * mounted is not the same as staying busy, though: leaving the loop running cost the
     * planar view a third of its frame rate on a laptop and rather more on a phone, since two
     * renderers were competing for one budget to draw one canvas.
     *
     * The loop keeps its rAF so that resuming is immediate; it simply does no work.
     */
    setPaused(paused: boolean) {
        if (paused === this.paused) return;
        this.paused = paused;
        if (paused) {
            /*
             * The frame is cancelled, not merely skipped.
             *
             * The loop used to reschedule itself before testing the flag, so a paused engine
             * still woke about sixty times a second to read a boolean and return. That is the
             * residual cost the homepage measured while its preview was scrolled off screen,
             * and it is the same shape as the bug this pause was introduced to fix: honoured
             * for drawing, not for scheduling.
             */
            cancelAnimationFrame(this.frame);
            this.frame = 0;
            return;
        }
        this.pickDirty = true;
        /* A pause is not a frame. Left alone, the first sample after resuming reports the whole
           idle period as one interval, and the HUD announces a forty-second frame. */
        this.lastFrame = 0;
        this.frameTimes = [];
        this.jsTimes = [];
        if (!this.disposed && this.frame === 0) this.frame = requestAnimationFrame(this.loop);
    }

    /**
     * Which semantic view this is, and now it changes what is drawn.
     *
     * This method existed and was called from nowhere, so the field it wrote was initialised to
     * WORLD and never moved: World and Focus rendered identically and "Focus" was a camera
     * position with some dimming over the whole corpus. Everything below this line is what it
     * should always have done.
     */
    setMode(mode: WorldMode) {
        if (mode === this.mode) return;
        this.mode = mode;
        this.applyLens();
        this.applySelection();
    }

    /**
     * A curated neighbourhood to draw, or null to stop drawing one.
     *
     * Pushed in rather than derived here. Choosing which of Indra's 5,544 neighbours are worth
     * drawing costs a millisecond or two and depends on relationship families, coverage rounds
     * and what was already on screen; it is memoised by the surface that owns the selection and
     * must never be reached from a frame. The engine takes the answer and draws it.
     */
    setFocus(scene: FocusScene | null) {
        this.focusScene = scene;
        this.applySelection();
    }

    /**
     * The lens and the reachable camera poses, which are properties of the mode.
     *
     * The polar clamp is not a comfort setting - it *is* the separation guarantee. A slab seen
     * from within its own plane has no guaranteed projected separation at all, for the reason
     * set out in `focus-layout.ts`, so the elevation band is the premise the bound is proved
     * from. Leaving the orbit free would make the arrangement a hope again.
     */
    private applyLens() {
        const focus = this.mode === "FOCUS";
        this.camera.fov = focus ? FOCUS_FOV : WORLD_FOV;
        this.camera.updateProjectionMatrix();
        this.controls.minPolarAngle = focus ? (90 - SLAB_ELEVATION.max) * DEG : 0;
        this.controls.maxPolarAngle = focus ? (90 - SLAB_ELEVATION.min) * DEG : Math.PI;
        this.controls.minDistance = focus ? FOCUS_DISTANCE * FOCUS_ZOOM_IN : 40;
        this.controls.maxDistance = focus ? FOCUS_DISTANCE * FOCUS_ZOOM_OUT : 6000;
        this.applyLevels();
        this.pickDirty = true;
    }

    /** The per-level size clamps, in framebuffer pixels, which is what `gl_PointSize` is in. */
    private applyLevels() {
        const dpr = this.renderer.getPixelRatio();
        const world = this.mode === "PATH" ? NODE_LEVELS.PATH : NODE_LEVELS.WORLD;
        const u = (this.nodes.material as ShaderMaterial).uniforms;
        u.uGamma.value = world.gamma;
        (u.uClamp.value as Vector2).set(world.minPx * dpr, world.maxPx * dpr);
        (u.uRootClamp.value as Vector2).set(world.minPx * dpr, world.maxPx * dpr);
        const c = (this.curated.material as ShaderMaterial).uniforms;
        c.uGamma.value = NODE_LEVELS.NEIGHBOUR.gamma;
        c.uRefDepth.value = FOCUS_DISTANCE;
        (c.uClamp.value as Vector2).set(
            NODE_LEVELS.NEIGHBOUR.minPx * dpr,
            NODE_LEVELS.NEIGHBOUR.maxPx * dpr,
        );
        (c.uRootClamp.value as Vector2).set(
            NODE_LEVELS.ROOT.minPx * dpr,
            NODE_LEVELS.ROOT.maxPx * dpr,
        );
    }

    /**
     * Emphasise a traced route.
     *
     * A path is a different kind of focus from a selection: a selection has a centre and a
     * ring around it, a path has a run of subjects and the specific steps between them. The
     * steps are drawn on the selection overlay, which already exists and is already the right
     * size, rather than by widening the world draw range to reach edges scattered through
     * 185,693 of them.
     */
    setPath(nodes: number[]) {
        this.path = nodes;
        this.applySelection();
    }

    /**
     * Show this subject as the selected one. A command, and silent.
     *
     * It does not raise `onTap`. A command that announces itself cannot be called by whoever
     * listens to the announcement, and the thing that owns the selection is exactly the thing
     * that needs to do both.
     */
    select(node: number | null) {
        if (node === this.selected) return;
        this.selected = node;
        this.applySelection();
    }

    /**
     * Draw a hovered subject's own connections, without selecting it.
     *
     * Before this, hovering changed nothing in the scene: it reported a node and drew no edges.
     * That was survivable while edges were anonymous and fatal once they carry names, because
     * the world draw range is a budget - 24,000 of 185,693 edges, sorted by structural
     * importance - so a given subject's connections are usually *not* among the lines on screen.
     * Naming edges that are not being drawn would put words next to whichever line happened to
     * pass underneath.
     *
     * So hovering now fills the same overlay a selection fills. The dimming is deliberately not
     * applied: a selection re-weights the whole world and that is too violent to happen under a
     * moving pointer. This adds lines and nothing else.
     */
    setEmphasis(node: number | null) {
        if (node === this.emphasis) return;
        this.emphasis = node;
        if (this.selected === null && this.path.length <= 1) this.updateSelectionEdges();
    }

    /**
     * The edges of a node that are actually on screen, in draw order.
     *
     * The selection overlay is a fixed buffer and truncates past its capacity, so a node with
     * more connections than that has some which are emphasised and some which are not. Anything
     * choosing edges to name has to choose from this, not from the full incident set, or it will
     * eventually label a line nobody can see.
     */
    drawnEdgesOf(node: number): Uint32Array {
        /* A curated scene knows exactly which of its subject's edges are drawn, and it is a
           small deliberate set rather than a prefix of a large accidental one. Reading the
           incident set here instead would name lines that were curated out. */
        if (this.focusScene && this.focusScene.root === node) {
            return Uint32Array.from(this.focusScene.spokes, (spoke) => spoke.edge);
        }
        const capacity = this.selectionPositions.length / 6;
        const touching = edgesOf(this.world, node);
        return touching.length <= capacity ? touching : touching.subarray(0, capacity);
    }

    /**
     * Selection, as emphasis rather than as isolation.
     *
     * Nothing is removed from the scene. The world stays where it is and recedes, the chosen
     * node's own edges come up, and its neighbours brighten. Deleting the rest would be
     * cheaper to draw and would destroy the one thing a spatial view is for: seeing where in
     * the whole the thing you picked actually sits.
     */
    private applySelection() {
        const count = this.world.manifest.counts.nodes;
        const focus = this.selected;

        /*
         * A curated Focus is composed rather than emphasised, and the two cannot be blended.
         *
         * Below this branch the whole graph stays drawn and is re-weighted. Above it, forty-one
         * orbs have been lifted onto a slab and the world is not drawn at all. Attempting both at
         * once was the first design and it produced the worst of each: a curated arrangement
         * behind a wash of everything it had been curated out of.
         */
        const wantFocus =
            this.mode === "FOCUS" &&
            this.focusScene !== null &&
            this.focusScene.root === focus &&
            this.focusScene.members.length > 0;
        if (wantFocus !== this.focusActive) {
            this.focusActive = wantFocus;
            if (wantFocus) this.composeFocus();
            this.beginStage(wantFocus ? "in" : "out");
        } else if (wantFocus) {
            this.composeFocus();
        }
        if (this.focusActive) {
            this.applyEdgeRange();
            this.updateSelectionEdges();
            this.drawnNodes = this.curatedNodes.length;
            return;
        }

        /*
         * Nothing here writes `edgeAlpha` any more, and that removal is a measured fix rather
         * than a tidy-up.
         *
         * Selecting anything used to rest all 185,693 edge weights and then raise the incident
         * ones, which is 0.7 ms of arithmetic and - worse - **1.48 MB of buffer re-uploaded to
         * the GPU on every selection, whatever was selected**. It is why `select()` cost 1.8 ms
         * at degree 1 and only 3.0 ms at degree 7,347: almost all of it was the fixed upload,
         * not the neighbour count. It also bought nothing, because the chosen subject's lines
         * are drawn on the selection overlay in the accent colour, so the raised weights were a
         * second, dimmer copy of the same emphasis underneath the first.
         *
         * The weights are therefore set once, in `buildEdges`, and never again.
         */
        if (this.path.length > 1) {
            const along = new Set(this.path);
            for (let i = 0; i < count; i += 1) this.nodeAlpha[i] = along.has(i) ? 1 : 0.06;
        } else if (focus === null) {
            for (let i = 0; i < count; i += 1) this.nodeAlpha[i] = NODE_ALPHA_REST;
        } else {
            /*
             * Dimmed to the curated set, not to everything the subject touches.
             *
             * Indra has 5,544 distinct neighbours. Brightening all of them was the letter of
             * "selection is emphasis" and the opposite of its purpose: a reader who picks the
             * busiest node in the corpus got one sixth of the graph lit at 0.96 and the rest at
             * 0.1, which is not a neighbourhood, it is a stain. Where a curated set exists it is
             * the emphasis; the incident set is the fallback for a subject nothing has curated
             * yet, and for that subject - median six neighbours - the two are the same thing.
             */
            const near = new Set<number>([focus]);
            if (this.focusScene && this.focusScene.root === focus) {
                for (const member of this.focusScene.members) near.add(member.node);
            } else {
                const touching = edgesOf(this.world, focus);
                for (let i = 0; i < touching.length; i += 1) {
                    near.add(otherEnd(this.world, touching[i], focus));
                }
            }
            for (let i = 0; i < count; i += 1) {
                this.nodeAlpha[i] = near.has(i) ? 0.96 : 0.1;
            }
        }

        this.drawnNodes = 0;
        for (let i = 0; i < count; i += 1) if (this.nodeAlpha[i] >= 0.14) this.drawnNodes += 1;

        this.applyEdgeRange();
        this.updateSelectionEdges();
        (this.nodes.geometry.getAttribute("aAlpha") as BufferAttribute).needsUpdate = true;
    }

    /* -------------------------------------------------------------- focus - */

    /**
     * How many world units one CSS pixel of the layout is worth, at the framing distance.
     *
     * The slab is laid out in pixels because the guarantee it carries is a pixel guarantee, and a
     * separation stated in world units says nothing about whether a reader can see two things as
     * two things. This is the one conversion, and it is the reason nothing downstream of the
     * layout has to know about the camera.
     */
    private slabScale() {
        const { height } = this.viewport();
        const perUnit = height / (2 * Math.tan((FOCUS_FOV * Math.PI) / 360) * FOCUS_DISTANCE);
        return perUnit > 0 ? 1 / perUnit : 1;
    }

    /**
     * Lay the curated set out on a slab anchored at the subject, and fill the curated buffers.
     *
     * The subject does not move. That is the whole reason the slab is anchored on it rather than
     * on the origin: a transition in which the thing the reader just chose stays put, and its
     * neighbours travel to arrange themselves around it, answers "where did that go" for every
     * mark on screen. Translating survivors beats rotating them for comprehension, and moving the
     * subject as well would have made the one fixed reference into another moving one.
     */
    private composeFocus() {
        const scene = this.focusScene;
        if (!scene) return;
        const { width, height } = this.viewport();
        const visibleWidth = Math.max(1, width - this.safeArea.left - this.safeArea.right);
        const visibleHeight = Math.max(1, height - this.safeArea.top - this.safeArea.bottom);
        /* The radius comes from the band a reader can actually see, not from the canvas. On a
           phone the canvas is the screen and is then covered by a sheet, and a slab sized to the
           canvas puts half of itself behind it. */
        const radius = slabRadiusFor(Math.min(visibleWidth, visibleHeight));
        const members: SlabMember[] = scene.members.map((member) => ({
            node: member.node,
            family: member.family,
        }));
        const slab = layoutFocusSlab(scene.root, members, {
            radius,
            spread: this.focusSpread,
        });
        this.focusSlab = slab;

        const scale = this.slabScale();
        const { positions, nodeDegree } = this.world;
        const root = scene.root;
        const ox = positions[root * 3];
        const oy = positions[root * 3 + 1];
        const oz = positions[root * 3 + 2];

        this.curatedNodes = [root, ...slab.placements.map((placement) => placement.node)];
        if (this.curatedNodes.length > CURATED_CAPACITY) {
            this.curatedNodes = this.curatedNodes.slice(0, CURATED_CAPACITY);
        }
        this.curatedSlot.clear();
        this.curatedNodes.forEach((node, slot) => this.curatedSlot.set(node, slot));

        const place = (slot: number, x: number, y: number, z: number) => {
            /* Where it starts is where it is *currently drawn*, not where the artifact says it
               is. Re-composing mid-flight - which a resize or a re-space does - must not snap
               anything back to a position it has already left. */
            const node = this.curatedNodes[slot];
            this.curatedFrom[slot * 3] = this.drawPositions[node * 3];
            this.curatedFrom[slot * 3 + 1] = this.drawPositions[node * 3 + 1];
            this.curatedFrom[slot * 3 + 2] = this.drawPositions[node * 3 + 2];
            this.curatedTo[slot * 3] = x;
            this.curatedTo[slot * 3 + 1] = y;
            this.curatedTo[slot * 3 + 2] = z;
        };

        place(0, ox, oy, oz);
        slab.placements.forEach((placement, index) => {
            const slot = index + 1;
            if (slot >= this.curatedNodes.length) return;
            /* In-plane (x, y) becomes world (x, z); the slab offset becomes world y, which is the
               axis the elevation clamp keeps the camera above. */
            place(
                slot,
                ox + placement.x * scale,
                oy + placement.z * scale,
                oz + placement.y * scale,
            );
        });

        for (let slot = 0; slot < this.curatedNodes.length; slot += 1) {
            const node = this.curatedNodes[slot];
            this.curatedSize[slot] = 9 + Math.cbrt(nodeDegree[node]) * 2.6;
            this.curatedAlpha[slot] = NODE_ALPHA_CURATED;
            this.curatedRoot[slot] = slot === 0 ? 1 : 0;
        }
        this.paintCurated();

        const world = radius * scale;
        const u = (this.curated.material as ShaderMaterial).uniforms;
        u.uFogNear.value = Math.max(1, FOCUS_DISTANCE - world);
        u.uFogFar.value = FOCUS_DISTANCE + world;
        this.curated.geometry.setDrawRange(0, this.curatedNodes.length);
        for (const attribute of ["aSize", "aAlpha", "aRoot"]) {
            (this.curated.geometry.getAttribute(attribute) as BufferAttribute).needsUpdate = true;
        }
        this.writeCuratedPositions(1);
    }

    /** Group colours for the curated slots. Separate from `composeFocus` so a theme change can
        re-run it without re-laying anything out. */
    private paintCurated() {
        const { nodeGroup } = this.world;
        for (let slot = 0; slot < this.curatedNodes.length; slot += 1) {
            const group = nodeGroup[this.curatedNodes[slot]];
            this.curatedColour[slot * 3] = this.groupColours[group * 3];
            this.curatedColour[slot * 3 + 1] = this.groupColours[group * 3 + 1];
            this.curatedColour[slot * 3 + 2] = this.groupColours[group * 3 + 2];
        }
        (this.curated.geometry.getAttribute("aColour") as BufferAttribute).needsUpdate = true;
    }

    /**
     * Move the curated set `travel` of the way to its seats, and publish the result.
     *
     * The draw buffer is written first and the compact curated buffer is copied out of it, rather
     * than the other way round, so that there is exactly one answer to "where is this node
     * drawn". Everything else in the class - the lines, the pick index, the label projection, the
     * camera framing - reads the draw buffer, so none of them can disagree with the picture.
     */
    private writeCuratedPositions(travel: number) {
        const total = this.curatedNodes.length;
        if (total === 0) return;
        /* The stagger runs over the neighbours, not over the subject, which does not travel. */
        const staggered = Math.max(1, total - 1);
        for (let slot = 0; slot < total; slot += 1) {
            const node = this.curatedNodes[slot];
            const t = slot === 0 ? 1 : itemWeight(travel, slot - 1, staggered);
            for (let axis = 0; axis < 3; axis += 1) {
                const from = this.curatedFrom[slot * 3 + axis];
                const to = this.curatedTo[slot * 3 + axis];
                const at = from + (to - from) * t;
                this.drawPositions[node * 3 + axis] = at;
                this.curatedPositions[slot * 3 + axis] = at;
            }
        }
        (this.curated.geometry.getAttribute("position") as BufferAttribute).needsUpdate = true;
        (this.nodes.geometry.getAttribute("position") as BufferAttribute).needsUpdate = true;
    }

    /** Put every curated node back where the artifact says it is, and stop drawing them. */
    private clearCurated() {
        const { positions } = this.world;
        for (const node of this.curatedNodes) {
            this.drawPositions[node * 3] = positions[node * 3];
            this.drawPositions[node * 3 + 1] = positions[node * 3 + 1];
            this.drawPositions[node * 3 + 2] = positions[node * 3 + 2];
        }
        if (this.curatedNodes.length > 0) {
            (this.nodes.geometry.getAttribute("position") as BufferAttribute).needsUpdate = true;
        }
        this.curatedNodes = [];
        this.curatedSlot.clear();
        this.focusSlab = null;
        this.curated.geometry.setDrawRange(0, 0);
        this.pickDirty = true;
        this.applyEdgeRange();
        this.updateSelectionEdges();
    }

    /**
     * Start a World <-> Focus transition, and fly the camera with it.
     *
     * Two stages of about a second, which is the arbitration's correction to a five-phase
     * design: heavy multi-stage animation was measured as *increasing* interpretation error, and
     * the source's own note on the five-stage case is that most subjects laughed at it. Stage A
     * is this camera flight plus the travel; stage B is the lines and then the names.
     */
    private beginStage(direction: TransitionDirection) {
        this.stage = { started: performance.now(), direction, scope: "full" };
        if (direction === "in" && this.focusScene) {
            this.flyToSlab(this.focusScene.root, STAGE_A_MS);
        }
        /* Applied once immediately so that the first frame of the transition is its own first
           frame rather than the last frame of the previous state. */
        this.tickStage(this.stage.started);
    }

    /**
     * Read the clock, and apply what it says.
     *
     * The weights come from a pure function of elapsed time, so reduced motion is one branch
     * inside it rather than a condition threaded through here, and the schedule can be tested
     * without a renderer or a frame.
     */
    private tickStage(now: number) {
        if (!this.stage) return;
        const elapsed = now - this.stage.started;
        const travelOnly = this.stage.scope === "travel";
        const weights = transitionWeights(elapsed, {
            direction: this.stage.direction,
            reducedMotion: this.reducedMotion,
        });
        this.weights = weights;

        if (!travelOnly) {
            (this.nodes.material as ShaderMaterial).uniforms.uAlpha.value = weights.context;
            (this.selectionEdges.material as LineBasicMaterial).opacity = 0.75 * weights.edges;
        }
        if (this.curatedNodes.length > 0) {
            this.writeCuratedPositions(weights.travel);
            this.updateSelectionEdges();
        }
        this.pickDirty = true;

        /* A travel-only stage is over when the geometry stops, which is the end of stage A. The
           rest of the schedule is lines and names, and neither of them is changing. */
        if (travelOnly ? elapsed < STAGE_A_MS : weights.running) return;
        const finished = this.stage.direction;
        this.stage = null;
        if (finished === "out" && !travelOnly) {
            this.clearCurated();
            (this.nodes.material as ShaderMaterial).uniforms.uAlpha.value = 1;
            (this.selectionEdges.material as LineBasicMaterial).opacity = 0.75;
        }
    }

    /**
     * Re-space the current neighbourhood: the same subjects, further apart.
     *
     * A trade rather than a loosening, and the thing being traded is node-to-spoke overlap. The
     * layout normally takes the fewest rings whose guarantee clears the floor, because a
     * single-ring arrangement has no spoke passing any node at all; this takes whichever ring
     * count has the *largest* guaranteed separation instead. Measured on a desktop canvas that is
     * 42 px to 66 px at twenty-four orbs and 44 px to 51 px at forty.
     *
     * It cannot break the invariant, and not by being careful: both arrangements are drawn from
     * the same family of ring constructions, each with its own proven bound, and this picks the
     * larger of the two. The bound does not have to be clamped because it only ever improves.
     *
     * It also cannot widen the set. There is no path from here to a neighbour that was not
     * already shown - that is a different control, and conflating the two is what made the
     * previous button claim to pull connections apart while actually changing renderer.
     *
     * `slabSpreadGain` is 1 for twelve orbs and fewer, which is nine subjects in ten. A control
     * offering this should read that first and disable itself rather than animate a scene into
     * the arrangement it is already in.
     */
    respaceFocus() {
        if (!this.focusActive || !this.focusScene) return;
        this.focusSpread = this.focusSpread === "compact" ? "wide" : "compact";
        this.composeFocus();
        /* A nudge to an existing arrangement, not a third stage: the orbs travel to new seats and
           nothing else changes, so it borrows stage A's travel curve and none of the rest. */
        if (this.reducedMotion) {
            this.writeCuratedPositions(1);
            this.updateSelectionEdges();
            this.stage = null;
            return;
        }
        this.stage = { started: performance.now(), direction: "in", scope: "travel" };
        this.tickStage(this.stage.started);
    }

    /**
     * Take hold of one curated orb, and let its neighbours resist.
     *
     * ## Why a simulation rather than a lerp
     *
     * Because a lerp is what a picture does and this is what an object does. The planar view's
     * whole claim is that taking hold of a subject and feeling its neighbours resist is worth
     * more than a tidy arrangement, and that claim does not stop being true in three dimensions.
     * The simulation is `local-physics.ts` with `dims: 3` - the same tuned, measured loop the 2D
     * view runs, not a second copy of it. A copy is how this codebase previously ended up with
     * two disagreeing implementations of one rule, twice.
     *
     * ## Why the slab survives being pulled about
     *
     * The slab seats become anchors and `slack` bounds how far a body may leave one. That is what
     * keeps the separation guarantee a guarantee: the floor after a drag is `spacing - 2 * slack`
     * rather than whatever the tuning happens to balance at, because the clamp is applied to the
     * position and not added to the forces. At `DRAG_SLACK` the bound retains 76% of its settled
     * value, which is stated here so that raising the slack is visibly a decision about the
     * guarantee rather than about how loose the drag feels.
     *
     * ## What drives it
     *
     * `offerGrab` / `moveGrab` / `releaseGrab`, from the three grab handlers `installGestures`
     * raises. The discrimination between a drag on a node and a drag that is an orbit lives in
     * that file, which owns the pointer precisely because three consumers previously answered it
     * separately and two of the answers were wrong. `controls.enabled` is turned off in
     * `offerGrab` rather than here, because it has to be off before the camera has moved and this
     * function does not run until the press has travelled - see the note there.
     */
    beginNodeDrag(node: number): boolean {
        if (!this.focusActive || !this.focusSlab) return false;
        const slot = this.curatedSlot.get(node);
        if (slot === undefined) return false;

        const scene = this.focusScene;
        if (!scene) return false;
        const lines = scene.spokes.length + scene.between.length;
        const field = createField({
            dims: 3,
            count: this.curatedNodes.length,
            edges: lines,
            /* No centre pull and no shell. The arrangement is held by its anchors, and a centre
               pull in three dimensions collapses a slab towards a ball - which is the shape the
               arbitration measured as having no projected-separation guarantee at all. */
            tuning: tuningFor(3, { centrePull: 0, shell: null }),
        });
        const scale = this.slabScale();
        const slackWorld = this.focusSlab.spacing * scale * DRAG_SLACK;
        for (let i = 0; i < this.curatedNodes.length; i += 1) {
            const index = this.curatedNodes[i];
            for (let d = 0; d < 3; d += 1) {
                field.pos[i * 3 + d] = this.drawPositions[index * 3 + d];
                field.anchor[i * 3 + d] = this.curatedTo[i * 3 + d];
            }
            field.mass[i] = 1 + Math.cbrt(this.world.nodeDegree[index]) * 0.5;
            field.radius[i] = (i === 0 ? 20 : 13) * scale;
            field.seed[i] = index;
            field.slack[i] = slackWorld;
        }
        let at = 0;
        const join = (a: number, b: number) => {
            const ai = this.curatedSlot.get(a);
            const bi = this.curatedSlot.get(b);
            if (ai === undefined || bi === undefined || at >= lines) return;
            field.edgeA[at] = ai;
            field.edgeB[at] = bi;
            let d2 = 0;
            for (let d = 0; d < 3; d += 1) {
                const step = field.pos[ai * 3 + d] - field.pos[bi * 3 + d];
                d2 += step * step;
            }
            /* Rest length is the settled length, so the springs agree with the arrangement they
               were given instead of dragging it back towards a knot. */
            field.edgeRest[at] = Math.sqrt(d2);
            at += 1;
        };
        for (const spoke of scene.spokes) join(scene.root, spoke.node);
        for (const edge of scene.between) join(edge.a, edge.b);

        field.held[slot] = 1;
        this.field = field;
        this.heldSlot = slot;
        this.controls.enabled = false;
        return true;
    }

    /**
     * Move the held orb to where the pointer is, in the slab's own plane.
     *
     * The pointer is a ray and the orb is a point, so something has to supply the missing
     * dimension. The slab plane does: it is the surface the arrangement lives on and the one a
     * reader is looking at, so dragging along it is the motion they think they are making.
     * Dragging along the camera's own plane instead would push orbs through the slab and out of
     * the elevation band the guarantee is proved in.
     */
    dragNodeTo(x: number, y: number) {
        const field = this.field;
        if (!field || this.heldSlot === null || !this.focusScene) return;
        const { width, height } = this.viewport();
        if (!width || !height) return;
        const root = this.focusScene.root;
        const plane = this.world.positions[root * 3 + 1];
        const ray = new Vector3(
            (x / width) * 2 - 1,
            -(y / height) * 2 + 1,
            0.5,
        ).unproject(this.camera);
        ray.sub(this.camera.position);
        if (Math.abs(ray.y) < 1e-6) return;
        const t = (plane - this.camera.position.y) / ray.y;
        if (t <= 0) return;
        const slot = this.heldSlot;
        field.pos[slot * 3] = this.camera.position.x + ray.x * t;
        field.pos[slot * 3 + 1] = plane;
        field.pos[slot * 3 + 2] = this.camera.position.z + ray.z * t;
    }

    /** Let go. The orb drifts back to its seat; the field sleeps and is dropped. */
    endNodeDrag() {
        if (this.heldSlot !== null && this.field) this.field.held[this.heldSlot] = 0;
        this.heldSlot = null;
        this.controls.enabled = true;
    }

    /**
     * A press landed here. Is there an orb under it to take hold of?
     *
     * ## Why the camera is stopped on the press and not on the first move
     *
     * Because by the first move it is too late. `OrbitControls` is constructed before
     * `installGestures`, so its own `pointerdown` listener runs first and has already recorded a
     * rotation start and captured the pointer by the time this is asked. Waiting for the gesture
     * to be *recognisable* as a drag - four pixels for a mouse, ten for a finger - means those
     * first pixels orbit the camera and the orb then starts moving from a scene that has already
     * turned under it. Disabling here costs nothing that is wanted: `OrbitControls` checks
     * `enabled` again in its move handler, so the rotation it prepared never advances, while the
     * capture it took stays in place and keeps delivering moves after the pointer leaves the
     * canvas - which a drag towards the edge needs.
     *
     * The physics is not started here, though. A press that never travels is a selection, and
     * building a field for it would seed a relaxation over the whole neighbourhood on every tap:
     * the orbs are seeded from their drawn positions and anchored to their seats, and during a
     * transition those two differ, so a tap mid-flight would visibly nudge the arrangement. So
     * the node is remembered and `beginNodeDrag` waits for travel.
     *
     * Only a curated orb answers. In WORLD there are 35,370 of them at two pixels across, none
     * of them has an anchor to be pulled away from, and a reader there is navigating rather than
     * handling anything.
     */
    private offerGrab(node: number | null): boolean {
        if (node === null || !this.focusActive || !this.focusSlab) return false;
        if (!this.curatedSlot.has(node)) return false;
        this.pendingGrab = node;
        this.controls.enabled = false;
        return true;
    }

    /** The press has travelled. Promote it to a hold on the first call, then track the pointer. */
    private moveGrab(x: number, y: number) {
        if (this.heldSlot === null) {
            const node = this.pendingGrab;
            /* A refusal is not an error - the scene can have been replaced between the press and
               the move - but it must hand the camera back rather than leave the view inert. */
            if (node === null || !this.beginNodeDrag(node)) {
                this.releaseGrab();
                return;
            }
        }
        this.dragNodeTo(x, y);
    }

    /** Whatever the press turned out to be, the camera comes back and nothing stays held. */
    private releaseGrab() {
        this.pendingGrab = null;
        if (this.heldSlot !== null) this.endNodeDrag();
        else this.controls.enabled = true;
    }

    /** One physics step, and the write-back. Returns false once the field has gone to sleep. */
    private tickField() {
        const field = this.field;
        if (!field) return false;
        const energy = stepField(field);
        for (let i = 0; i < this.curatedNodes.length; i += 1) {
            const node = this.curatedNodes[i];
            for (let d = 0; d < 3; d += 1) {
                this.drawPositions[node * 3 + d] = field.pos[i * 3 + d];
                this.curatedPositions[i * 3 + d] = field.pos[i * 3 + d];
            }
        }
        (this.curated.geometry.getAttribute("position") as BufferAttribute).needsUpdate = true;
        (this.nodes.geometry.getAttribute("position") as BufferAttribute).needsUpdate = true;
        this.updateSelectionEdges();
        this.pickDirty = true;
        if (this.heldSlot === null && fieldAtRest(field, energy)) {
            this.field = null;
            /* The settled positions become the seats, so a second drag starts from what the
               reader is looking at rather than from an arrangement they have already changed. */
            this.curatedFrom.set(this.curatedTo);
            return false;
        }
        return true;
    }

    /** Whether `respaceFocus` would change anything, as a ratio of guaranteed separation. */
    canRespaceFocus() {
        if (!this.focusSlab || !this.focusScene) return 1;
        return slabSpreadGain(this.focusScene.members.length, this.focusSlab.radius);
    }

    /** The slab as laid out, for the benchmark and the report. Null outside a curated Focus. */
    get focusGeometry(): FocusSlab | null {
        return this.focusSlab;
    }

    /** How present names should be, from the transition clock. 1 when nothing is in flight. */
    get labelOpacity() {
        return this.weights?.labels ?? 1;
    }

    /**
     * Whether the geometry has stopped moving.
     *
     * The one thing a label layout may wait on. Placement against moving geometry is placement
     * against a position that will not exist by the time it lands, and this goes true at the end
     * of stage A rather than at the end of the whole transition - the names are still crossfading
     * after it, and waiting for that would delay placement by the length of its own fade.
     */
    get isSettled() {
        return this.weights ? this.weights.settled : true;
    }

    /* ----------------------------------------------------------- picking - */

    /**
     * Screen-space bucket picking.
     *
     * Three's raycast against a large object is a linear scan, and at 35,370 nodes that is a
     * full pass per pointer move. Instead every node is projected once when the camera
     * settles and dropped into a coarse pixel bucket; a hover then reads one bucket and its
     * eight neighbours. The cost of a hover stops depending on the size of the graph.
     */
    private rebuildPickIndex() {
        const count = this.world.manifest.counts.nodes;
        const positions = this.drawPositions;
        const width = this.renderer.domElement.clientWidth;
        const height = this.renderer.domElement.clientHeight;
        this.pickBuckets.clear();
        const v = new Vector3();
        /* The same multiplier the shader applies, so "drawn" here means the same thing it means
           on screen. Without it a Focus scene had no hit targets at all: the world alpha is zero
           there, and every curated orb is a world node too. */
        const worldAlpha = (this.nodes.material as ShaderMaterial).uniforms.uAlpha.value as number;
        for (let i = 0; i < count; i += 1) {
            if (this.nodeAlpha[i] * worldAlpha < 0.14 && !this.curatedSlot.has(i)) {
                this.projected[i * 3 + 2] = 2;
                continue;
            }
            v.set(positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]).project(
                this.camera,
            );
            this.projected[i * 3 + 2] = v.z;
            if (v.z > 1 || v.z < -1) continue;
            const x = (v.x * 0.5 + 0.5) * width;
            const y = (-v.y * 0.5 + 0.5) * height;
            this.projected[i * 3] = x;
            this.projected[i * 3 + 1] = y;
            const key = (Math.floor(x / this.pickCell) << 16) ^ Math.floor(y / this.pickCell);
            const bucket = this.pickBuckets.get(key);
            if (bucket) bucket.push(i);
            else this.pickBuckets.set(key, [i]);
        }
        this.pickDirty = false;
    }

    /** The node under a client-space point, or null. Nearest wins, then closest to camera. */
    pick(x: number, y: number): number | null {
        if (this.pickDirty) this.rebuildPickIndex();
        const cx = Math.floor(x / this.pickCell);
        const cy = Math.floor(y / this.pickCell);
        let best: number | null = null;
        let bestScore = Infinity;
        for (let ox = -1; ox <= 1; ox += 1) {
            for (let oy = -1; oy <= 1; oy += 1) {
                const bucket = this.pickBuckets.get(((cx + ox) << 16) ^ (cy + oy));
                if (!bucket) continue;
                for (const i of bucket) {
                    const dx = this.projected[i * 3] - x;
                    const dy = this.projected[i * 3 + 1] - y;
                    const d2 = dx * dx + dy * dy;
                    /*
                     * A generous radius on the busiest nodes, which are also the largest - and a
                     * flat, larger one on a curated orb, which is drawn at 9 to 26 CSS px rather
                     * than at 2 to 4. 17 px is under half the guaranteed separation, so no point
                     * can be inside two orbs' targets at once.
                     */
                    const radius = this.curatedSlot.has(i)
                        ? 17
                        : 6 + Math.cbrt(this.world.nodeDegree[i]) * 1.6;
                    if (d2 > radius * radius) continue;
                    const score = d2 + this.projected[i * 3 + 2] * 40;
                    if (score < bestScore) {
                        bestScore = score;
                        best = i;
                    }
                }
            }
        }
        return best;
    }

    hover(x: number, y: number) {
        const node = this.pick(x, y);
        if (node !== this.hovered) {
            this.hovered = node;
            this.events.onHover?.(node);
        }
        return node;
    }

    /* ------------------------------------------------------------- labels - */

    /** The canvas size in CSS pixels, which is the space label layout works in. */
    viewport(): { width: number; height: number } {
        return {
            width: this.renderer.domElement.clientWidth,
            height: this.renderer.domElement.clientHeight,
        };
    }

    /**
     * Where to write a word on each of these connections.
     *
     * `segments` is pairs of node indices, flat - the same shape the selection edges are built
     * from, so a label always lands on a line that is actually drawn. For each pair this writes
     * `usable`, then an x and a y for every fraction in `LABEL_FRACTIONS`, and returns `out`.
     *
     * Projected fresh rather than read from the pick index. That index holds every node and is
     * rebuilt only when the camera settles, which is correct for hovering and useless here: a
     * label has to stay on its line *during* an orbit, not snap to it afterwards. Sixteen
     * labels is thirty-two `project` calls a frame against 35,370, so doing it properly costs
     * nothing.
     *
     * The interpolation happens in screen space, after projecting both ends, rather than in
     * world space before it. Those give different points under perspective, and the one that
     * matters is a point on the line the reader can actually see.
     *
     * A pair with either end outside the depth range is marked unusable rather than clamped.
     * Interpolating between a point in front of the camera and one behind it produces a
     * confident position that is nowhere near the line, so the only safe answer is silence.
     */
    projectSegmentPoints(segments: ArrayLike<number>, out?: Float32Array): Float32Array {
        const pairs = segments.length >> 1;
        const needed = pairs * LABEL_STRIDE;
        const result = out && out.length >= needed ? out : new Float32Array(needed);
        const positions = this.drawPositions;
        const { width, height } = this.viewport();
        const a = new Vector3();
        const b = new Vector3();

        for (let i = 0; i < pairs; i += 1) {
            const na = segments[i * 2];
            const nb = segments[i * 2 + 1];
            a.set(positions[na * 3], positions[na * 3 + 1], positions[na * 3 + 2]).project(
                this.camera,
            );
            b.set(positions[nb * 3], positions[nb * 3 + 1], positions[nb * 3 + 2]).project(
                this.camera,
            );
            const base = i * LABEL_STRIDE;
            result[base] = a.z >= -1 && a.z <= 1 && b.z >= -1 && b.z <= 1 ? 1 : 0;

            const ax = (a.x * 0.5 + 0.5) * width;
            const ay = (-a.y * 0.5 + 0.5) * height;
            const bx = (b.x * 0.5 + 0.5) * width;
            const by = (-b.y * 0.5 + 0.5) * height;
            for (let f = 0; f < LABEL_FRACTIONS.length; f += 1) {
                const t = LABEL_FRACTIONS[f];
                result[base + 1 + f * 2] = ax + (bx - ax) * t;
                result[base + 2 + f * 2] = ay + (by - ay) * t;
            }
        }

        return result;
    }

    /**
     * Which part of the canvas is actually visible.
     *
     * On a phone the canvas fills the screen and is then covered: a band of chrome at the top and
     * a sheet at the bottom. Measured, the largest unbroken strip of visible canvas down the
     * centre line was 122 pixels of 780 - and `focusNode` flies the chosen subject to the
     * geometric centre, which sat underneath the sheet describing it.
     *
     * The fix is a lens shift, not a change to any of the framing code. `setViewOffset` with the
     * full size equal to the real size scales the frustum by one and only translates it, so this
     * moves what the centre of the screen means without zooming, cropping or moving the orbit
     * pivot. Moving `controls.target` instead would have put the pivot off the subject, and
     * orbiting would then swing it around a point beside itself.
     *
     * `focusNode`, `fitNodes` and `fitWorld` need no knowledge of this: they keep aiming at the
     * true centre and inherit the shift. Picking is unaffected for the same reason - the pick
     * index projects through this same matrix.
     */
    setSafeArea(area: { top?: number; right?: number; bottom?: number; left?: number }) {
        const next = {
            top: Math.max(0, area.top ?? 0),
            right: Math.max(0, area.right ?? 0),
            bottom: Math.max(0, area.bottom ?? 0),
            left: Math.max(0, area.left ?? 0),
        };
        const same =
            next.top === this.safeArea.top &&
            next.right === this.safeArea.right &&
            next.bottom === this.safeArea.bottom &&
            next.left === this.safeArea.left;
        if (same) return;
        this.safeArea = next;
        this.applySafeArea();
    }

    private applySafeArea() {
        const { width, height } = this.viewport();
        if (width <= 0 || height <= 0) return;
        const { top, right, bottom, left } = this.safeArea;

        /*
         * An impossible band is clamped to the largest feasible shift, not abandoned.
         *
         * It used to call `clearViewOffset` - so where the visible strip was narrower than this,
         * the camera went back to centring the subject in the *whole* canvas. Worked through on
         * the measured phone case that is the worst possible answer: a 684 px sheet over a 780 px
         * canvas leaves a 96 px strip, which is under the minimum, so the shift was dropped and
         * the subject was flown to y = 390 - dead centre, under 684 px of sheet, invisible. With
         * the centre clamped instead it lands at y = 60, inside the 96 px the reader can see.
         *
         * A band narrower than this is still not somewhere a subject can be *read*, which is what
         * the minimum is for; it is the difference between "as close as this can get" and
         * "nowhere near", and the first is worth having.
         */
        const MIN_BAND = 120;
        const visibleWidth = width - left - right;
        const visibleHeight = height - top - bottom;
        const clampCentre = (chrome: number, visible: number, total: number) => {
            const wanted = chrome + visible / 2;
            if (total <= MIN_BAND) return total / 2;
            return Math.max(MIN_BAND / 2, Math.min(total - MIN_BAND / 2, wanted));
        };

        const centreX = clampCentre(left, visibleWidth, width);
        const centreY = clampCentre(top, visibleHeight, height);
        if (Math.abs(centreX - width / 2) < 1 && Math.abs(centreY - height / 2) < 1) {
            this.camera.clearViewOffset();
        } else {
            this.camera.setViewOffset(
                width,
                height,
                width / 2 - centreX,
                height / 2 - centreY,
                width,
                height,
            );
        }
        this.pickDirty = true;
    }

    /* ------------------------------------------------------------ camera - */

    /** Where a node is *drawn*. Never the artifact's own array; see `drawPositions`. */
    private positionOf(node: number) {
        return new Vector3(
            this.drawPositions[node * 3],
            this.drawPositions[node * 3 + 1],
            this.drawPositions[node * 3 + 2],
        );
    }

    /** Frame the whole world. See `WORLD_DISTANCE` for where the number came from. */
    fitWorld(ms = 900) {
        this.flyTo(new Vector3(0, 0, WORLD_DISTANCE), new Vector3(0, 0, 0), ms);
    }

    /**
     * Frame a node and its neighbours.
     *
     * The distance comes from the spread of the neighbourhood rather than from a constant, so
     * a deity with four thousand edges and a verse with three both arrive at a readable size.
     */
    focusNode(node: number, ms = 1000) {
        /*
         * Inside Focus the slab pose is the framing, so this defers to it rather than computing
         * a second answer.
         *
         * It has to be the same answer rather than merely a sensible one. The selection arrives
         * before the curated set does - they are separate effects, and the curation costs a
         * millisecond or two - so without this the camera flew once to a distance derived from
         * the *world* spread of the neighbourhood and then again to the slab, which reads as a
         * lurch. Both paths now fly to the same place, so the second flight is a no-op.
         */
        if (this.mode === "FOCUS") {
            this.flyToSlab(node, ms);
            return;
        }
        const centre = this.positionOf(node);
        const touching = edgesOf(this.world, node);
        let radius = 60;
        for (let i = 0; i < touching.length; i += 1) {
            const other = this.positionOf(otherEnd(this.world, touching[i], node));
            radius = Math.max(radius, centre.distanceTo(other));
        }
        const distance = Math.min(2400, Math.max(120, radius * 2.1));
        const direction = this.camera.position.clone().sub(this.controls.target);
        if (direction.lengthSq() < 1) direction.set(0, 0, 1);
        direction.normalize().multiplyScalar(distance);
        this.flyTo(centre.clone().add(direction), centre, ms);
    }

    /**
     * Frame an arbitrary set of nodes, used for a path and for the homepage preview.
     *
     * `spread` and `floor` are exposed because the defaults are the path's. A route across the
     * corpus needs to be framed loosely and from far enough out that the camera is not inside
     * the cloud; a fifty-node preview in a small panel needs neither, and inheriting both left
     * it a scatter of dots in the middle of an empty frame.
     */
    fitNodes(nodeIds: number[], ms = 900, { spread = 2.6, floor = 700 } = {}) {
        if (!nodeIds.length) return;
        const centre = new Vector3();
        for (const id of nodeIds) centre.add(this.positionOf(id));
        centre.divideScalar(nodeIds.length);
        let radius = 60;
        for (const id of nodeIds) radius = Math.max(radius, centre.distanceTo(this.positionOf(id)));
        const direction = this.camera.position.clone().sub(this.controls.target);
        if (direction.lengthSq() < 1) direction.set(0, 0, 1);
        /* The floor exists because framing two subjects that happen to be close together would
           otherwise put the camera inside the cloud, where every edge crosses the viewport and
           nothing is legible however well it is framed. */
        direction.normalize().multiplyScalar(Math.min(3200, Math.max(floor, radius * spread)));
        this.flyTo(centre.clone().add(direction), centre, ms);
    }

    /**
     * The pose a slab is read from: a fixed distance, above the plane, and off both axes.
     *
     * Diagonal on purpose. An axis-aligned arrival reads as a diagram rather than as a place and
     * users reject it, and it is also the one pose from which the slab's thickness conveys
     * nothing at all - looking straight down a plane's normal flattens it exactly.
     */
    private flyToSlab(node: number, ms: number) {
        const centre = this.positionOf(node);
        const azimuth = SLAB_AZIMUTH_DEFAULT * DEG;
        const elevation = SLAB_ELEVATION.default * DEG;
        this.flyTo(
            centre
                .clone()
                .add(
                    new Vector3(
                        Math.cos(elevation) * Math.cos(azimuth),
                        Math.sin(elevation),
                        Math.cos(elevation) * Math.sin(azimuth),
                    ).multiplyScalar(FOCUS_DISTANCE),
                ),
            centre,
            ms,
        );
    }

    private flyTo(to: Vector3, target: Vector3, ms: number) {
        if (this.reducedMotion || ms <= 0) {
            this.camera.position.copy(to);
            this.controls.target.copy(target);
            this.controls.update();
            this.pickDirty = true;
            return;
        }
        this.flight = {
            from: this.camera.position.clone(),
            to,
            fromTarget: this.controls.target.clone(),
            toTarget: target,
            started: performance.now(),
            ms,
        };
    }

    /* -------------------------------------------------------------- loop - */

    private tickFlight(now: number) {
        if (!this.flight) return;
        const t = Math.min(1, (now - this.flight.started) / this.flight.ms);
        // Cubic ease-out: quick departure, soft arrival, no overshoot to fight the controls.
        const e = 1 - (1 - t) ** 3;
        this.camera.position.lerpVectors(this.flight.from, this.flight.to, e);
        this.controls.target.lerpVectors(this.flight.fromTarget, this.flight.toTarget, e);
        this.pickDirty = true;
        if (t >= 1) this.flight = null;
    }

    /**
     * The frame loop, as a bound field rather than a local.
     *
     * `setPaused` has to be able to schedule it again after cancelling it, so it cannot be a
     * closure inside `start`.
     */
    private readonly loop = () => {
        if (this.disposed) {
            this.frame = 0;
            return;
        }
        this.frame = requestAnimationFrame(this.loop);
        /* Belt and braces for the one frame that may already be queued when the pause lands.
           `setPaused` cancels the pending frame; this catches the race if it does not. */
        if (this.paused) return;
        const began = performance.now();
        /* Dropped before any work is done, not after: the point is to skip the frame, and the
           stats below deliberately do not count a frame that was never drawn. */
        if (this.frameInterval > 0 && began - this.lastDrawn < this.frameInterval - 1) return;
        this.lastDrawn = began;
        this.tickFlight(began);
        this.tickStage(began);
        /* After the transition, never before: a field seeded mid-flight would be relaxing towards
           seats the transition is still moving it to. */
        if (this.field && (!this.weights || !this.weights.running)) this.tickField();
        this.controls.update();
        /*
         * Point size is in *framebuffer* pixels, so this has to be the framebuffer height.
         *
         * It was the CSS height, which made every node in the product 1/DPR of the size the
         * sizing rule asks for - a third smaller on a desktop at the capped ratio, and the reason
         * an unconnected node measured 1.3 CSS px where the arithmetic said 2. The bug was
         * invisible as a bug because the picture merely looked a bit thin, and it was doubly
         * invisible in the numbers: every measurement of "node CSS diameter" taken off the sizing
         * formula was really a framebuffer figure, so the formula and the screen disagreed by
         * exactly the ratio nobody was multiplying by.
         *
         * It tracks the field of view as well as the height, which now matters rather than being
         * defensive: Focus draws through a 34-degree lens and the world through 52.
         */
        const scale =
            (this.renderer.domElement.clientHeight * this.renderer.getPixelRatio()) /
            (2 * Math.tan((this.camera.fov * Math.PI) / 360));
        (this.nodes.material as ShaderMaterial).uniforms.uScale.value = scale;
        (this.curated.material as ShaderMaterial).uniforms.uScale.value = scale;
        /* The budget is a function of camera distance, so it is re-read per frame rather than per
           selection. Setting a draw range is a property write; measuring the alternative is what
           produced the number in the comment on EDGE_BUDGET_DISTANCE. */
        this.applyEdgeRange();
        /*
         * A fully faded world is not submitted at all.
         *
         * `discard` in the fragment shader saves the fill but still pays the vertex stage for
         * 35,370 points and the draw call for 24,000 lines. Measured at 0.7 ms for the node cloud
         * alone, which is worth having back in a scene whose whole budget is 5.9 ms.
         */
        const worldAlpha = (this.nodes.material as ShaderMaterial).uniforms.uAlpha.value as number;
        this.nodes.visible = worldAlpha > 0.002;
        this.edges.visible = this.drawnEdges > 0 && worldAlpha > 0.002;
        this.renderer.render(this.scene, this.camera);
        /* Read straight after the render, which is the only moment it is this frame's number:
           three resets `info` at the start of every `render`. */
        const info = this.renderer.info.render;
        this.drawnNodes = info.points;
        this.drawnEdges = info.lines;
        this.drawn += 1;
        /* After the render, never before it. `renderer.render` is what refreshes the camera's
           `matrixWorldInverse`, and a projection taken ahead of it is computed from the
           previous frame's camera - so anything positioned from it trails the lines it is
           meant to sit on by exactly one frame, which reads as lag during an orbit and is
           invisible when still. */
        this.events.onFrame?.();
        this.sample(began);
    };

    /** Idempotent: a second call must not leave two loops running against one canvas. */
    start() {
        if (this.frame !== 0 || this.disposed) return;
        this.frame = requestAnimationFrame(this.loop);
    }

    /**
     * Frame cost, measured between frames rather than inside one.
     *
     * The obvious thing to time is the work this class does: start a clock, render, stop it.
     * That number is meaningless as a frame time. `renderer.render` returns as soon as the
     * commands are queued, so it excludes everything the GPU then does and everything spent
     * waiting for the display, and the first version of this reported 1,667 fps at 0.6 ms
     * while drawing 35,370 nodes in a software rasteriser. What a reader of these numbers
     * wants is how long a frame actually took, which is the gap between one rAF callback and
     * the next; the JS half is kept separately because when the two diverge, the difference
     * is where the cost is.
     */
    private sample(began: number) {
        const jsCost = performance.now() - began;
        this.jsTimes.push(jsCost);
        if (this.lastFrame > 0) this.frameTimes.push(began - this.lastFrame);
        this.lastFrame = began;

        if (began - this.lastStats < 1000 || this.frameTimes.length < 2) return;
        const sorted = [...this.frameTimes].sort((a, b) => a - b);
        const mean = sorted.reduce((a, b) => a + b, 0) / sorted.length;
        const jsMean = this.jsTimes.reduce((a, b) => a + b, 0) / this.jsTimes.length;
        this.events.onStats?.({
            fps: Math.round(1000 / Math.max(mean, 0.001)),
            frameMs: Number(mean.toFixed(2)),
            p95Ms: Number(sorted[Math.floor(sorted.length * 0.95)].toFixed(2)),
            jsMs: Number(jsMean.toFixed(2)),
            /*
             * What the renderer actually submitted, not the size of the artifact.
             *
             * This was `manifest.counts.nodes` - a constant - and it is printed to readers in the
             * status line under the canvas. So the one number on screen that could confirm a
             * curated Focus is drawing forty-one orbs instead of 35,370 was structurally
             * incapable of ever saying so, whatever the renderer did.
             */
            drawnNodes: this.drawnNodes,
            drawnEdges: this.drawnEdges,
        });
        this.frameTimes = [];
        this.jsTimes = [];
        this.lastStats = began;
    }

    /**
     * Override the world edge budget, for the benchmark sweep.
     *
     * The constant above has to come from a measurement on real hardware, and a measurement
     * needs a way to vary the thing it is measuring. This is that way and it has no other
     * caller; passing null restores the constant.
     */
    setEdgeBudgetOverride(value: number | null) {
        this.edgeBudgetOverride = value;
        this.applyEdgeRange();
    }

    resize() {
        const canvas = this.renderer.domElement;
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        if (!width || !height) return;
        /*
         * The ratio is re-read here, which it never was.
         *
         * `setPixelRatio` appeared exactly once in this file, in the constructor, so the ratio was
         * decided from the canvas size at mount and then kept for the life of the context. A phone
         * rotating, a window being dragged wider, or a window moving between a 1x and a 2x monitor
         * all left it stale - and since the ratio is now derived from the canvas *area*, a stale
         * one is a wrong one rather than merely an old one.
         */
        this.renderer.setPixelRatio(this.pixelRatioFor(width, height));
        this.renderer.setSize(width, height, false);
        this.applyLevels();
        this.camera.aspect = width / height;
        /* Re-applied after a resize: the view offset is stored in terms of the full canvas size,
           so `updateProjectionMatrix` would otherwise keep shifting by the old screen's geometry. */
        this.applySafeArea();
        this.camera.updateProjectionMatrix();
        this.pickDirty = true;
    }

    setReducedMotion(value: boolean) {
        this.reducedMotion = value;
        this.controls.enableDamping = !value;
        if (value) this.flight = null;
    }

    /**
     * How many frames this engine has actually drawn, and whether it is drawing now.
     *
     * For the tests, not for the product. The offscreen pause can only be asserted honestly as
     * an equality - draw count before, scroll away, draw count after, expect the same number -
     * and a "less than a few" assertion would pass with the defect still present.
     */
    get drawCount() {
        return this.drawn;
    }

    get isPaused() {
        return this.paused;
    }

    /** Screen position of a node, for placing a label in the DOM above the canvas. */
    screenPositionOf(node: number): { x: number; y: number; z: number } | null {
        if (this.pickDirty) this.rebuildPickIndex();
        const z = this.projected[node * 3 + 2];
        if (z > 1 || z < -1) return null;
        return { x: this.projected[node * 3], y: this.projected[node * 3 + 1], z };
    }

    get currentMode() {
        return this.mode;
    }

    /**
     * What the two depth cues are currently set to, and where one node sits in the fog.
     *
     * ## Why this is reported rather than looked up
     *
     * Because neither cue is a constant. The fog ceiling is *solved* against the 3:1 contrast
     * gate for the palette and the page colour of the moment - see `fogCeiling` - and the key
     * light's tint and shape are derived from the page's luminance, so the light shades towards
     * whichever side of the page has contrast to spare. Anything outside this file that needs to
     * know what a fragment will be worth cannot hardcode them and would otherwise have to read
     * the material's uniforms, which is a private arrangement that no test should be pinned to.
     *
     * The one consumer today is `graph-palette.spec.ts`, which predicts the pixels of a curated
     * orb from the CSS tokens plus these numbers and compares them against a screenshot. That
     * test exists because a missing `colorspace_fragment` published every fill about 21 dE00
     * darker than the palette declared and nothing else noticed; predicting a shaded, fogged
     * fragment is what it takes to make that claim about a real orb rather than about a flat
     * patch, because there is no flat patch - the key light is a gradient and the spoke fan is
     * drawn over the middle of its own subject.
     *
     * `fog` is the resolved product: how far towards the page colour this node's fragments are
     * mixed, per-vertex and therefore constant across its disc.
     */
    depthCues(node: number) {
        const uniforms = (
            (this.curatedSlot.has(node) ? this.curated : this.nodes).material as ShaderMaterial
        ).uniforms;
        const target = new Vector3(
            this.drawPositions[node * 3],
            this.drawPositions[node * 3 + 1],
            this.drawPositions[node * 3 + 2],
        ).applyMatrix4(this.camera.matrixWorldInverse);
        const depth = Math.max(-target.z, 1);
        const near = uniforms.uFogNear.value as number;
        const far = uniforms.uFogFar.value as number;
        const reach = Math.min(1, Math.max(0, (depth - near) / Math.max(far - near, 1)));
        const triple = (value: Vector3): [number, number, number] => [value.x, value.y, value.z];
        return {
            depth,
            /** Linear-light, because that is the space the shader mixes in. */
            fogColour: triple(uniforms.uFog.value as Vector3),
            fog: reach * (uniforms.uFogMax.value as number),
            keyAmount: uniforms.uKeyAmount.value as number,
            /** 0 shades the unlit side, 1 lights the lit side. */
            keyShape: uniforms.uKeyShape.value as number,
            keyTint: triple(uniforms.uKeyTint.value as Vector3),
            /** Unit length, in the disc's own coordinates: x right, y down, z towards the eye. */
            light: triple(uniforms.uLight.value as Vector3),
            alpha: uniforms.uAlpha.value as number,
        };
    }

    /**
     * Orb geometry for whoever is placing text: where, how big, how far.
     *
     * A one-way contract, and the direction is the point. Screen-space collision for node labels
     * and relationship labels has to be one pass with one priority order, because two passes on
     * separate cadences cannot honour one order - a relation can never outrank a name that was
     * already placed. So that pass lives in one place and this hands it geometry without placing
     * anything, without an opinion about tiers, and without knowing that labels exist.
     *
     * `radius` is the drawn radius in CSS pixels including the per-level clamp, which is what a
     * collision box has to be built from: the old fixed `COLLIDE_X = 132, COLLIDE_Y = 20`
     * centre-distance test over-reserves for "Agni" and under-reserves for a long constellation
     * name, and it cannot know that a curated orb is ten times the width of a world one.
     *
     * `depth` is normalised device depth, so a caller can order by it without a camera.
     */
    orbGeometry(
        nodes: Iterable<number>,
    ): Array<{ node: number; x: number; y: number; depth: number; radius: number }> {
        if (this.pickDirty) this.rebuildPickIndex();
        const dpr = this.renderer.getPixelRatio();
        const uniforms = (
            (this.curatedSlot.size > 0 ? this.curated : this.nodes).material as ShaderMaterial
        ).uniforms;
        const scale = uniforms.uScale.value as number;
        const gamma = uniforms.uGamma.value as number;
        const reference = uniforms.uRefDepth.value as number;
        const limit = uniforms.uClamp.value as Vector2;
        const rootLimit = uniforms.uRootClamp.value as Vector2;
        const target = new Vector3();
        const out: Array<{
            node: number;
            x: number;
            y: number;
            depth: number;
            radius: number;
        }> = [];
        for (const node of nodes) {
            const at = this.screenPositionOf(node);
            if (!at) continue;
            target
                .set(
                    this.drawPositions[node * 3],
                    this.drawPositions[node * 3 + 1],
                    this.drawPositions[node * 3 + 2],
                )
                .applyMatrix4(this.camera.matrixWorldInverse);
            const distance = Math.max(-target.z, 1);
            const size =
                ((this.world.nodeDegree[node] >= 0
                    ? 9 + Math.cbrt(this.world.nodeDegree[node]) * 2.6
                    : 9) *
                    scale *
                    reference ** (gamma - 1)) /
                distance ** gamma;
            const bounds = this.curatedSlot.get(node) === 0 ? rootLimit : limit;
            const clamped = Math.min(bounds.y, Math.max(bounds.x, size));
            out.push({ node, x: at.x, y: at.y, depth: at.z, radius: clamped / (2 * dpr) });
        }
        return out;
    }

    /**
     * The named constellations, as marks rather than as regions.
     *
     * Centroids and a projected extent, and deliberately nothing else. Encoding group membership
     * over a node-link diagram was measured to cost about 25% accuracy on network tasks across
     * ~800 subjects and ten task types, with hulls winning only for group-membership questions;
     * the one component with positive evidence is a prominent group *label*. This artifact also
     * has 33 communities that are spatially interleaved, so hulls would interpenetrate, and 12 of
     * the 33 are named only "passage cluster" - a label there would assert a distinction the
     * reader cannot use. So: no hulls, no contours, no fills. A centroid, a size, and a name where
     * there is a real one, placed by whoever owns placement.
     */
    constellationMarks(): Array<{
        id: number;
        name: string | null;
        size: number;
        x: number;
        y: number;
        depth: number;
        radius: number;
    }> {
        const constellations = this.world.manifest.constellations ?? [];
        const { width, height } = this.viewport();
        const v = new Vector3();
        const out: Array<{
            id: number;
            name: string | null;
            size: number;
            x: number;
            y: number;
            depth: number;
            radius: number;
        }> = [];
        for (const region of constellations) {
            v.set(region.centre[0], region.centre[1], region.centre[2]);
            const world = v.clone();
            v.project(this.camera);
            if (v.z > 1 || v.z < -1) continue;
            const distance = Math.max(
                world.applyMatrix4(this.camera.matrixWorldInverse).z * -1,
                1,
            );
            const perUnit = height / (2 * Math.tan((this.camera.fov * Math.PI) / 360) * distance);
            out.push({
                id: region.id,
                name: region.name,
                size: region.size,
                x: (v.x * 0.5 + 0.5) * width,
                y: (-v.y * 0.5 + 0.5) * height,
                depth: v.z,
                radius: region.radius * perUnit,
            });
        }
        return out;
    }

    dispose() {
        this.disposed = true;
        cancelAnimationFrame(this.frame);
        this.renderer.domElement.removeEventListener("webglcontextlost", this.onContextLost);
        this.releaseGestures();
        this.controls.dispose();
        this.nodes.geometry.dispose();
        (this.nodes.material as ShaderMaterial).dispose();
        this.curated.geometry.dispose();
        (this.curated.material as ShaderMaterial).dispose();
        this.edges.geometry.dispose();
        (this.edges.material as ShaderMaterial).dispose();
        this.selectionEdges.geometry.dispose();
        (this.selectionEdges.material as LineBasicMaterial).dispose();
        this.renderer.dispose();
    }
}
