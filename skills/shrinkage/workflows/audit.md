# Workflow: Audit

<objective>
Produce the repo-wide (or subtree) ranked backlog of shrink opportunities —
SHRINK-PLAN.md — with evidence, tiers, and payoff estimates. The audit finds
and ranks; it does not cut. Execution happens through shave runs (or GSD
phases) consuming the plan.
</objective>

<process>
1. **Fresh map, full scope.** `codemap.py build` (or `scope <dir>`); note
   files collapsed by budget — for an audit, prefer raising the budget or
   auditing per-subtree so nothing hides in a collapsed file.

2. **Sweep by signal — run ALL of these, they find different things:**
   - **Dead-symbol sweep:** every `x0` symbol → C6 candidates
   - **Duplication sweep:** `codemap.py dupes` → C1/C9 candidates
   - **Structure sweep:** one-method classes, depth-1 no-override hierarchies,
     single-implementer `i` symbols → C3/C7
   - **Flag sweep:** grep known flag patterns; cross-check rollout state → C4
   - **Platform sweep:** walk `utils`/`helpers`/`lib` against the language's
     platform idioms (rules/<lang>.md) → C5
   - **Noise sweep:** commented-out blocks, stale TODOs → C10
   Subagents parallelize cleanly here: one sweep each, evidence-only briefs
   (see `agents/shrink-auditor.md`). **Inject the ledger** (`scripts/ledger.py`,
   file `references/ledger.md`) into every brief: `## keeps` (do NOT re-flag;
   re-verify only if explicitly asked) and `## frozen` (never a candidate). The
   map already drops `## excluded` globs, so phantom files never reach a sweep.
   Append new keeps and hidden-dependency discoveries back to the ledger — it
   outlives the per-audit plan.

   **Carry over a prior plan as explicit re-verify work (re-audit).** When a
   SHRINK-PLAN.md already exists, don't start from a blank sheet — its still-open
   rows are known candidates whose status may have changed. List them with
   `python3 $SKILL/scripts/plan.py open` and **partition those rows among the
   matching sweeps as explicit RE-VERIFY items** (a dead-symbol row → the
   dead-symbol sweep, a dupe row → the duplication sweep). Each carried row's
   brief says: re-confirm the evidence still holds and report the *current*
   state, specifically the things that go stale between audits — a baseline that
   was red is now green, a target that was DIRTY is now committed/clean, a ref
   count that moved, a keep that no longer applies. This makes carry-over
   systematic instead of a hand-written "RE-VERIFY these" list, and status
   changes get re-checked every audit rather than silently rotting. Use
   `plan.py carry <old-plan>` to seed the new plan skeleton from the still-open
   rows + ledger sections.

3. **Verify before ranking.** Ref counts and name matches are signals — each
   candidate gets a source-level look before it enters the plan (the auditor
   brief requires quoting the evidence). No candidate ships on map data alone.
   **Join coverage into the signal:** run `coverage_check.py` on candidate
   files — 0 refs AND uncovered is a much stronger dead-code case (nothing
   calls it, nothing tests it), while 0 refs but well-covered says the refs
   are hiding somewhere (fixtures, dynamic dispatch) — walk the checklist
   harder before believing it's dead.
   **No coverage report at all → suite-gated mode** (safety-model §4): don't
   cap the whole plan at T2. Declare the standing condition **once** in the plan
   header (see step 6) and then, per row, name the specific suite that would
   observe a regression in that target — put it in the **coverage** column as
   `gate: <suite>` (e.g. `gate: tests/Feature/InvoiceTest.php`). A row with no
   nameable observing suite stays T2. Naming "the tests" doesn't qualify — name
   the file/group that actually exercises the target.
   **Dirty check:** run `git status --porcelain -- <file>` per candidate. A
   target with uncommitted changes is marked **DIRTY** in its evidence column —
   the shave skips dirty targets by default (they're blocked on the user's
   in-flight work), so recording it here lets the plan hand them back cleanly
   instead of the shave re-discovering it item by item.

4. **Tier and estimate.** Per candidate: catalog entry, risk tier, estimated
   net LOC, effort (S/M/L), confidence (evidence completeness), and blast
   radius (callers, compat surface?). **Calibrate to history:** when `/srk:trend`
   shows a realization factor for a catalog, scale that catalog's estimates by
   it — C1/C9 dedupe merges routinely realize well under the naive line count
   (byte-identical-output constraints keep genuine divergences child-side; one
   deployment saw ~40% twice, another netted −70 est → +1 actual). `plan.py done`
   feeds this loop automatically (derives the actual from git).
   **C1/C9 specifically — price the NEW HOME, don't just count removed lines.**
   Net ≈ `N × block_LOC − (merged body + docblock + N call-lines)`, where the
   merged body is usually ≥ one block once it absorbs the variants; a documented
   shared home often nets ~0. So **rank C1/C9 by duplicate definitions
   collapsed and bug-surface removed** (the shared fix touches one place, not N),
   NOT by net LOC — otherwise a realization factor near 0 silently buries
   genuinely valuable merges. Put the collapse count (e.g. "9 defs → 4") in the
   row's evidence so payoff is legible without trusting the LOC number.

5. **Rank** by (payoff × confidence) / effort — with T0s first regardless
   (they're free wins that build trust in the process) and T2s last, each
   carrying its deprecation-cycle proposal.

6. **Write SHRINK-PLAN.md** (repo root, or `.planning/` in a GSD project).
   Stamp the current map fingerprint at the top so staleness is detectable —
   the startup line reads this to say "plan is stale, re-audit" when code has
   moved on. Get it from the codemap header (`| fp: XX␣`) or
   `codemap.py refresh`:

   ```
   <!-- map-fp: <12-char fingerprint from the codemap header> -->
   <!-- est-savings: <sum of the est. net LOC column, e.g. -1240> -->
   ```

   Stamp both reliably with `python3 $SKILL/scripts/plan.py restamp` (it reads
   the map fingerprint and sums the est. net LOC of the open rows) rather than
   hand-summing or sed. On a re-audit, `plan.py carry <old-plan>` emits a fresh
   skeleton of the still-open rows to build on.

   The `est-savings` total lets the session-start line show the headline
   ("~1240 LOC to reclaim") without re-reading the whole plan. Keep the tier
   letter (T0–T3) visible in each row so the startup line can summarize the
   mix (T0×3 T1×5 …).

   **When there's no coverage report,** state the suite-gated standing
   condition once, right under the stamps, so every row is read against it
   instead of repeating it per row:

   ```
   > **Tiering: suite-gated** (no coverage artifact in this repo). T0/T1 rows
   > execute only when the `coverage` column names an observing suite that runs
   > green before+after; rows with no nameable suite stay T2. (safety-model §4)
   ```

   Then the fixed schema so shaves can consume it mechanically — ranked table
   with EXACTLY these columns:

   ```
   | # | candidate | file:line | catalog | tier | est. net LOC | effort | confidence | coverage | evidence |
   ```

   followed by a `## Hidden dependencies discovered` section that future
   audits and shaves append to (reverted attempts land here), and a
   `## Deferred (T2)` section where each entry carries its deprecation-cycle
   proposal. This file is the audit's product and the shave's input.

   Close the plan with a **`## TODO before shaving`** checklist — the
   operator's gate for the whole shave cycle. Source items from: every entry in
   `## Bugs found` (fix-first), security/hygiene hazards the sweeps surfaced
   (secrets files in the tree, gitignore gaps), tooling/environment blockers (a
   stale plugin version, a red baseline that a planned row's gate needs green),
   and any ⚖ decision that gates a top-3 row. Each item is a checkbox written
   as a **paste-able imperative** — what, why it matters, and the exact action:

   ```
   ## TODO before shaving

   - [ ] **[bug]** Alpaca/IBKR `estimateFees()` reads wrong config keys — paper
         PnL is silently gross, not net. → Fix: wire the real keys; one labeled
         `fix:` commit covering both engines.
   - [ ] **[security]** `.env.backup-2026…` sits un-gitignored in the webroot,
         one `git add -A` from history. → Move it outside public_html or delete.
   - [ ] **[tooling]** Plugin cache shows 0.26.2; releases at 0.28.0. →
         `cd ~/.claude/plugins/marketplaces/<mp> && git pull`, reinstall, restart.
   ```

   Only genuine blockers belong here — bugs, security, tooling, prerequisites
   of planned rows. A deferred ⚖ decision that gates nothing executable stays in
   its own section; a padded TODO trains the operator to skip the list.

   Also include a **`## Bugs found (not shaves — fix-first, separate labeled
   commits)`** section. Audits routinely surface REAL defects that are explicitly
   *not* subtractions — a missing filter double-counting on a user-facing page, a
   null-guard divergence, a config key-name mismatch, a narrow-catch bug copied
   across N twins. These must never be folded into a `shrink:` commit (§7
   "never fix while shrinking"): they go here so the fix ships as its own labeled
   commit and downstream planners (GSD etc.) have a stable place to harvest fix
   work from. Each entry: `file:line`, one-line symptom, blast radius (user-facing?
   silent data error?). **Blocking-prerequisite rule:** when a dedupe/merge row
   touches code that has a bug listed here, the plan row names that bug as a
   blocking prerequisite — you fix the bug (separate commit) *before* merging the
   twins, or the merge bakes the bug into the surviving copy.

7. **Offer execution:** top T0/T1 items via `/srk:shave <target>` —
   or, in a GSD project, as planned phases so executors run them with fresh
   contexts and the verify step checks the scoreboard.

8. **Report in TWO sections — findings, then the gate.** The plan is the
   deliverable and it's on disk — do NOT paste the full ranked table. Keep it
   lean (raw sweep output stays in the subagents) and use exactly this shape:

   ```
   Results:
     <n> candidates: T0×a T1×b executable now (≈ −X LOC) · T2×c deferred (≈ −Y behind your decisions)
     top 3 by payoff: ① <candidate, est, one-line why> ② … ③ …
     <one line each, only if present: bugs found ×n · ledger updates ×n>
     full plan: SHRINK-PLAN.md

   TODO before advancing — do these BEFORE any shave (paste an item to the AI, or do it by hand):
     1. [bug] <what + why it matters> → <exact action / fix as its own labeled commit>
     2. [security] <what> → <exact action>
     3. [tooling] <what> → <exact commands>
   ⚠ Do NOT start /srk:shave until this list is clear — shaving over an unfixed
   bug bakes it into consolidated code, and an open hazard outlives the batch.
   Say "shave anyway" to waive explicitly.
   ```

   The TODO section mirrors the plan's `## TODO before shaving` checklist, one
   numbered line per item, every line an imperative the operator can paste
   verbatim to an AI session. Empty checklist → say "no blockers — shave when
   ready" and lead the Next block with `/srk:shave 1` instead.
</process>

End with a terse result line + a **Next** block that LEADS with the one concrete action to take now, as a plain imperative — including a non-`srk` step (commit or stash in-flight work, land the branch, adjudicate a ⚖ item) when that's the real next move — then ≤2 alternatives (command file's <next> block + SKILL.md "Response style"). Never a bare command menu or a buried "becomes executable after…". No wall of prose.

<success_criteria>
- [ ] All six sweeps ran (or skipped with stated reason)
- [ ] Every plan entry: catalog #, tier, net-LOC estimate, effort, confidence
- [ ] Zero candidates ranked on map evidence alone
- [ ] SHRINK-PLAN.md written and self-contained (evidence travels with it)
- [ ] T2 items carry deprecation-cycle proposals, not deletion proposals
</success_criteria>
