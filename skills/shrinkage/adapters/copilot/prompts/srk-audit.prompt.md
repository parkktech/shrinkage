---
name: srk-audit
description: Repo-wide shrink audit — six evidence sweeps, ranked SHRINK-PLAN.md backlog
argument-hint: "[dir]"
agent: agent
---

Follow `.claude/skills/shrinkage/workflows/audit.md` for ${input} (default: whole
repo): fresh map, all six sweeps (dead-symbol, duplication via dupes+clones,
structure, flags, platform, noise). Read the ledger first
(`.shrinkage/ledger.md`): never flag `## keeps`, never propose `## frozen`
paths; carry a prior plan's open rows in as explicit re-verify items (`plan.py
open`, `plan.py carry`). Verify every candidate in source, run `git status
--porcelain` per target (dirty → mark DIRTY), tier + estimate (price C1/C9's new
home; rank dedups by definitions collapsed, not LOC) + rank, include the
`## Bugs found` section for real defects (fix-first, separate commits), write
SHRINK-PLAN.md and stamp it with `plan.py restamp`, offer execution via
/srk-shave. No coverage artifact → declare suite-gated mode once in the plan
header. The audit finds and ranks; it does not cut.
