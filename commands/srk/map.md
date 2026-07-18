---
name: srk:map
description: "Build or refresh the token-lean codemap; prints detected languages and which rules to load"
argument-hint: "[--budget N] [--sync-intel]"
allowed-tools: [Bash, Read]
---

<objective>
Build/refresh the repo's symbol map so all later work orients from ~4k tokens
of map instead of repo-wide exploration.
</objective>

<execution_context>
$SKILL is resolved FRESH for THIS invocation — never reuse a path remembered from earlier in the session (a mid-session plugin update strands version-pinned cache paths). Churn-proof order: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` if set; else the newest installed copy `$(ls -dv ~/.claude/plugins/cache/*/shrinkage/*/skills/shrinkage 2>/dev/null | tail -1)`; else the vendored locations.

Locate the shrinkage skill dir ($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else `.claude/skills/shrinkage` or `~/.claude/skills/shrinkage`), then follow
`$SKILL/workflows/map.md`: run `python3 $SKILL/scripts/codemap.py refresh
$ARGUMENTS`, handle the first-build commit-vs-gitignore question, read the
language report, and load the named `rules/<lang>.md` files. GSD projects
sync to `.planning/intel/` automatically — confirm the sync line.
</execution_context>

<success_criteria>
- [ ] Map current at the correct location; languages + rules reported
- [ ] Rules for the task's languages loaded
- [ ] GSD project → api-map.json sync confirmed
</success_criteria>

<next>
Next:
• /srk:gate "<task>"  — before writing code for a feature/fix
• /srk:audit          — read-only scan → ranked SHRINK-PLAN.md of safe cleanups
• /srk:onboard        — if settings aren't set yet
</next>
