---
name: srk:audit
description: "Repo-wide shrink audit: six evidence sweeps, tiered candidates, ranked SHRINK-PLAN.md backlog"
argument-hint: "[dir]"
allowed-tools: [Bash, Read, Grep, Write, Agent]
---

<objective>
Produce the ranked, evidence-backed backlog of shrink opportunities for the
repo (or $ARGUMENTS subtree) as SHRINK-PLAN.md. The audit finds and ranks; it
does not cut.
</objective>

<execution_context>
Locate the shrinkage skill dir ($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else `.claude/skills/shrinkage` or `~/.claude/skills/shrinkage`), then follow
`$SKILL/workflows/audit.md` exactly. Subagents for the parallel sweeps use the
brief in `$SKILL/agents/shrink-auditor.md`. Required reading:
`$SKILL/references/safety-model.md` §§0–3 and
`$SKILL/references/consolidation-catalog.md`.
</execution_context>

<success_criteria>
- [ ] All six sweeps ran (dead-symbol, duplication, structure, flag, platform, noise)
- [ ] Every entry: catalog #, tier, net-LOC estimate, effort, confidence
- [ ] Zero candidates ranked on map evidence alone
- [ ] SHRINK-PLAN.md written; execution offered via /srk:shave or GSD phases
</success_criteria>

<next>
Lead with the concrete action:
• top items clean → /srk:shave 1 (execute the plan's #1 safely)
• top items blocked on your dirty tree → say it plainly: "Commit or stash your
  in-flight work, then /srk:shave 1" — don't just list the command
• /srk:trend — track the ratchet over time
</next>
