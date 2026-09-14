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
    Vector3,
    WebGLRenderer,
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { edgesOf, otherEnd, type World } from "./artifact";
import { LABEL_FRACTIONS, LABEL_STRIDE } from "./edge-labels";
import { installGestures } from "./gesture";

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

/**
 * How many edges the world tier draws before anything is selected.
 *
 * Chosen from the sweep in `scripts/bench-world.mjs --sweep`, which varies this number and
 * measures the resulting frame interval on the machine it runs on. The value here is the one
 * that held a frame inside the refresh budget on the development machine's integrated GPU
 * with headroom left for a camera move, which is when the scene is at its most expensive.
 */
const WORLD_EDGE_BUDGET = 24_000;

/** What stays drawn behind a traced route: enough for context, not enough to obscure it. */
const PATH_EDGE_BUDGET = 1_200;

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

export type EngineStats = {
    /** Derived from the real frame interval, not from how long `render` took to return. */
    fps: number;
    frameMs: number;
    /** 95th percentile frame interval over the sampling window. */
    p95Ms: number;
    /** The JavaScript half of the frame. Its distance from `frameMs` is the GPU and vsync. */
    jsMs: number;
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
    uniform float uScale;
    varying vec3 vColour;
    varying float vAlpha;
    void main() {
        vColour = aColour;
        vAlpha = aAlpha;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        /*
         * Perspective size attenuation, clamped at both ends.
         *
         * A node twice as far is half as wide, which is what makes depth readable without fog
         * or glow. Unclamped, though, the division by view depth is unbounded: fly the camera
         * up to a hub and its disc grows without limit, and a node with 7,347 edges seen from
         * close range covers a large part of the viewport. Measured, that is not a cosmetic
         * problem - the same scene that holds 60 fps at world distance fell to 10 fps with the
         * camera brought in, because a handful of discs were each filling millions of pixels.
         *
         * The ceiling is also the right answer visually. These are index marks, not spheres;
         * one is meant to say "a subject is here", and past about thirty pixels it stops
         * saying that and starts looking like an object with a surface.
         */
        gl_PointSize = clamp(aSize * uScale / max(-mv.z, 1.0), 1.0, 30.0);
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
        gl_FragColor = vec4(vColour, vAlpha * edge);
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
    private nodeAlpha!: Float32Array;
    private nodeColour!: Float32Array;
    private nodeSize!: Float32Array;
    private edgeAlpha!: Float32Array;
    private edgeColour!: Float32Array;

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
        /*
         * Pixel ratio is capped at 1.5, not at the usual 2.
         *
         * This scene is fill-rate bound rather than geometry bound - it is a very large number
         * of translucent fragments over a small number of objects - so the framebuffer is the
         * budget. At DPR 2 a 1440x836 viewport is 4.8 million pixels; at 1.5 it is 2.7
         * million, and every blended line is paid for once per pixel it covers. Points and
         * hairlines have no fine detail for the extra samples to resolve, so the cost buys
         * almost nothing back.
         */
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
        this.renderer.setClearColor(options.background, 1);
        this.scene.background = options.background;

        const { clientWidth, clientHeight } = options.canvas;
        this.camera = new PerspectiveCamera(
            52,
            Math.max(clientWidth, 1) / Math.max(clientHeight, 1),
            1,
            20000,
        );
        this.camera.position.set(0, 0, 2600);

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
        this.resize();
    }

    /* ---------------------------------------------------------- geometry - */

    private buildNodes() {
        const { positions, nodeGroup, nodeDegree, manifest } = this.world;
        const count = manifest.counts.nodes;

        this.nodeColour = new Float32Array(count * 3);
        this.nodeSize = new Float32Array(count);
        this.nodeAlpha = new Float32Array(count);

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
            this.nodeAlpha[i] = 0.85;
        }

        const geometry = new BufferGeometry();
        geometry.setAttribute("position", new BufferAttribute(positions, 3));
        geometry.setAttribute("aColour", new BufferAttribute(this.nodeColour, 3));
        geometry.setAttribute("aSize", new BufferAttribute(this.nodeSize, 1));
        geometry.setAttribute("aAlpha", new BufferAttribute(this.nodeAlpha, 1));

        const material = new ShaderMaterial({
            vertexShader: NODE_VERTEX,
            fragmentShader: NODE_FRAGMENT,
            uniforms: { uScale: { value: 1 } },
            transparent: true,
            // Depth writing off, so a node behind another does not punch a hole in it; the
            // discs are translucent and are meant to accumulate into density.
            depthWrite: false,
        });
        this.nodes = new Points(geometry, material);
        // One object for the whole graph means frustum culling is all-or-nothing, and since
        // the camera is usually inside the cloud it would never cull anything anyway.
        this.nodes.frustumCulled = false;
        this.scene.add(this.nodes);
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
        const { positions } = this.world;

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
        const budget =
            this.edgeBudgetOverride ??
            (this.path.length > 1 ? PATH_EDGE_BUDGET : WORLD_EDGE_BUDGET);
        const drawn = Math.min(semantic, budget);
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

    setMode(mode: WorldMode) {
        this.mode = mode;
        this.applySelection();
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

        if (this.path.length > 1) {
            const along = new Set(this.path);
            for (let i = 0; i < count; i += 1) this.nodeAlpha[i] = along.has(i) ? 1 : 0.06;
            this.restEdges();
        } else if (focus === null) {
            for (let i = 0; i < count; i += 1) this.nodeAlpha[i] = 0.85;
            this.restEdges();
        } else {
            const near = new Set<number>([focus]);
            const touching = edgesOf(this.world, focus);
            for (let i = 0; i < touching.length; i += 1) {
                near.add(otherEnd(this.world, touching[i], focus));
            }
            for (let i = 0; i < count; i += 1) {
                this.nodeAlpha[i] = near.has(i) ? 0.96 : 0.1;
            }
            this.restEdges();
            for (let i = 0; i < touching.length; i += 1) {
                const edge = touching[i];
                this.edgeAlpha[edge * 2] = 0.62;
                this.edgeAlpha[edge * 2 + 1] = 0.62;
            }
        }

        this.applyEdgeRange();
        this.updateSelectionEdges();
        (this.nodes.geometry.getAttribute("aAlpha") as BufferAttribute).needsUpdate = true;
        (this.edges.geometry.getAttribute("aAlpha") as BufferAttribute).needsUpdate = true;
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
        const { positions } = this.world;
        const width = this.renderer.domElement.clientWidth;
        const height = this.renderer.domElement.clientHeight;
        this.pickBuckets.clear();
        const v = new Vector3();
        for (let i = 0; i < count; i += 1) {
            if (this.nodeAlpha[i] < 0.14) {
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
                    // A generous radius on the busiest nodes, which are also the largest.
                    const radius = 6 + Math.cbrt(this.world.nodeDegree[i]) * 1.6;
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
        const { positions } = this.world;
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

        /* A band narrower than this is not somewhere a subject can be read, so the shift stops
           growing rather than flying the camera off to satisfy an impossible constraint. */
        const MIN_BAND = 120;
        const visibleWidth = width - left - right;
        const visibleHeight = height - top - bottom;
        if (visibleWidth < MIN_BAND || visibleHeight < MIN_BAND) {
            this.camera.clearViewOffset();
            this.pickDirty = true;
            return;
        }

        const centreX = left + visibleWidth / 2;
        const centreY = top + visibleHeight / 2;
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

    private positionOf(node: number) {
        const { positions } = this.world;
        return new Vector3(
            positions[node * 3],
            positions[node * 3 + 1],
            positions[node * 3 + 2],
        );
    }

    /** Frame the whole world. */
    fitWorld(ms = 900) {
        this.flyTo(new Vector3(0, 0, 2600), new Vector3(0, 0, 0), ms);
    }

    /**
     * Frame a node and its neighbours.
     *
     * The distance comes from the spread of the neighbourhood rather than from a constant, so
     * a deity with four thousand edges and a verse with three both arrive at a readable size.
     */
    focusNode(node: number, ms = 1000) {
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
        this.controls.update();
        const material = this.nodes.material as ShaderMaterial;
        // Point size is in pixels, so it has to track both the viewport height and the field
        // of view or nodes change size when the window does.
        material.uniforms.uScale.value =
            this.renderer.domElement.clientHeight /
            (2 * Math.tan((this.camera.fov * Math.PI) / 360));
        this.renderer.render(this.scene, this.camera);
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
            drawnNodes: this.world.manifest.counts.nodes,
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
        this.renderer.setSize(width, height, false);
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

    dispose() {
        this.disposed = true;
        cancelAnimationFrame(this.frame);
        this.renderer.domElement.removeEventListener("webglcontextlost", this.onContextLost);
        this.releaseGestures();
        this.controls.dispose();
        this.nodes.geometry.dispose();
        (this.nodes.material as ShaderMaterial).dispose();
        this.edges.geometry.dispose();
        (this.edges.material as ShaderMaterial).dispose();
        this.selectionEdges.geometry.dispose();
        (this.selectionEdges.material as LineBasicMaterial).dispose();
        this.renderer.dispose();
    }
}
