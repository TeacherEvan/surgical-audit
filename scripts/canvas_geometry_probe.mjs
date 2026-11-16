#!/usr/bin/env node
/**
 * Canvas geometry probe for surgical-audit Pass 2.5.
 *
 * Hooks CanvasRenderingContext2D path and rect operations per context and reports
 * segment counts, the longest segment, and horizontal/vertical span counts. Use
 * it to prove a cross-canvas artefact exists (and later that it is gone).
 *
 * Usage:
 *   node canvas_geometry_probe.mjs <url> [thresholdPx] [hueCanvasSelector]
 *
 *   thresholdPx        default 300 — a legitimate per-frame move cannot reach it
 *   hueCanvasSelector  optional; when given, also histogram hue bands over vivid pixels
 *
 * Env:
 *   PLAYWRIGHT_MODULE  module specifier for playwright (default: 'playwright')
 *   PROBE_MS           observation wait in ms after load (default: 6500)
 *
 * Exit: 0 on successful probe (long segments are reported, not fatal); 2 on bad CLI args.
 */

const PW = process.env.PLAYWRIGHT_MODULE || 'playwright';

const URL = process.argv[2];
const rawThreshold = process.argv[3];
const THRESH = rawThreshold !== undefined ? Number(rawThreshold) : 300;
const HUE_SELECTOR = process.argv[4] || null;
const rawProbeMs = process.env.PROBE_MS;
const PROBE_MS = rawProbeMs !== undefined ? Number(rawProbeMs) : 6500;

if (!URL || !Number.isFinite(THRESH) || THRESH < 0) {
    console.error('usage: node canvas_geometry_probe.mjs <url> [thresholdPx>=0] [hueCanvasSelector]');
    process.exit(2);
}
if (!Number.isFinite(PROBE_MS) || PROBE_MS < 0) {
    console.error('error: PROBE_MS must be a non-negative finite number');
    process.exit(2);
}

const { chromium } = await import(PW);

const browser = await chromium.launch();
const pageErrors = [];
const consoleErrors = [];
const requestFailures = [];
let geometry = {};
let hues = null;

try {
    const page = await browser.newPage({
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 1,
    });
    page.on('pageerror', (e) => pageErrors.push(String(e)));
    page.on('console', (msg) => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('requestfailed', (req) => {
        const failure = req.failure();
        requestFailures.push({
            url: req.url(),
            errorText: failure ? failure.errorText : 'unknown',
        });
    });

    await page.addInitScript((thresh) => {
        window.__geom = {};
        const proto = CanvasRenderingContext2D.prototype;
        const origBegin = proto.beginPath;
        const origClose = proto.closePath;
        const origMove = proto.moveTo;
        const origLine = proto.lineTo;
        const origQuad = proto.quadraticCurveTo;
        const origBezier = proto.bezierCurveTo;
        const origRect = proto.rect;
        const origStrokeRect = proto.strokeRect;

        const lastByCtx = new WeakMap();
        const canvasIds = new WeakMap();
        let nextAnonId = 1;

        const ctxId = (ctx) => {
            const canvas = ctx && ctx.canvas;
            if (!canvas) return 'detached-ctx';
            if (canvas.id) return canvas.id;
            let assigned = canvasIds.get(canvas);
            if (!assigned) {
                assigned = `anon-canvas-${nextAnonId}`;
                nextAnonId += 1;
                canvasIds.set(canvas, assigned);
            }
            return assigned;
        };

        const mapPt = (ctx, x, y) => {
            if (typeof ctx.getTransform === 'function') {
                const m = ctx.getTransform();
                return {
                    x: m.a * x + m.c * y + m.e,
                    y: m.b * x + m.d * y + m.f,
                };
            }
            return { x, y };
        };

        const bucket = (id) =>
            (window.__geom[id] = window.__geom[id] || {
                count: 0,
                longest: 0,
                longCount: 0,
                horizontal: 0,
                vertical: 0,
                rectEdges: 0,
                sample: [],
            });

        const record = (id, dx, dy) => {
            if (!Number.isFinite(dx) || !Number.isFinite(dy)) return;
            const b = bucket(id);
            const len = Math.hypot(dx, dy);
            b.count += 1;
            if (len > b.longest) b.longest = len;
            if (len > thresh) {
                b.longCount += 1;
                if (dx > dy * 4) b.horizontal += 1;
                if (dy > dx * 4) b.vertical += 1;
                if (b.sample.length < 4) b.sample.push(Math.round(len));
            }
        };

        const recordPts = (id, p0, p1) => {
            record(id, Math.abs(p1.x - p0.x), Math.abs(p1.y - p0.y));
        };

        proto.beginPath = function () {
            lastByCtx.delete(this);
            return origBegin.call(this);
        };

        proto.closePath = function () {
            const state = lastByCtx.get(this);
            if (state) {
                recordPts(ctxId(this), state, { x: state.startX, y: state.startY });
                state.x = state.startX;
                state.y = state.startY;
            }
            return origClose.call(this);
        };

        proto.moveTo = function (x, y) {
            const p = mapPt(this, x, y);
            lastByCtx.set(this, { startX: p.x, startY: p.y, x: p.x, y: p.y });
            return origMove.call(this, x, y);
        };

        proto.lineTo = function (x, y) {
            const p = mapPt(this, x, y);
            const state = lastByCtx.get(this);
            if (state) {
                recordPts(ctxId(this), state, p);
                state.x = p.x;
                state.y = p.y;
            } else {
                lastByCtx.set(this, { startX: p.x, startY: p.y, x: p.x, y: p.y });
            }
            return origLine.call(this, x, y);
        };

        proto.quadraticCurveTo = function (cpx, cpy, x, y) {
            const p = mapPt(this, x, y);
            const state = lastByCtx.get(this);
            if (state) {
                recordPts(ctxId(this), state, p);
                state.x = p.x;
                state.y = p.y;
            } else {
                lastByCtx.set(this, { startX: p.x, startY: p.y, x: p.x, y: p.y });
            }
            return origQuad.call(this, cpx, cpy, x, y);
        };

        proto.bezierCurveTo = function (cp1x, cp1y, cp2x, cp2y, x, y) {
            const p = mapPt(this, x, y);
            const state = lastByCtx.get(this);
            if (state) {
                recordPts(ctxId(this), state, p);
                state.x = p.x;
                state.y = p.y;
            } else {
                lastByCtx.set(this, { startX: p.x, startY: p.y, x: p.x, y: p.y });
            }
            return origBezier.call(this, cp1x, cp1y, cp2x, cp2y, x, y);
        };

        const recordRectCorners = (ctx, x, y, w, h) => {
            const id = ctxId(ctx);
            const p0 = mapPt(ctx, x, y);
            const p1 = mapPt(ctx, x + w, y);
            const p2 = mapPt(ctx, x + w, y + h);
            const p3 = mapPt(ctx, x, y + h);
            bucket(id).rectEdges += 4;
            recordPts(id, p0, p1);
            recordPts(id, p1, p2);
            recordPts(id, p2, p3);
            recordPts(id, p3, p0);
            return p0;
        };

        proto.rect = function (x, y, w, h) {
            const p0 = recordRectCorners(this, x, y, w, h);
            lastByCtx.set(this, { startX: p0.x, startY: p0.y, x: p0.x, y: p0.y });
            return origRect.call(this, x, y, w, h);
        };

        proto.strokeRect = function (x, y, w, h) {
            recordRectCorners(this, x, y, w, h);
            return origStrokeRect.call(this, x, y, w, h);
        };
    }, THRESH);

    await page.goto(URL, { waitUntil: 'load' });
    // Two animation cycles minimum so a wrap-triggered artefact is not missed.
    await page.waitForTimeout(PROBE_MS);

    geometry = await page.evaluate(() => {
        const out = {};
        for (const [id, b] of Object.entries(window.__geom || {})) {
            out[id] = {
                segments: b.count,
                longCount: b.longCount,
                longest: Math.round(b.longest * 10) / 10,
                horizontal: b.horizontal,
                vertical: b.vertical,
                rectEdges: b.rectEdges,
                sample: b.sample,
            };
        }
        return out;
    });

    if (HUE_SELECTOR) {
        hues = await page.evaluate((sel) => {
            const canvas = document.querySelector(sel);
            if (!canvas) return { error: 'selector not found' };
            if (!canvas.width || !canvas.height) return { error: 'zero-sized canvas' };
            const tmp = document.createElement('canvas');
            tmp.width = canvas.width;
            tmp.height = canvas.height;
            const tctx = tmp.getContext('2d');
            if (!tctx) return { error: '2d context unavailable' };
            let data;
            try {
                tctx.drawImage(canvas, 0, 0);
                data = tctx.getImageData(0, 0, tmp.width, tmp.height).data;
            } catch (err) {
                return { error: String(err) };
            }
            const names = [
                'red', 'orange', 'amber', 'lime', 'green', 'spring',
                'cyan', 'azure', 'blue', 'violet', 'magenta', 'pink',
            ];
            const bands = new Array(12).fill(0);
            let vivid = 0;
            for (let i = 0; i < data.length; i += 4) {
                const r = data[i];
                const g = data[i + 1];
                const b = data[i + 2];
                const max = Math.max(r, g, b);
                const min = Math.min(r, g, b);
                if (max / 255 < 0.45 || max === 0 || (max - min) / max < 0.35) continue;
                vivid += 1;
                const d = max - min;
                let h = 0;
                if (d !== 0) {
                    if (max === r) h = ((g - b) / d) % 6;
                    else if (max === g) h = (b - r) / d + 2;
                    else h = (r - g) / d + 4;
                    h *= 60;
                    if (h < 0) h += 360;
                }
                bands[Math.min(11, Math.floor(h / 30))] += 1;
            }
            return {
                vivid,
                hueBands: Object.fromEntries(
                    bands.map((c, i) => [names[i], +((c / Math.max(1, vivid)) * 100).toFixed(1)]),
                ),
            };
        }, HUE_SELECTOR);
    }

    console.log(
        JSON.stringify(
            {
                url: URL,
                threshold: THRESH,
                pageErrors,
                consoleErrors,
                requestFailures,
                geometry,
                hues,
            },
            null,
            2,
        ),
    );
} finally {
    await browser.close();
}
