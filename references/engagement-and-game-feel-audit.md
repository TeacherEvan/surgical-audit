# Engagement & Game-Feel Audit (the 11th lens)

The ten lenses in SKILL.md audit *correctness*. None of them will tell you the product is not fun, and a repo can score HIGH on every one of them while shipping a flat experience. Use this file when the user's question is about excitement, juice, retention, "what popular practice am I neglecting", or any kid-/consumer-facing interactive surface.

This lens runs **after** Pass 2, reusing the same hotspot files. It does not need a separate scan.

---

## 1. The signature finding: authored but unwired

The most common engagement defect is not a missing feature. It is a **finished feature connected to nothing**. Someone wrote the content, typed the state, added the prop and the styles, and the last wire was never run — usually because the work spanned several sessions and each assumed another had finished it.

Detect it in three passes, cheapest first.

### 1a. Dead-export sweep

```bash
python3 <skill>/scripts/dead_export_sweep.py <repo> --src src
```

A whole engagement module — combo levels, power-up table, milestone list, near-miss messages — returning zero external references is the tell. These modules type-check, may own a green test suite, and never execute.

### 1b. Field triage on the state object

For every field that looks like a reward (`multiplier`, `streak`, `lastMilestone`, `activePowerUps`, `combo`), count **writes and reads separately**:

```bash
grep -rn "multiplier" src --include=*.ts --include=*.tsx
```

- Initialised and never written → the feature is disconnected.
- Written and never read → the same bug from the other end.
- Both → the reward curve is a constant, whatever the UI claims.

The give-away pattern is a field with exactly two hits: its initialiser and its type declaration.

### 1c. Three-break check on every user-visible affordance

For a badge, HUD element or celebration, verify each link **separately**. Each break is sufficient alone, and they co-occur because they landed in different sessions:

| Link | Check | Failure |
| :--- | :--- | :--- |
| **computed** | the helper is imported and called | pure constant |
| **passed** | `propname=` appears in JSX at the call site | optional prop, never supplied |
| **rendered** | the render condition is reachable | dead JSX |

An optional prop that no call site passes will type-check forever and render nothing. Search for `propname=` in the component tree, not `propname` in the type definitions.

---

## 2. Feedback-channel matrix

Every input needs **at least two** simultaneous channels. One is not feedback, it is a log line. With sound muted — normal in a classroom, and a managed-browser default — audio-only feedback means the user cannot distinguish a hit from a miss.

```bash
grep -rn ":active" src --include=*.css | wc -l        # visual press state
grep -rni "navigator.vibrate\|Haptics" src | wc -l    # haptic
grep -rn "playbackRate" src                           # per-hit audio variation
```

Zero `:active` rules and zero haptics are two entire channels missing, and both are cheap. Also check *duration*: an entity removed from state in the same frame as the tap has no post-hit acknowledgement at all — nothing survives long enough to animate.

When adding a channel, respect reduced motion: a press-state transform is a static state change and survives it; a new animation does not. Guard new motion, keep new state.

---

## 3. Difficulty arc — arithmetic, not vibes

Two checks catch most dead ramps:

1. **Is the curve called?** A `calculateSpawnInterval` / `calculateSpeed` helper with zero call sites while the scheduler hardcodes a literal is a flat difficulty curve with a control panel that does nothing. Grep the helper name across production code, not just tests.
2. **Is the configured ceiling reachable?** Compute the maximum the curve can return over the real input domain. `min(1 + floor(progress / 10) * 0.03, 1.8)` with `progress <= 100` tops out at `1.3` — the `1.8` is unreachable by construction. That is dead config pretending to be a ramp.
3. **Check the edges.** Unclamped negative progress can *invert* the curve: slower than the configured floor, or a spawn interval **longer** than the configured base. Clamping input is part of the fix, not a nicety.

State the arc as numbers (interval and speed at 0 % vs 100 %) so the user can see whether minute three differs from minute one.

---

## 4. Progression and the win moment

- **What survives a reload?** If settings persist but achievement does not, there is no mastery loop and no reason to replay a level. Check `localStorage`/IndexedDB keys for anything resembling stars, unlocks or best-score; a single "high score time" is not progression.
- **Score, stars, accuracy.** A progress bar that only runs 0→100 has nothing to beat. Look for any rating derived from errors and elapsed time.
- **The win screen** is the payoff and is usually the least-produced screen in the product: look for stats, a next-level CTA, and an auto-close timer that dismisses the reward before it can be read.
- **Does winning advance the level?** A completion that returns the user to a menu dead-ends the loop.

---

## 5. Report shape

Do not report a feature wish-list. Report a **coverage table**, because the actionable distinction is wired / authored-but-dead / absent:

| Practice | State | Evidence |
| :--- | :--- | :--- |
| Escalating combo | authored, not wired | `combo-levels.ts` (97 LOC), 0 external refs |
| Touch acknowledgement | absent | 0 `:active` rules in any stylesheet |
| Haptics | absent | 0 references, platform plugin already installed |
| Difficulty ramp | absent | interval hardcoded at call site; curve helper unused |
| Win celebrations | wired | `FireworksDisplay`, referenced from the app root |

Then quantify the cheap half, because it reprioritises the whole backlog: *"five of the six biggest levers are already written and connected to nothing; most of this is integration work, not new design."*

---

## 6. Pitfalls

- **Do not recommend building what exists.** The first draft of the fix list is usually wrong: the combo system, power-ups and milestones are already authored. Lead with "wire it", and reserve new-build recommendations for genuinely absent channels.
- **Cosmetic wiring is still a real win, and often the right first step.** A multiplier that only drives a badge and a pitch lift — without touching progress maths — delivers most of the felt improvement, changes no balance, and cannot break a level-length test. Say so, and leave the balance decision with the user.
- **Never multiply the score/progress as a side effect of wiring.** Changing how fast a level completes silently retunes the whole game and invalidates existing length assertions. Wire the display and the escalation; propose the maths change separately.
- **Reduced motion is a channel constraint, not a checkbox.** A static state change (colour, scale, outline) reads under reduced motion; a transition or keyframe does not. Keep the state, drop the animation.
- **A settings toggle that writes a class the stylesheet does not match is dead**, and it is easy to miss because the OS-preference path may write the same class to a *different* element and work correctly. When an accessibility toggle appears to do nothing, grep for who sets the class and who matches it, on which element.
