# Workflow: Score

<objective>
Measure every change on the metric that matters: goal achieved with how much
code. The scoreboard makes minimalism visible, comparable, and habitual — for
the model on every task, and optionally for humans on every PR.
</objective>

<process>
1. **Run:** `python3 $SKILL/scripts/diffstat.py [REF] [--pr]` (default REF:
   HEAD → scores the working diff; pass `main` to score a whole branch).
   **This step is script-only:** run it and echo its output verbatim — no
   re-analysis pass, no subagent, no re-reading the codebase. The script now
   prints everything that needs judgment flags: `compat-watch` lines
   (signature changes on existing symbols — Zeroth Law check) and
   `unjustified new symbols` (gate-ledger cross-check). Only those two lines
   warrant follow-up reasoning; a clean scoreboard needs none.

2. **Read the line:** net app LOC, net test LOC (counted separately — test
   deletions never flatter the score), files touched, new symbols (named),
   removed symbols (named).

3. **Interrogate the numbers:**
   - New symbols the gate didn't justify → flag; either justify now or fold
     them into existing homes before finishing.
   - Net app LOC positive and large → re-check the plan against the catalog:
     is a C1/C9 hiding in the diff?
   - Removed symbols present → confirm each had its evidence chain (riding a
     feature diff doesn't exempt a deletion from the safety model).

4. **Report** the scoreboard line verbatim (with the script's quip when humor
   is on — one joke, information first). Net-negative → celebrate. Large
   growth → tease gently, never scold; growth that survived the gate is
   legitimate.

5. **Publish where it counts:**
   - `--pr` (or `pr_scoreboard: true`) → paste the markdown block into the PR
     description so human reviewers see the metric.
   - GSD project → the line goes in the plan's SUMMARY.md; verifiers check it
     against the plan's expectation.
   - The trend log (`.claude/shrinkage-log.jsonl`, `--log`) accumulates one
     entry per scored change — the repo's weight over time, for retros and
     for proving the ratchet only moves down.
</process>

End with a terse result line + a **Next** menu of 1-3 `/srk-` commands (see the command file's <next> block). No wall of prose.

<success_criteria>
- [ ] Scoreboard line reported verbatim
- [ ] Every new symbol traceable to a gate justification
- [ ] App vs test LOC read separately, no test-deletion flattery
- [ ] Configured outputs (PR block / SUMMARY.md / trend log) delivered
</success_criteria>
