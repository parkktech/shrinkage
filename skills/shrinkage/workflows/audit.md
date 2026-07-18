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

3. **Verify before ranking.** Ref counts and name matches are signals — each
   candidate gets a source-level look before it enters the plan (the auditor
   brief requires quoting the evidence). No candidate ships on map data alone.
   **Join coverage into the signal:** run `coverage_check.py` on candidate
   files — 0 refs AND uncovered is a much stronger dead-code case (nothing
   calls it, nothing tests it), while 0 refs but well-covered says the refs
   are hiding somewhere (fixtures, dynamic dispatch) — walk the checklist
   harder before believing it's dead.
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
   deployment saw ~40% twice). `/srk:score --log --cat C<n> --est <n>` at shave
   time feeds this loop.

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

   Then the fixed schema so shaves can consume it mechanically — ranked table
   with EXACTLY these columns:

   ```
   | # | candidate | file:line | catalog | tier | est. net LOC | effort | confidence | coverage | evidence |
   ```

   followed by a `## Hidden dependencies discovered` section that future
   audits and shaves append to (reverted attempts land here), and a
   `## Deferred (T2)` section where each entry carries its deprecation-cycle
   proposal. This file is the audit's product and the shave's input.

7. **Offer execution:** top T0/T1 items via `/srk:shave <target>` —
   or, in a GSD project, as planned phases so executors run them with fresh
   contexts and the verify step checks the scoreboard.

8. **Report lean (anti context-rot).** The plan is the deliverable and it's on
   disk — do NOT paste the full ranked table into the reply. Report only:
   total candidates, tier mix (T0×N T1×N…), total est. LOC to reclaim, the top
   3 by payoff, and "full plan: SHRINK-PLAN.md". Raw sweep output stays in the
   subagents; only the ranked, verified plan is written to disk.
</process>

End with a terse result line + a **Next** menu of 1-3 `/srk:` commands (see the command file's <next> block). No wall of prose.

<success_criteria>
- [ ] All six sweeps ran (or skipped with stated reason)
- [ ] Every plan entry: catalog #, tier, net-LOC estimate, effort, confidence
- [ ] Zero candidates ranked on map evidence alone
- [ ] SHRINK-PLAN.md written and self-contained (evidence travels with it)
- [ ] T2 items carry deprecation-cycle proposals, not deletion proposals
</success_criteria>
