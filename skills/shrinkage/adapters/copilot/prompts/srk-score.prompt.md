---
name: srk-score
description: Minimalism scoreboard — net app/test LOC, new/removed symbols
argument-hint: "[ref] [--pr] [--log]"
agent: agent
---

Run `python3 .github/shrinkage/scripts/diffstat.py ${input}` and report the
line verbatim. Flag any new symbol without a gate justification and any
test-LOC drop. With --pr, paste the markdown block into the PR description.
Full process: `.github/shrinkage/workflows/score.md`.
