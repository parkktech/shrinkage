---
name: audit
description: "Repo-wide shrink audit: seven evidence sweeps, tiered candidates, ranked SHRINK-PLAN.md backlog"
argument-hint: "[dir] [--force]"
allowed-tools: [Bash, Read, Grep, Write, Agent]
---

<objective>
Produce the ranked, evidence-backed backlog of shrink opportunities for the
repo (or $ARGUMENTS subtree) as SHRINK-PLAN.md. The audit finds and ranks; it
does not cut.
</objective>

<execution_context>
$SKILL is resolved FRESH for THIS invocation — never reuse a path remembered from earlier in the session (a mid-session plugin update strands version-pinned cache paths). Churn-proof order: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` if set; else the newest installed copy `$(ls -dv ~/.claude/plugins/cache/*/*/*/skills/shrinkage 2>/dev/null | tail -1)`; else the vendored locations.

Locate the shrinkage skill dir ($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else `.claude/skills/shrinkage` or `~/.claude/skills/shrinkage`), then follow
`$SKILL/workflows/audit.md` exactly — starting with its step-0 freshness gate:
when a current plan already exists and nothing changed, ASK (work the plan /
re-verify only / force a full re-sweep) instead of silently re-sweeping or
silently re-stamping; `--force` in $ARGUMENTS always runs the full seven sweeps.
Every path ends with the step-8 two-section close (Results / TODO). Subagents for the parallel sweeps use the
brief in `$SKILL/agents/shrink-auditor.md`. Required reading:
`$SKILL/references/safety-model.md` §§0–3 and
`$SKILL/references/consolidation-catalog.md`.
</execution_context>

<success_criteria>
- [ ] All seven sweeps ran (suite-health, dead-symbol, duplication, structure, flag, platform, noise)
- [ ] Every entry: catalog #, tier, net-LOC estimate, effort, confidence
- [ ] Zero candidates ranked on map evidence alone
- [ ] SHRINK-PLAN.md written; execution offered via /srk:shave or GSD phases
</success_criteria>

<next>
The report itself ends with the TODO-before-advancing section (see the
workflow's two-section report format) — the Next block follows from it:
• TODO list has open items → lead with item 1's action verbatim; do NOT suggest
  /srk:shave while the list is open
• TODO list empty, top items clean → /srk:shave 1 (execute the plan's #1 safely)
• top items blocked on your dirty tree → say it plainly: "Commit or stash your
  in-flight work, then /srk:shave 1" — don't just list the command
• /srk:trend — track the ratchet over time
</next>
