# Workflow: Shave

<objective>
Execute a subtraction pass — remove or consolidate code the repo no longer
needs — with zero behavior change, following the safety model to the letter.
Deleting is part of the feature; this workflow is how deletion earns trust.
</objective>

<required_reading>
`references/safety-model.md` (the whole thing — especially §0 Zeroth Law,
§3 evidence chain, §6 transformation protocol) and
`references/consolidation-catalog.md` for the transforms in play.
</required_reading>

<process>
0. **Dry-run mode (v0.8).** If invoked with `--dry-run`: execute steps 1–4
   fully (scope, baseline check, hunt, tier + evidence), then produce the
   complete transform plan — per candidate: catalog entry, tier, evidence
   chain, the exact edit intended, expected net LOC — and STOP. No file is
   modified, no commit made. This is the review artifact before letting the
   surgeon loose.

1. **Scope.** The target argument is one of:
   - **a SHRINK-PLAN.md item number** (`1`, `3`, or `#3`) — execute exactly
     that plan entry: its file(s) are the scope, its catalog entry and
     evidence come pre-loaded from the plan (re-verify per §3 anyway);
   - **`--auto`** (alias: `all`) — **keep going until done**: work the whole
     backlog top-to-bottom, unattended, one gated commit per item (batch loop
     below). The answer to "why doesn't it do the whole project?";
   - **a directory or file path** — hunt within it;
   - **nothing** — the files in `git diff --name-only HEAD` (riding along
     with a feature change).
   A number/`--auto` with no SHRINK-PLAN.md present → say so and suggest
   `/srk:audit` first. Keep a single-item shave scoped — a repo-wide *hunt* is
   the audit workflow's job.

   ### Interactive vs --auto
   - **Single item / bare** (no `--auto`): do the ONE item, then **prompt for
     the next** — end with "next up: #N `<candidate>` (Tstier, ~N LOC) —
     `/srk:shave N`, or `/srk:shave --auto` to run the rest." One reviewable
     step at a time; you stay in the loop.
   - **`--auto`**: don't prompt between items — keep going until a stop
     condition. This is the "set it running on the backlog" mode.

   ### Batch loop (`--auto`)
   Process every OPEN plan item in ranked order, each as its own gated commit —
   throughput without giving up the per-commit safety guarantee:

   ```
   for each open item, highest rank first:
     if item.tier is T2/T3:  STOP — needs your judgment (report and halt)
     run the single-item shave (steps 2–7): re-verify evidence, gate,
       apply ONE transform, tests green, commit, update the plan row to Done
     if the gate went RED:   revert that item, record the hidden dependency,
                             STOP (a break means the plan's assumptions are off —
                             don't keep going blind)
   ```

   `--auto` halts on the **first T2/T3 item, the first red gate, or an empty
   backlog** — never a whole-repo rampage of unreviewed commits. On a
   production codebase, review the batch before pushing; each commit is
   independently `git revert`-able. Report cumulative net LOC and a per-item
   line (done / reverted / halted-at), then name what stopped it.

2. **Baseline.** Relevant test suite green. Red baseline → stop and report;
   you cannot detect breakage against a red baseline.

3. **Hunt, using signals in this order (cheap → expensive):**
   - `codemap.py refresh` then scan the target's symbols for `x0` refs (C6
     candidates) and one-method classes (C7)
   - `codemap.py dupes` scoped output for same-name / similar-signature
     groups (C1, C9)
   - read the target files once, flagging: dead branches & expired flags
     (C4), pass-through wrappers (C2), single-implementer abstractions (C3),
     switch ladders (C8), comment noise (C10), hand-rolled platform features
     (C5)

4. **Tier every candidate** (safety-model §2). T0 → proceed. T1 → build the
   full evidence chain (§3) including the language's dynamic-reference
   checklist from `rules/<lang>.md`, AND run
   `coverage_check.py <target files>` — unreported/low-coverage targets
   auto-escalate to T2 unless you write characterization tests first
   (safety-model §4). T2 → do NOT execute; record in the report with
   evidence and the recommended deprecation-cycle plan. T3 → not a shave;
   route to the normal gate/plan flow.

5. **Execute, one transform per commit,** per the transformation protocol
   (§6): apply one catalog entry → gates green → commit with the evidence
   template → next. Any red → revert that transform fully, record the hidden
   dependency you just discovered in the report. **Economy:** spawn the
   `srk-surgeon` agent to apply each transform — it runs on the cheap model
   (the what/how is already decided here), with the test gate guaranteeing
   safety. Reserve the capable model for the analysis (this workflow) and the
   `srk-verifier` pass.

6. **Compatibility check per transform:** old entry points on the surface
   keep working (deprecation shims where needed, marked and scheduled). Every
   shim created gets a line in **DEPRECATIONS.md** at the repo root:
   `- [ ] <old entry point> -> <replacement> (remove <date/release>)`. The
   trend report nags about unchecked entries, so shims can't accumulate
   silently forever — check the box when the shim is finally removed.

7. **Score.** `python3 $SKILL/scripts/diffstat.py` — the shave should read
   net-negative in app LOC with test LOC steady or up (characterization tests
   added count as investment, not weight). Report the scoreboard line and, in
   a GSD project, put it in the plan SUMMARY.md.

8. **Update SHRINK-PLAN.md** so it stays current: mark each executed item done
   (strike the row with `~~...~~` or move it to a `## Done` section — the
   startup line counts unstruck `| N |` rows as open), append reverted
   attempts to `## Hidden dependencies discovered`, and re-stamp `map-fp` to
   the post-shave fingerprint so the plan doesn't read as stale from your own
   changes.

9. **Report:** transforms executed (catalog # + tier + net LOC each), T2
   candidates escalated with evidence, reverted attempts and what they
   revealed, suite status, and remaining open plan items.
</process>

End with a terse result line + a **Next** menu of 1-3 `/srk:` commands (see the command file's <next> block). No wall of prose.

<success_criteria>
- [ ] Suite green before, after every transform, and at the end
- [ ] One atomic commit per transform, evidence template in each message
- [ ] No T2 executed without human confirmation; escalations documented
- [ ] Compatibility surface intact (shims in place where required)
- [ ] Net app LOC negative (or every exception justified in the report)
- [ ] Test LOC not reduced to flatter the score
</success_criteria>
