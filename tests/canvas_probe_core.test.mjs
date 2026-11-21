import assert from 'node:assert/strict';
import test from 'node:test';
import {
  computeHueHistogram,
  installCanvasGeometryHook,
  summarizeGeometry,
} from '../scripts/canvas_probe_core.mjs';

function makeEnv(threshold = 300) {
  class FakeCtx {
    constructor(id, scaleX = 1) {
      this.canvas = { id };
      this._sx = scaleX;
    }
    getTransform() { return { a: this._sx, b: 0, c: 0, d: 1, e: 0, f: 0 }; }
    beginPath() {} closePath() {} moveTo() {} lineTo() {}
    quadraticCurveTo() {} bezierCurveTo() {} rect() {}
    stroke() {} strokeRect() {} fill() {} clip() {}
  }
  class FakePath2D { moveTo() {} lineTo() {} rect() {} }
  const store = {};
  installCanvasGeometryHook(FakeCtx.prototype, FakePath2D, threshold, store);
  return { FakeCtx, FakePath2D, store };
}

test('rect() followed by clip() or fill() emits zero stroked artefacts', () => {
  const { FakeCtx, store } = makeEnv(300);
  const ctx = new FakeCtx('bg');
  ctx.beginPath();
  ctx.rect(0, 0, 1440, 900);
  ctx.clip();
  ctx.fill();
  assert.deepEqual(summarizeGeometry(store), {});
});

test('rect() + stroke() reports four full-span edges', () => {
  const { FakeCtx, store } = makeEnv(300);
  const ctx = new FakeCtx('grid');
  ctx.beginPath();
  ctx.rect(0, 0, 1440, 900);
  ctx.stroke();
  const s = summarizeGeometry(store).grid;
  assert.equal(s.segments, 4);
  assert.equal(s.rectEdges, 4);
  assert.equal(s.horizontal, 2);
  assert.equal(s.vertical, 2);
  assert.equal(s.longest, 1440);
});

test('strokeRect() commits edges without a prior rect()', () => {
  const { FakeCtx, store } = makeEnv(300);
  const ctx = new FakeCtx('frame');
  ctx.strokeRect(0, 0, 800, 600);
  const s = summarizeGeometry(store).frame;
  assert.equal(s.segments, 4);
  assert.equal(s.rectEdges, 4);
  assert.equal(s.longCount, 4);
});

test('getTransform() scales distances and Path2D strokes are tracked', () => {
  const { FakeCtx, FakePath2D, store } = makeEnv(300);
  const ctx = new FakeCtx('trail', 2);
  const path = new FakePath2D();
  path.moveTo(0, 10);
  path.lineTo(200, 10); // 400px after 2x transform
  ctx.stroke(path);
  const s = summarizeGeometry(store).trail;
  assert.equal(s.longCount, 1);
  assert.equal(s.horizontal, 1);
  assert.equal(s.longest, 400);
});

test('beginPath() discards pending segments from a prior un-stroked path', () => {
  const { FakeCtx, store } = makeEnv(300);
  const ctx = new FakeCtx('reset');
  ctx.moveTo(0, 0);
  ctx.lineTo(2000, 0); // pending, never stroked
  ctx.beginPath(); // discard
  ctx.moveTo(0, 0);
  ctx.lineTo(10, 0);
  ctx.stroke();
  const s = summarizeGeometry(store).reset;
  assert.equal(s.segments, 1);
  assert.equal(s.longCount, 0);
});

test('multi-canvas WeakMap isolates contexts and hue histogram classifies bands', () => {
  const { FakeCtx, store } = makeEnv(300);
  const c1 = new FakeCtx('one');
  const c2 = new FakeCtx('two');
  c1.moveTo(0, 0);
  c2.moveTo(900, 900);
  c1.lineTo(10, 0);
  c1.stroke();
  assert.equal(summarizeGeometry(store).one.longCount, 0);
  assert.equal(summarizeGeometry(store).two, undefined);

  const rgba = new Uint8ClampedArray([
    255, 0, 0, 255, 0, 255, 255, 255, 128, 128, 128, 255,
  ]);
  const hist = computeHueHistogram(rgba);
  assert.equal(hist.vivid, 2);
  assert.equal(hist.hueBands.red, 50);
  assert.equal(hist.hueBands.cyan, 50);
});
