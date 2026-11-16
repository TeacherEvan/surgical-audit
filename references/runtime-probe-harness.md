# Runtime Probe Harness — auditing what the app actually draws

Use during **Pass 2.5 (Live Geometry Probe)** when the defect is visual: lines across the screen, washed-out colour, flicker, elements painted outside their container, or WCAG 2.2 accessibility/focus regressions. Static reading cannot prove a visual fix; only the same probe run against the before and after builds can.

---

## 1. Scope the preflight scan for focus and speed

`scripts/preflight_telemetry.py <repo-root>` automatically prunes standard vendored and cache trees (`.git`, `node_modules`, `dist`, `build`, `.next`, `.turbo`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `venv`, `.venv`) and reports `skipped_dirs_count`. On huge monorepos with additional generated assets or media fixtures, scan the application source subtree or emit SARIF directly:

```bash
# Preferred: scan the source subtree for focused telemetry
python3 <skill>/scripts/preflight_telemetry.py src --out /tmp/telemetry.json

# Whole-tree scan exporting SARIF 2.1.0 for CI / static-analysis consumption
python3 <skill>/scripts/preflight_telemetry.py . --sarif --out /tmp/telemetry.sarif
```

A subtree digest still satisfies invariant #2 as long as you digest the exact same subtree before and after.

---

## 2. Keep a pristine baseline when the tree is already dirty

Prior work in flight means `HEAD` is not the pre-audit state. Capture both:

```bash
# the state you are about to change
git status --porcelain && git rev-parse HEAD

# a reproducible "before" build
git archive HEAD | tar -x -C <scratch>/baseline
```

Serve the baseline on a second port (`http-server -p <alt> -c-1 -s`) so one probe script runs against both URLs. Confirm which port serves which build by grepping a symbol the fix introduces — never assume port order:

```bash
curl -s "$URL/renderer/effects.js" | grep -c "drawSubtleGridPattern"   # 2 = before, 0 = after
```

---

## 3. Hook Canvas 2D geometry instead of comparing screenshots

Screenshots prove *something* changed; segment counts prove the artefact is gone. Install the hook before page scripts run, using Playwright's `addInitScript`, wrapping `beginPath`, `closePath`, `moveTo`, `lineTo`, `quadraticCurveTo`, `bezierCurveTo`, `rect`, and `strokeRect` with a per-context `WeakMap` (`lastByCtx`), per-canvas ID assignment (`canvasIds` `WeakMap`), and `this.getTransform()` CSS-pixel coordinate mapping.

Rules that keep the probe honest:

- **Record counts, not histories.** A busy canvas emits ~1M segments in seconds; storing every segment exhausts the page's memory. Keep `count`, `longest`, and only the segments above the threshold.
- **Isolate per-context state.** Track path state inside a `WeakMap` keyed by `CanvasRenderingContext2D`, never a shared global `let last` variable — otherwise multi-canvas scenes cross-contaminate endpoints.
- **Classify the axis.** A full-span artefact is axis-aligned: flag `dx > dy * 4` as horizontal and `dy > dx * 4` as vertical. A diagonal streak is a different bug.
- **Threshold only a teleport can cross.** An entity moving a few px per frame cannot emit a 300 px segment. Anything above that is a discontinuity — edge wrap, drag, resize, or a mis-scaled unit.
- **Reduce, never spread.** `Math.max(0, ...segments.map(...))` throws `RangeError: Maximum call stack size exceeded` around ~100k elements inside `page.evaluate`. Accumulate in a loop.
- **Pin the DPR and apply `getTransform()`.** Launch with `deviceScaleFactor: 1` and transform coordinates with `this.getTransform()` so `ctx.translate` / `ctx.scale` / `ctx.rotate` produce accurate CSS-pixel distances.

`scripts/canvas_geometry_probe.mjs` implements all of the above (including `try/finally` browser cleanup, `consoleErrors` / `requestFailures` capture, and zero-size / CORS-tainted canvas guards); run it against both ports.

---

## 4. Probe traps that cost time

- **Disabled-control gating.** A "Start" button is often disabled until a prerequisite choice is made. Click the prerequisite first (grid size, mode, player count) or the probe times out and reports a false negative for the whole screen.
- **Redacted tool output.** Long paths and filenames can come back from the terminal as `***` or `sk-men....png` while the file on disk is intact. Confirm with `grep`/`sed` against the real file before repairing something that is not broken.
- **Silent zero.** A probe that finds zero segments may be hooked to the wrong canvas id, or the page may have swapped canvases on navigation. Print the per-canvas id keys alongside the numbers so "0" is distinguishable from "not observed".
- **`pkill -f` matches your own command line.** `pkill -f "http-server -p 8123"` terminates the shell that is running the `pkill`, because the pattern appears in that shell's own argv (exit `-15`, truncated output, no error message). Bracket one character — `pkill -f "[h]ttp-server -p 812"` — or kill by PID taken from `ss -lntp`.
- **Single-sample flattery.** Sample at least two full animation cycles; a streak bug that fires on wrap can be absent from a short, lucky window.

---

## 5. Quantify colour complaints as distributions

"Too washed out" and "no bright colours" are measurable. Draw the live canvas into an offscreen canvas, read `getImageData`, and histogram hue bands over pixels above a vividness floor (`V >= 0.45`, `S >= 0.35`). Report each band's percentage share plus total vivid pixel count.

- Before/after shares prove both directions in one table: a single hue collapsing from ~60 % to ~15 %, and a band stuck at 0 % rising to double digits.
- Watch the trade. Full hue coverage can *lower* total vivid pixel mass on a light backdrop, because the old monochrome element was the brightest object in the scene. State the trade explicitly rather than claiming an unambiguous win.

### 5b. Accessibility, Focus & Media-Query Probes (WCAG 2.2)

- **Target Size (`WCAG 2.5.8`):** Measure every interactive control's rendered hit box (`getBoundingClientRect()`): assert `width >= 24 && height >= 24` CSS px (except inline prose links or equivalent spaced targets).
- **Focus Not Obscured (`WCAG 2.4.11`):** Tab through interactive elements in headless Chromium and assert the focused element's rect is not wholly hidden behind sticky headers/footers/modals (`elementFromPoint` at center hits the target or its descendant).
- **Preference Media Queries:** Audit with `emulateMedia` across `reducedMotion: 'reduce'`, `contrast: 'more'`, and `forcedColors: 'active'` so motion suppression and high-contrast outlines work on all three queries (`prefers-reduced-motion`, `prefers-contrast`, `forced-colors`).
- **Composited Contrast:** Compute WCAG 1.4.3 / 1.4.11 contrast against the *actual composited pixel background* (alpha-blended layers, translucent scrims, or `<canvas>` backdrops), never raw CSS hex tokens alone.

---

## 6. Calibrate constants by measurement, not taste

When an alpha, opacity, or line width exists to keep something legible, tune it against the measurement that motivated it. Run the probe at candidate values, keep the value whose numbers match the intent, and write the measured justification beside the constant so a later cleanup does not revert it to the pre-fix guess.

---

## 7. Protected instruction files

If a write to `AGENTS.md` or another protected agent-instruction file is refused (approval timeout), do not route around it through the terminal or another path. Deliver the exact Markdown block in the report for the user to paste in, and label it blocked. If the user later explicitly re-requests the write, retry once — that is fresh authorisation, not a workaround.

---

## 8. Proving a performance claim

A remediation motivated by frame cost lives or dies on one number, and that number is the easiest thing in the session to fake by accident. Run this protocol before any sentence containing "fps", "faster", "smoother" or "no longer drops frames".

### 8a. Check the host before you trust a result

```bash
uptime                                                 # load average vs core count
nproc
ps -eo pcpu,comm --sort=-pcpu | head -6                # who is eating the cores
```

A load average near or above `nproc`, or an unrelated browser/compiler holding a core, means the benchmark is measuring the machine. Two dev servers plus a game instance on a CPU-only box is already contention — and a dev server also carries HMR and framework development-mode overhead the product never ships.

**Prefer production builds for both arms.** `git archive HEAD | tar -x -C <scratch>/baseline`, build each tree, and serve the two `dist/` directories over a static server, so neither arm pays for the dev toolchain. Never kill the user's unrelated processes to buy a clean number.

### 8b. Alternate, and take a median of N

Never sample the same build twice in a row and compare means of two. Run the arms **alternately** (`A, B, A, B, A, B`) so slow drift hits both, take three or more samples per arm, and report the **median plus the spread**. Alternating controls for drift; the median survives a single bad sample; the spread is the number that tells you whether any of it means anything.

```python
for _ in range(3):
    base.append(sample(BASELINE_URL)); ref.append(sample(REF_URL))
median = statistics.median
```

### 8c. The same-build spread is the noise floor — respect it

Measure the **baseline against itself** before comparing arms. If identical builds report 30 fps and 59 fps on different runs, the effect you are trying to prove is smaller than the environment and **no comparison between arms is meaningful**. In that state the honest output is "inconclusive, host was saturated" — not the most flattering of the two numbers. Cherry-picking the good run is the failure mode this whole section exists to prevent.

Corollary: an effect that appears in one pair and vanishes in the next is not an effect. Report the direction and the spread together, or report nothing.

### 8d. A regression result is a hypothesis test on your own design

When the first A/B says the change made things **worse**, do not re-run until it agrees with you. Treat it as evidence the diagnosis was wrong and go looking for what the refactor actually left in the hot path. In frame-budget work the usual culprit is a **layout property being written every frame**: `left`, `top`, `width`, `height` and `margin` invalidate layout even when assigned an unchanged value, while `transform` and `opacity` are compositor-only. Writing "the same position" via `style.left` every tick is a per-frame layout pass wearing the costume of an animation.

### 8e. When timing cannot be measured, measure counts

Frame time is the noisiest possible instrument. The work you claimed to remove is usually **countable**, and counts are unaffected by load:

| Instead of | Count |
| :--- | :--- |
| "runs smoother" | React/state dispatches per second on a movement-only frame |
| "less DOM churn" | `style` attribute mutations per second (`MutationObserver`, `attributeFilter: ['style']`) |
| "fewer allocations" | allocations per frame inside the loop |
| "cheaper collision" | dispatch count vs. frames where something actually collided |

```js
window.__probe = { writes: 0 };
new MutationObserver((r) => { window.__probe.writes += r.length; })
  .observe(document.querySelector('[data-testid=game-area]'),
           { attributes: true, attributeFilter: ['style'], subtree: true });
```

Counts convert directly into **unit-test assertions** ("a movement-only frame dispatches nothing"), which run forever on any machine, instead of a browser probe that only reproduces on an idle host. State the deterministic reductions as proven and the wall-clock win as unproven — in that order, and never merge the two into one claim.

### 8f. Whenever the claim is about rendering, also capture long tasks

`PerformanceObserver({ entryTypes: ['longtask'] })` totals main-thread blocking that frame-delta sampling smooths over. It is more stable than FPS under load and exposes stalls a p50 hides. Report `count` and total `ms` beside the frame numbers.
