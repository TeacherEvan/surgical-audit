# Test Suite Comparison & Mental Mutation Testing Rubric

Use this rubric during **Pass 3 (Existing Test Suite Comparison & Mental Mutation Analysis)** to rigorously evaluate whether existing tests verify actual behavior or merely provide false confidence ("green checkmark theater").

---

## 1. The 6 Vibe-Coded Test Pathologies

When AI coding assistants write tests alongside implementation code, they systematically introduce six defects. Audit every test file against these patterns:

1. **The Mock-Mirror Tautology (Testing the Mock, Not the Code):**
   - *Symptom:* The test mocks the database/API/physics module to return `{ status: "ok", score: 100 }`, calls a thin wrapper, and asserts `expect(res.score).toBe(100)`.
   - *Diagnosis:* `0%` real logic verification. If the underlying query syntax, schema field name, or math formula breaks, the test still passes.
2. **Weak / Existence-Only Assertions ("No-Throw Theater"):**
   - *Symptom:* Tests that only assert `expect(result).toBeDefined()`, `expect(component).toBeTruthy()`, or `assert res is not None` without checking exact state values, invariants, or side effects.
3. **Happy-Path Tunnel Vision:**
   - *Symptom:* 100% of test cases pass valid, well-formed, positive numbers and non-empty arrays. Zero tests exercise `null`/`undefined`/`None`, empty arrays `[]`, `0`, `-1`, `NaN`, `Infinity`, malformed JSON, network timeouts (`500`/`429`), or unauthorized users.
4. **Shared Mutable Test State (Order-Dependent Flakiness):**
   - *Symptom:* Global singletons, module-level caches, `localStorage`, or system clocks (`Date.now()`) are mutated in Test A and never reset in `beforeEach`/`afterEach`, causing tests to pass in isolation but fail under parallel or shuffled execution.
5. **Implementation-Coupled Brittle Assertions:**
   - *Symptom:* Asserting exact internal private method call counts (`expect(spy).toHaveBeenCalledTimes(3)`) instead of observable state outputs, making safe refactoring impossible without breaking tests.
   - *Data-array variant:* Asserting a literal snapshot of a shipped data array (`expect(palette).toEqual(['#00f0ff', ...])`) enforces the array's *shape*, not its *intent* — adding a missing colour family fails the test, while shipping a palette with no red passes it. Assert the property the array exists to satisfy (hue-band coverage, saturation floor, contrast ratio) and keep exact brand tokens in a separate check when the values matter.
   - *Canvas-stub variant:* A stub context of `vi.fn()` for `moveTo`/`lineTo` discards coordinates, so a 1,440 px streak and a 2 px stroke are the same call. Geometry bugs survive a green suite unless the test records coordinates and asserts on distances.
6. **Time-Window Myopia (Sampling Shorter Than the Defect):**
   - *Symptom:* A periodic defect with an 8 s period is tested with a 5–6 s sample, or a single sample taken after "the system settled". The test passes against the broken build because it never observed the failing phase.
   - *Diagnosis:* Name the period the bug lives on (animation cycle, timer sweep, cache invalidation) and check the sample covers at least two full periods. If not, the test cannot kill the mutant — compress the timing through the runtime config or lengthen the window.
   - *Fix shape:* sample the transition windows explicitly (startup burst, end-of-cycle blank, eviction) and assert the failure mode directly (`min > 0`, `max <= capacity`) instead of a proxy (`element exists`, `panel is visible`).

---

## 1a. Regression Test Acceptance Gate

A test written alongside a fix is only a regression test if it would have failed before the fix. Before reporting a fix as done, answer all four:

1. **What exactly turns red on the pre-fix code?** Name the assertion and the pre-fix value it would have observed. If the assertion only proves the feature exists, it is smoke, not a regression.
2. **Does the sample span the defect's period?** Two full cycles minimum; compress timings through the runtime config when the real period is slow.
3. **Does it assert the invariant, not the implementation?** "No two entities overlap" survives a rewrite; "the sampler ran 15 times" does not.
4. **Would a plausible alternative fix also pass?** If any implementation change passes, the test guards presence rather than correctness.

A fix whose only evidence is "the suite is green" has not been verified — the suite was green before the fix too.

---

## 2. Mental Mutation Testing Protocol (Calculating Mutation Kill Rate)

Line coverage measures which lines *executed*, not which bugs are *caught*. For every core implementation function that has an existing test, apply **4 Mental Mutants** and trace whether the existing test suite would fail (Killed) or still pass (Survived):

| Mutant ID | Mutation Operator | Concrete Transformation | Question to Answer |
| :--- | :--- | :--- | :--- |
| **M1 (Boundary Flip)** | Relational boundary shift | Change `<` to `<=` or `>` to `>=` at loop/condition edges | Does an existing test assert the exact boundary value $N$ vs $N-1$? |
| **M2 (Zero/Empty Degeneracy)** | Collection/Scalar collapse | Pass `[]`, `""`, `0`, or `dt = 0.0` into the function | Does an existing test verify graceful handling without `ZeroDivisionError` / `NaN` / `IndexError`? |
| **M3 (Side-Effect Deletion)** | State commit removal | Comment out the state update, cleanup call, or DB index filter | Would any assertion in the test file actually turn red? |
| **M4 (Async Failure Injection)** | Promise/I/O rejection | Force the awaited dependency to throw/reject | Is there a negative test verifying rollback, retry, or structured error state? |

### Estimating the Mutation Kill Score ($M_{\text{kill}}$)
Compute the estimated Mutation Kill Score across sampled critical functions:
$$M_{\text{kill}} = \frac{\text{Total Mutants Killed by Existing Assertions}}{\text{Total Mutants Evaluated}} \times 100\%$$

- **$M_{\text{kill}} \ge 80\%$:** Hardened, high-signal test suite.
- **$40\% \le M_{\text{kill}} < 80\%$:** Partial coverage; boundary and error-path blind spots exist.
- **$M_{\text{kill}} < 40\%$ (or no tests):** False-confidence / hollow test suite. Treat modules as effectively unprotected during refactoring.

---

## 3. Minimal Viable Test Harness (MVTH) Blueprint (When Coverage is 0% or Hollow)

Never recommend writing 100 boilerplate unit tests for UI markup. Prioritize the highest-ROI test pyramid in the Markdown report:

1. **Tier 1 — Pure Core & Math Invariants (Highest ROI, Zero Mocks):**
   - Physics/collision calculations, scoring/grading/payroll formulas, state machine transition reducers, and schema parsers.
   - Recommend **Property-Based / Table-Driven Tests** (`pytest.mark.parametrize` or `test.each([...])`) covering `[min, -1, 0, 1, boundary, max, NaN/None]`.
2. **Tier 2 — State Machine & Concurrency Integration Tests:**
   - Multi-step state transitions (e.g., `IDLE -> RUNNING -> PAUSED -> GAME_OVER -> RESET`), verifying that `RESET` restores exact initial memory and listener counts (`listenerCount(after) == listenerCount(before)`).
3. **Tier 3 — Smoke & Contract Boundaries:**
   - API/database mutation round-trips with invalid payloads and unauthorized contexts.
4. **Tier 0 — Pure Geometry/Invariant Proofs (when the bug was spatial):**
   - Extract the maths into pure functions over measured inputs, then assert structural invariants exhaustively (`for every slot pair: boxes do not intersect`). These run in milliseconds with no browser, which is what makes them survive as CI guards instead of flaking out.
