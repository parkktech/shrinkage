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
   (see `agents/shrink-auditor.md`).

3. **Verify before ranking.** Ref counts and name matches are signals — each
   candidate gets a source-level look before it enters the plan (the auditor
   brief requires quoting the evidence). No candidate ships on map data alone.

4. **Tier and estimate.** Per candidate: catalog entry, risk tier, estimated
   net LOC, effort (S/M/L), confidence (evidence completeness), and blast
   radius (callers, compat surface?).

5. **Rank** by (payoff × confidence) / effort — with T0s first regardless
   (they're free wins that build trust in the process) and T2s last, each
   carrying its deprecation-cycle proposal.

6. **Write SHRINK-PLAN.md** (repo root, or `.planning/` in a GSD project):
   ranked table + per-candidate evidence notes + a "hidden dependencies
   discovered" section that future audits and shaves append to. This file is
   the audit's product and the shave's input.

7. **Offer execution:** top T0/T1 items via `/srk:shave <target>` —
   or, in a GSD project, as planned phases so executors run them with fresh
   contexts and the verify step checks the scoreboard.
</process>

<success_criteria>
- [ ] All six sweeps ran (or skipped with stated reason)
- [ ] Every plan entry: catalog #, tier, net-LOC estimate, effort, confidence
- [ ] Zero candidates ranked on map evidence alone
- [ ] SHRINK-PLAN.md written and self-contained (evidence travels with it)
- [ ] T2 items carry deprecation-cycle proposals, not deletion proposals
</success_criteria>
