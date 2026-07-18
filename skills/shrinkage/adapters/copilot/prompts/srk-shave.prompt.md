---
name: srk-shave
description: Safe subtraction pass — remove/consolidate code with evidence chains, zero behavior change
argument-hint: "[plan item # | dir or files]"
agent: agent
---

REQUIRED READING FIRST: `.claude/skills/shrinkage/references/safety-model.md` and
`.claude/skills/shrinkage/references/consolidation-catalog.md`. TODO GATE: if
SHRINK-PLAN.md has unchecked `- [ ]` items under `## TODO before shaving`, stop
and report them — no shave until the list is clear or the user says "shave
anyway". Then follow
`.claude/skills/shrinkage/workflows/shave.md` on ${input} (a SHRINK-PLAN item
number, a path, or the current diff's files): green baseline (no coverage
report → suite-gated mode, safety-model §4), hunt (map x0 refs, `codemap.py
dupes`, `codemap.py clones`, dead branches, wrappers), tier every candidate, run
`coverage_check.py` on targets, execute T0/T1 one transform per commit with the
evidence template. COMMIT DISCIPLINE: only via
`python3 .claude/skills/shrinkage/scripts/safe_commit.py -m "<msg>" -- <files>`
— never `git add -A`/`git commit -a`; Copilot has no staging-guard hook, the
script is the guard. Dirty target → SKIP by default; the only sanctioned
exception is `dirty_apply.py park → precheck (BEFORE the commit) → safe_commit →
unpark`. Mark each done row with `plan.py done <id> HEAD` (derives sha + actual
LOC itself), escalate T2 with a deprecation plan, finish with the scoreboard.
