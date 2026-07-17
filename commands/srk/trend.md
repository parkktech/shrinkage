---
name: srk:trend
description: "Lifetime shrinkage total across EVERY shave commit — removed/merged/cleaned — plus recent scored changes"
argument-hint: ""
allowed-tools: [Bash]
---

<objective>
Show the real cumulative reduction: net app/test LOC summed across every shave
commit in the repo's history — not just what was manually logged — with the
removed/merged/cleaned breakdown, then the recent scored changes.
</objective>

<execution_context>
Locate the shrinkage skill dir ($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage`
when installed as a plugin, else `.claude/skills/shrinkage` or
`~/.claude/skills/shrinkage`), then run:
`python3 $SKILL/scripts/diffstat.py --trend --color`

It computes the LIFETIME total from git history — every commit carrying a shave
marker (`shrink:` subject / `catalog:` line, safety-model §6) — so the number
reflects all your cleanup, not the last couple of changes. Below it, the recent
trend-log entries (from `/srk:score --log`) list the last ten scored changes.
Report it verbatim; a negative lifetime app LOC is the ratchet — celebrate.

Only shave commits that followed the §6 commit template are counted. If the
total reads low for a big cleanup, those commits probably lack the marker — say
so and offer `/srk:score <base>..HEAD` to score an explicit committed range
instead. (`diffstat.py --total` prints just the lifetime block.)
</execution_context>

<next>
Next:
• /srk:score <base>..HEAD  — score a specific committed range
• /srk:audit               — find the next reductions to extend the streak
</next>
