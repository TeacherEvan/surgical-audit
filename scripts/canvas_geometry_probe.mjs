#!/usr/bin/env node
/**
 * Canvas geometry probe for surgical-audit Pass 2.5 (v3.0.0).
 *
 * Reuses the pure, unit-tested stroke-gated hooks in canvas_probe_core.mjs:
 * geometry counters commit only on stroke()/strokeRect()/stroke(Path2D), so
 * rect() used for clip()/fill() produces zero false artefacts.
 *
 * Usage:
 *   node canvas_geometry_probe.mjs <url> [thresholdPx] [hueCanvasSelector] \
 *       [--click SELECTOR]... [--viewport WxH] [--probe-ms N] [--wcag]
 *
 * Env:
 *   PLAYWRIGHT_MODULE  module specifier for playwright (default: 'playwright')
 *   PROBE_MS           default observation wait in ms (default: 6500)
 *
 * Exit: 0 on successful probe; 2 on bad CLI args.
 */

import {
  HUE_BAND_NAMES,
  computeHueHistogram,
  installCanvasGeometryHook,
  summarizeGeometry,
} from './canvas_probe_core.mjs';

const PW = process.env.PLAYWRIGHT_MODULE || 'playwright';

const positional = [];
const clicks = [];
let viewport = { width: 1440, height: 900 };
let probeMs = process.env.PROBE_MS !== undefined ? Number(process.env.PROBE_MS) : 6500;
let wcag = false;

const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i += 1) {
  const a = argv[i];
  if (a === '--click') {
    clicks.push(argv[i + 1]);
    i += 1;
  } else if (a === '--viewport') {
    const m = /^(\d+)x(\d+)$/.exec(argv[i + 1] || '');
    if (!m) {
      console.error('error: --viewport expects WxH (e.g. 1280x720)');
      process.exit(2);
    }
    viewport = { width: Number(m[1]), height: Number(m[2]) };
    i += 1;
  } else if (a === '--probe-ms') {
    probeMs = Number(argv[i + 1]);
    i += 1;
  } else if (a === '--wcag') {
    wcag = true;
  } else {
    positional.push(a);
  }
}

const URL = positional[0];
const THRESH = positional[1] !== undefined ? Number(positional[1]) : 300;
const HUE_SELECTOR = positional[2] || null;

if (!URL || !Number.isFinite(THRESH) || THRESH < 0) {
  console.error('usage: node canvas_geometry_probe.mjs <url> [thresholdPx>=0] [hueCanvasSelector] [--click S] [--viewport WxH] [--probe-ms N] [--wcag]');
  process.exit(2);
}
if (!Number.isFinite(probeMs) || probeMs < 0) {
  console.error('error: --probe-ms / PROBE_MS must be a non-negative finite number');
  process.exit(2);
}
if (clicks.some((c) => !c)) {
  console.error('error: --click requires a selector argument');
  process.exit(2);
}

const initScript = `
  const HUE_BAND_NAMES = ${JSON.stringify(HUE_BAND_NAMES)};
  const computeHueHistogram = ${computeHueHistogram.toString()};
  const summarizeGeometry = ${summarizeGeometry.toString()};
  const installCanvasGeometryHook = ${installCanvasGeometryHook.toString()};
  window.__geom = {};
  installCanvasGeometryHook(
    CanvasRenderingContext2D.prototype, window.Path2D, ${THRESH}, window.__geom
  );
  window.__summarizeGeometry = summarizeGeometry;
  window.__computeHueHistogram = computeHueHistogram;
`;

const { chromium } = await import(PW);
const browser = await chromium.launch();
const pageErrors = [];
const consoleErrors = [];
const requestFailures = [];
let geometry = {};
let hues = null;
let wcagResult = null;

try {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
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

  await page.addInitScript(initScript);
  await page.goto(URL, { waitUntil: 'load' });

  // Prerequisite click setup: dismiss onboarding / start the runtime before sampling.
  for (const selector of clicks) {
    try {
      await page.click(selector, { timeout: 5000 });
    } catch (err) {
      consoleErrors.push(`click failed for ${selector}: ${String(err)}`);
    }
  }

  await page.waitForTimeout(probeMs);

  geometry = await page.evaluate(() => window.__summarizeGeometry(window.__geom));

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
      return window.__computeHueHistogram(data);
    }, HUE_SELECTOR);
  }

  if (wcag) {
    wcagResult = await page.evaluate(() => {
      const interactive = Array.from(document.querySelectorAll(
        'button, a[href], input, select, textarea, [role="button"], [tabindex]'
      ));
      const smallTargets = [];
      for (const el of interactive) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0 && (r.width < 24 || r.height < 24)) {
          smallTargets.push({
            tag: el.tagName.toLowerCase(),
            width: Math.round(r.width),
            height: Math.round(r.height),
          });
        }
      }
      let focusObscured = false;
      const focusable = document.querySelector('button, a[href], input, [tabindex]');
      if (focusable) {
        focusable.focus();
        const r = focusable.getBoundingClientRect();
        const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        focusObscured = Boolean(top) && top !== focusable && !focusable.contains(top);
      }
      return {
        targetSize: { minimumPx: 24, smallTargets },
        focusObscured,
        media: {
          prefersReducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
          prefersContrast: matchMedia('(prefers-contrast: more)').matches,
          forcedColors: matchMedia('(forced-colors: active)').matches,
        },
      };
    });
  }

  console.log(JSON.stringify({
    url: URL,
    threshold: THRESH,
    viewport,
    clicks,
    pageErrors,
    consoleErrors,
    requestFailures,
    geometry,
    hues,
    wcag: wcagResult,
  }, null, 2));
} finally {
  await browser.close();
}
