/**
 * canvas_probe_core.mjs (v3.0.0) — pure, browser-free Canvas geometry + hue core.
 *
 * Stroke-gated geometry: path segments are buffered per context (WeakMap) and
 * committed ONLY on stroke() / strokeRect() / stroke(Path2D). A rect() used for
 * clip() or fill() therefore produces zero artefact counts, fixing the v2.4
 * false positive where path construction incremented counters immediately.
 *
 * Exports are pure functions so `node --test tests/canvas_probe_core.test.mjs`
 * exercises real behaviour with no Playwright/browser dependency.
 */

export const HUE_BAND_NAMES = Object.freeze([
  'red', 'orange', 'amber', 'lime', 'green', 'spring',
  'cyan', 'azure', 'blue', 'violet', 'magenta', 'pink',
]);

export function installCanvasGeometryHook(ctxProto, Path2DCtor, threshold, store) {
  const pendingByCtx = new WeakMap();
  const path2DSegments = new WeakMap();
  const canvasIds = new WeakMap();
  let nextAnonId = 1;

  const ctxId = (ctx) => {
    const canvas = ctx && ctx.canvas;
    if (!canvas) return 'detached-ctx';
    if (canvas.id) return canvas.id;
    let assigned = canvasIds.get(canvas);
    if (!assigned) {
      assigned = `anon-canvas-${nextAnonId++}`;
      canvasIds.set(canvas, assigned);
    }
    return assigned;
  };

  const mapPt = (ctx, x, y) => {
    if (ctx && typeof ctx.getTransform === 'function') {
      const m = ctx.getTransform();
      return { x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f };
    }
    return { x, y };
  };

  const bucket = (id) =>
    (store[id] = store[id] || {
      count: 0, longest: 0, longCount: 0,
      horizontal: 0, vertical: 0, rectEdges: 0, sample: [],
    });

  const commitSegment = (id, dx, dy, isRectEdge = false) => {
    if (!Number.isFinite(dx) || !Number.isFinite(dy)) return;
    const b = bucket(id);
    const len = Math.hypot(dx, dy);
    b.count += 1;
    if (isRectEdge) b.rectEdges += 1;
    if (len > b.longest) b.longest = len;
    if (len > threshold) {
      b.longCount += 1;
      if (dx > dy * 4) b.horizontal += 1;
      if (dy > dx * 4) b.vertical += 1;
      if (b.sample.length < 4) b.sample.push(Math.round(len));
    }
  };

  const getPending = (map, key) => {
    let state = map.get(key);
    if (!state) {
      state = { cursor: null, segments: [] };
      map.set(key, state);
    }
    return state;
  };

  const pushEdge = (state, p0, p1, isRectEdge = false) => {
    state.segments.push({ p0, p1, isRectEdge });
  };

  const orig = {
    beginPath: ctxProto.beginPath,
    closePath: ctxProto.closePath,
    moveTo: ctxProto.moveTo,
    lineTo: ctxProto.lineTo,
    quadraticCurveTo: ctxProto.quadraticCurveTo,
    bezierCurveTo: ctxProto.bezierCurveTo,
    rect: ctxProto.rect,
    stroke: ctxProto.stroke,
    strokeRect: ctxProto.strokeRect,
  };

  ctxProto.beginPath = function () {
    pendingByCtx.delete(this);
    return orig.beginPath.call(this);
  };

  ctxProto.moveTo = function (x, y) {
    const p = mapPt(this, x, y);
    getPending(pendingByCtx, this).cursor = { startX: p.x, startY: p.y, x: p.x, y: p.y };
    return orig.moveTo.call(this, x, y);
  };

  const hookSegmentMethod = (name, coordSelector) => {
    ctxProto[name] = function (...args) {
      const [x, y] = coordSelector(args);
      const p = mapPt(this, x, y);
      const state = getPending(pendingByCtx, this);
      if (state.cursor) {
        pushEdge(state, { x: state.cursor.x, y: state.cursor.y }, p);
        state.cursor.x = p.x;
        state.cursor.y = p.y;
      } else {
        state.cursor = { startX: p.x, startY: p.y, x: p.x, y: p.y };
      }
      return orig[name].apply(this, args);
    };
  };

  hookSegmentMethod('lineTo', (a) => [a[0], a[1]]);
  hookSegmentMethod('quadraticCurveTo', (a) => [a[2], a[3]]);
  hookSegmentMethod('bezierCurveTo', (a) => [a[4], a[5]]);

  ctxProto.closePath = function () {
    const state = pendingByCtx.get(this);
    if (state && state.cursor) {
      const target = { x: state.cursor.startX, y: state.cursor.startY };
      pushEdge(state, { x: state.cursor.x, y: state.cursor.y }, target);
      state.cursor.x = target.x;
      state.cursor.y = target.y;
    }
    return orig.closePath.call(this);
  };

  ctxProto.rect = function (x, y, w, h) {
    const state = getPending(pendingByCtx, this);
    const p0 = mapPt(this, x, y);
    const p1 = mapPt(this, x + w, y);
    const p2 = mapPt(this, x + w, y + h);
    const p3 = mapPt(this, x, y + h);
    pushEdge(state, p0, p1, true);
    pushEdge(state, p1, p2, true);
    pushEdge(state, p2, p3, true);
    pushEdge(state, p3, p0, true);
    state.cursor = { startX: p0.x, startY: p0.y, x: p0.x, y: p0.y };
    return orig.rect.call(this, x, y, w, h);
  };

  ctxProto.stroke = function (path) {
    const id = ctxId(this);
    if (path && path2DSegments.has(path)) {
      for (const seg of path2DSegments.get(path).segments) {
        const a = mapPt(this, seg.p0.x, seg.p0.y);
        const b = mapPt(this, seg.p1.x, seg.p1.y);
        commitSegment(id, Math.abs(b.x - a.x), Math.abs(b.y - a.y), seg.isRectEdge);
      }
    } else {
      const state = pendingByCtx.get(this);
      if (state) {
        for (const seg of state.segments) {
          commitSegment(
            id,
            Math.abs(seg.p1.x - seg.p0.x),
            Math.abs(seg.p1.y - seg.p0.y),
            seg.isRectEdge,
          );
        }
      }
    }
    return orig.stroke.apply(this, arguments);
  };

  ctxProto.strokeRect = function (x, y, w, h) {
    const id = ctxId(this);
    const p0 = mapPt(this, x, y);
    const p1 = mapPt(this, x + w, y);
    const p2 = mapPt(this, x + w, y + h);
    const p3 = mapPt(this, x, y + h);
    commitSegment(id, Math.abs(p1.x - p0.x), Math.abs(p1.y - p0.y), true);
    commitSegment(id, Math.abs(p2.x - p1.x), Math.abs(p2.y - p1.y), true);
    commitSegment(id, Math.abs(p3.x - p2.x), Math.abs(p3.y - p2.y), true);
    commitSegment(id, Math.abs(p0.x - p3.x), Math.abs(p0.y - p3.y), true);
    return orig.strokeRect.call(this, x, y, w, h);
  };

  if (Path2DCtor && Path2DCtor.prototype) {
    const pProto = Path2DCtor.prototype;
    const pMove = pProto.moveTo;
    const pLine = pProto.lineTo;
    const pRect = pProto.rect;
    pProto.moveTo = function (x, y) {
      getPending(path2DSegments, this).cursor = { startX: x, startY: y, x, y };
      return pMove.call(this, x, y);
    };
    pProto.lineTo = function (x, y) {
      const st = getPending(path2DSegments, this);
      if (st.cursor) {
        pushEdge(st, { x: st.cursor.x, y: st.cursor.y }, { x, y });
        st.cursor.x = x;
        st.cursor.y = y;
      } else {
        st.cursor = { startX: x, startY: y, x, y };
      }
      return pLine.call(this, x, y);
    };
    pProto.rect = function (x, y, w, h) {
      const st = getPending(path2DSegments, this);
      const p0 = { x, y };
      const p1 = { x: x + w, y };
      const p2 = { x: x + w, y: y + h };
      const p3 = { x, y: y + h };
      pushEdge(st, p0, p1, true);
      pushEdge(st, p1, p2, true);
      pushEdge(st, p2, p3, true);
      pushEdge(st, p3, p0, true);
      st.cursor = { startX: x, startY: y, x, y };
      return pRect.call(this, x, y, w, h);
    };
  }
}

export function computeHueHistogram(data) {
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
      bands.map((c, i) => [HUE_BAND_NAMES[i], +((c / Math.max(1, vivid)) * 100).toFixed(1)]),
    ),
  };
}

export function summarizeGeometry(store) {
  const out = {};
  for (const [id, b] of Object.entries(store || {})) {
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
}
