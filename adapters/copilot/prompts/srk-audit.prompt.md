---
name: srk-audit
description: Repo-wide shrink audit — six evidence sweeps, ranked SHRINK-PLAN.md backlog
argument-hint: "[dir]"
agent: agent
---

Follow `.github/shrinkage/workflows/audit.md` for ${input} (default: whole
repo): fresh map, all six sweeps (dead-symbol, duplication via dupes+clones,
structure, flags, platform, noise), verify every candidate in source, tier +
estimate + rank, write SHRINK-PLAN.md, offer execution via /srk-shave. The
audit finds and ranks; it does not cut.
