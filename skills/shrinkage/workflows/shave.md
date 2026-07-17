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

1. **Scope.** Target = the argument given, or the files in
   `git diff --name-only HEAD` when riding along with a feature change.
   Keep a shave scoped — a repo-wide hunt is the audit workflow's job.

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

8. **Report:** transforms executed (catalog # + tier + net LOC each), T2
   candidates escalated with evidence, reverted attempts and what they
   revealed, suite status.
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
