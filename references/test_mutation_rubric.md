# Test Suite Comparison & Mental Mutation Testing Rubric

Use this rubric during **Pass 3 (Existing Test Suite Comparison & Mental Mutation Analysis)** to rigorously evaluate whether existing tests verify actual behavior or merely provide false confidence ("green checkmark theater").

---

## 1. The 5 Vibe-Coded Test Pathologies

When AI coding assistants write tests alongside implementation code, they systematically introduce five defects. Audit every test file against these patterns:

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
