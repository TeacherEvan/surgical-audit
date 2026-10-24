#!/usr/bin/env node
/**
 * Canvas geometry probe for surgical-audit Pass 2.5.
 *
 * Hooks CanvasRenderingContext2D.moveTo/lineTo/strokeRect per canvas and reports
 * segment counts, the longest segment, and horizontal/vertical span counts. Use it
 * to prove a "lines across the screen" artefact exists (and later that it is gone).
 *
 * Usage:
 *   node canvas_geometry_probe.mjs <url> [thresholdPx] [hueCanvasSelector]
 *
 *   thresholdPx        default 300 — a legitimate per-frame move cannot reach it
 *   hueCanvasSelector  optional; when given, also histogram hue bands over vivid pixels
 *
 * Env:
 *   PLAYWRIGHT_MODULE  module specifier for playwright (default: 'playwright')
 *
 * Exit: 0 always; inspect the JSON. Long segments are reported, not fatal.
 */
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const PW = process.env.PLAYWRIGHT_MODULE || 'playwright';
const { chromium } = await import(PW);

const URL = process.argv[2];
const THRESH = Number(process.argv[3] || 300);
const HUE_SELECTOR = process.argv[4] || null;
if (!URL) {
    console.error('usage: node canvas_geometry_probe.mjs <url> [thresholdPx] [hueCanvasSelector]');
    process.exit(2);
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const pageErrors = [];
page.on('pageerror', (e) => pageErrors.push(String(e)));

await page.addInitScript((thresh) => {
    window.__geom = {};
    const proto = CanvasRenderingContext2D.prototype;
    const origMove = proto.moveTo;
    const origLine = proto.lineTo;
    const origRect = proto.strokeRect;
    let last = null;

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

    proto.moveTo = function (x, y) {
        last = { id: this.canvas && this.canvas.id ? this.canvas.id : 'no-id', x, y };
        return origMove.call(this, x, y);
    };
    proto.lineTo = function (x, y) {
        const id = this.canvas && this.canvas.id ? this.canvas.id : 'no-id';
        if (last && last.id === id) record(id, Math.abs(x - last.x), Math.abs(y - last.y));
        last = { id, x, y };
        return origLine.call(this, x, y);
    };
    proto.strokeRect = function (x, y, w, h) {
        const id = this.canvas && this.canvas.id ? this.canvas.id : 'no-id';
        bucket(id).rectEdges += 2;
        record(id, Math.abs(w), 0);
        record(id, 0, Math.abs(h));
        return origRect.call(this, x, y, w, h);
    };
}, THRESH);

await page.goto(URL, { waitUntil: 'load' });
// Two animation cycles minimum so a wrap-triggered artefact is not missed.
await page.waitForTimeout(Number(process.env.PROBE_MS || 6500));

const geometry = await page.evaluate(() => {
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

let hues = null;
if (HUE_SELECTOR) {
    hues = await page.evaluate((sel) => {
        const canvas = document.querySelector(sel);
        if (!canvas) return { error: 'selector not found' };
        const tmp = document.createElement('canvas');
        tmp.width = canvas.width;
        tmp.height = canvas.height;
        const tctx = tmp.getContext('2d');
        tctx.drawImage(canvas, 0, 0);
        const { data } = tctx.getImageData(0, 0, tmp.width, tmp.height);
        const names = ['red', 'orange', 'amber', 'lime', 'green', 'spring', 'cyan', 'azure', 'blue', 'violet', 'magenta', 'pink'];
        const bands = new Array(12).fill(0);
        let vivid = 0;
        for (let i = 0; i < data.length; i += 4) {
            const r = data[i], g = data[i + 1], b = data[i + 2];
            const max = Math.max(r, g, b), min = Math.min(r, g, b);
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
            hueBands: Object.fromEntries(bands.map((c, i) => [names[i], +((c / Math.max(1, vivid)) * 100).toFixed(1)])),
        };
    }, HUE_SELECTOR);
}

console.log(JSON.stringify({ url: URL, threshold: THRESH, pageErrors, geometry, hues }, null, 2));
await browser.close();
