---
name: srk-shave
description: Safe subtraction pass — remove/consolidate code with evidence chains, zero behavior change
argument-hint: "[dir or files]"
agent: agent
---

REQUIRED READING FIRST: `.github/shrinkage/references/safety-model.md` and
`.github/shrinkage/references/consolidation-catalog.md`. Then follow
`.github/shrinkage/workflows/shave.md` on ${input} (or the current diff's
files): green baseline, hunt (map x0 refs, `codemap.py dupes`, `codemap.py
clones`, dead branches, wrappers), tier every candidate, run
`coverage_check.py` on targets, execute T0/T1 one-transform-per-commit with
the evidence template, escalate T2 with a deprecation plan, finish with the
scoreboard.
