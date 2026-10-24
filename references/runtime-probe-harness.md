# Runtime Probe Harness — auditing what the app actually draws

Use during **Pass 2.5 (Live Geometry Probe)** when the defect is visual: lines across the screen, washed-out colour, flicker, elements painted outside their container. Static reading cannot prove a visual fix; only the same probe run against the before and after builds can.

---

## 1. Scope the preflight scan so it does not time out

`scripts/preflight_telemetry.py <repo-root>` prunes `.git` but still walks `node_modules`, and a JS repo blows past a 180 s foreground timeout. A timed-out scan emits no digest — and no digest means no zero-mutation proof.

```bash
# preferred: scan the source subtree only
python3 ~/.hermes/skills/surgical-audit/scripts/preflight_telemetry.py src --out /tmp/telemetry.json

# whole-tree runs: give it room, or run it in the background
python3 ~/.hermes/skills/surgical-audit/scripts/preflight_telemetry.py . --out /tmp/telemetry.json   # timeout >= 600 s
```

A subtree digest still satisfies invariant #2 as long as you digest the same subtree before and after.

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

Screenshots prove *something* changed; segment counts prove the artefact is gone. Install the hook before page scripts run, using Playwright's `addInitScript`, wrapping `moveTo`, `lineTo`, and `strokeRect` and bucketing by `this.canvas.id`.

Rules that keep the probe honest:

- **Record counts, not histories.** A busy canvas emits ~1M segments in seconds; storing every segment exhausts the page's memory. Keep `count`, `longest`, and only the segments above the threshold.
- **Classify the axis.** A full-span artefact is axis-aligned: flag `dx > dy * 4` as horizontal and `dy > dx * 4` as vertical. A diagonal streak is a different bug.
- **Threshold only a teleport can cross.** An entity moving a few px per frame cannot emit a 300 px segment. Anything above that is a discontinuity — edge wrap, drag, resize, or a mis-scaled unit.
- **Reduce, never spread.** `Math.max(0, ...segments.map(...))` throws `RangeError: Maximum call stack size exceeded` around ~100k elements inside `page.evaluate`. Accumulate in a loop.
- **Pin the DPR.** Launch with `deviceScaleFactor: 1` for reproducible pixel maths. Hook coordinates are in transform space, so a `ctx.scale(dpr)` does not change measured segment lengths.

`scripts/canvas_geometry_probe.mjs` implements all of the above; run it against both ports.

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
- If a metric regresses, say so in the ledger and name the follow-up lever (theme-aware alpha, larger sprite radius) instead of burying it.

---

## 6. Calibrate constants by measurement, not taste

When an alpha, opacity, or line width exists to keep something legible, tune it against the measurement that motivated it. Run the probe at candidate values, keep the value whose numbers match the intent, and write the measured justification beside the constant so a later cleanup does not revert it to the pre-fix guess.

---

## 7. Protected instruction files

If a write to `AGENTS.md` or another protected agent-instruction file is refused (approval timeout), do not route around it through the terminal or another path. Deliver the exact Markdown block in the report for the user to paste in, and label it blocked. If the user later explicitly re-requests the write, retry once — that is fresh authorisation, not a workaround.
