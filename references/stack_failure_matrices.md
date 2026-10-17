# Principal-Engineer Stack & Engine Failure Matrices

Consult the relevant domain matrix below during **Pass 2 (The 10-Principal-Engineer Deep Audit)** to catch stack-specific, high-severity defects that generic code reviews miss.

---

## Matrix A: 2D/3D Game Engines, Physics Loops & Shaders (WebGL/GLSL, Canvas, Pygame, Godot, Unity)

### 1. Frame-Time & Delta-Time (`dt`) Mathematical Integrity
- **Variable Frame-Rate Damping Bug:** Flag exponential decay written as `velocity *= 0.95` inside `requestAnimationFrame` / `_process(delta)` / `Update()`. On a 144Hz monitor or 120Hz mobile screen, damping occurs 2.4x faster than at 60Hz.
  - *Required Fix Pattern:* Frame-rate independent damping: `velocity *= Math.pow(0.95, dt * 60)` or `velocity = lerp(velocity, target, 1.0 - Math.exp(-decayRate * dt))`.
- **Unclamped Delta-Time Tunneling (Spiral of Death):** When a browser tab loses focus or a mobile device stutters, `dt` spikes to `>0.5s` (500ms). Multiplying `position += velocity * dt` teleports entities through thin collision walls.
  - *Required Fix Pattern:* Clamp `const safeDt = Math.min(dt, 0.05)` (max 50ms) or use a fixed-timestep accumulator (`FIXED_DT = 1 / 60`) with render interpolation alpha.
- **Zero-Vector Normalization NaN Poisoning:** Calculating unit direction vectors `dx / dist` when two entities occupy the exact same coordinates (`dist === 0`) produces `NaN`, permanently poisoning position/velocity state and making sprites vanish.
  - *Required Fix Pattern:* Guard with `const distSq = dx * dx + dy * dy; if (distSq > 1e-8) { const invDist = 1.0 / Math.sqrt(distSq); ... }`.

### 2. Garbage Collection (GC) Stutter & Hot-Loop Allocation Traps
- **Per-Frame Heap Churn (`>16.67ms` Frame Budget Violation):** Flag any instantiation inside 60–120Hz loops (`new Vector2()`, `new Color()`, `.map()`, `.filter()`, `[...arr]`, object literals `{ x, y }`, or template strings for HUD text that hasn't changed).
  - *Required Fix Pattern:* Pre-allocate scratch vectors/arrays at module/class init, mutate in-place, and use a fixed-capacity ring buffer or Object Pool (`acquire()` / `release()`) for particles, projectiles, and floating combat text.
- **O(N^2) All-Pairs Collision Scans:** Nested loops testing every entity against every other entity without broad-phase filtering or using `Math.sqrt()` inside the inner loop.
  - *Required Fix Pattern:* Use squared distance comparisons (`dx*dx + dy*dy < (r1+r2)*(r1+r2)`) and partition space via a uniform 2D Spatial Hash Grid or Quadtree when $N > 32$.

### 3. WebGL / GLSL / HTML5 Canvas & Audio Lifecycle Leaks
- **Mobile Fragment Shader Float Precision Collapse:** Using `precision mediump float;` (16-bit FP16, max value `65504`, 10-bit mantissa) for `u_time` or world coordinates causes visible stepping/jitter after `~180` seconds on mobile GPUs (Adreno/Mali/Apple).
  - *Required Fix Pattern:* Use `precision highp float;` or wrap `u_time = mod(rawTime, 3600.0)` on the CPU before uniform upload.
- **GPU & WebAudio Resource Leaks on Scene/Component Unmount:** Recreating `gl.createTexture()`, `gl.createBuffer()`, `gl.createProgram()`, or `new AudioContext()` on level restart without explicit `.deleteTexture()` / `.close()`, exhausting mobile VRAM or hitting the browser's 6-AudioContext hardware limit.
- **High-DPI (`devicePixelRatio`) Blur & Input Coordinate Desync:** Setting `<canvas width>` equal to CSS pixels without scaling by `Math.min(window.devicePixelRatio || 1, 2)`, or failing to transform `PointerEvent.clientX/Y` via `getBoundingClientRect()` ratio when the canvas is letterboxed.

---

## Matrix B: Reactive Web Apps, Next.js, Svelte, React & Serverless/BaaS (Convex / Supabase / Node)

### 1. AI "Split-Brain" State & Hydration Desync
- **Derived State Synchronization Anti-Pattern:** AI-generated code frequently stores props or server queries into local `useState` and synchronizes them via `useEffect`, causing a 1-frame stale render, cascading re-renders, or infinite loops.
  - *Required Fix Pattern:* Compute derived values inline during render (`useMemo` only if $>O(N \log N)$) and maintain a Single Source of Truth.
- **SSR / Client Hydration Mismatch:** Reading `window.innerWidth`, `localStorage`, `Date.now()`, or `Math.random()` directly during initial component render in Next.js/SvelteKit, breaking SSR hydration or flashing layout shifts.
- **Stale Closure Capture in Event Listeners & Intervals:** Registering `window.addEventListener` or `setInterval` inside `useEffect(fn, [])` with an empty dependency array while reading React state variables inside `fn`, locking the callback to the initial render's state forever.

### 2. Backend/Database Concurrency, Cost & Trust Boundaries
- **Unbounded Table Scans & Bandwidth Bombs:** Calling `.collect()` in Convex or `SELECT *` without `.withIndex()` and `.take(limit)`, which works in local testing with 20 rows but hits execution memory/time limits in production with 10,000 rows.
- **Client-Authoritative Trust Flaws:** Trusting client-supplied scores, currency deltas, timestamps, or role flags (`isAdmin`, `payRate`, `hoursLogged`) in mutation payloads instead of deriving identity from `ctx.auth.getUserIdentity()` and validating invariants server-side.
- **TOCTOU (Time-of-Check to Time-of-Use) Race Conditions:** Non-transactional read-then-write flows (e.g., checking if a class slot or payroll entry exists, awaiting an external fetch, then inserting) that create duplicate records on double-click or network retry.

---

## Matrix C: Python, C++, CLI Tools, Linux/PRoot Environments & Autonomous Agents

### 1. Subprocess, Filesystem & Sandbox Integrity
- **Non-Atomic File Writes (Data Corruption on Crash/OOM):** Writing state, JSON configs, or spreadsheets directly via `open(target, "w")` instead of writing to a sibling temporary file + `os.fsync()` + `os.replace(tmp, target)`.
- **Path Traversal & Symlink Sandbox Escapes:** Using `str.startswith()` to validate directory containment (`if file_path.startswith(workspace_dir)`), which is trivially bypassed via `../` or symlinks (`Path(p).resolve().is_relative_to(Path(root).resolve())` is required).
- **Shell Injection & Zombie Subprocesses:** Passing interpolated strings to `subprocess.Popen(..., shell=True)` or `child_process.exec()`, or failing to set `timeout=` and clean up process groups (`os.killpg`) when a child CLI hangs.

### 2. Python / C++ Runtime Footguns
- **Python Mutable Default Arguments & Late-Binding Closures:** `def add_item(item, bucket=[]):` sharing state across invocations, or lambdas inside loops (`[lambda: process(x) for x in items]`) all binding to the final value of `x`.
- **Asyncio Event Loop Blocking:** Calling synchronous `requests.get()`, `time.sleep()`, or heavy CPU/disk I/O inside an `async def` coroutine without `asyncio.to_thread()`, freezing the entire agent/server event loop.
- **C++ / Native Memory & UB Hazards:** Dangling references to `std::vector` elements across `push_back()` reallocations, signed integer overflow UB, virtual destructor omission on polymorphic base classes, and uninitialized struct fields.
