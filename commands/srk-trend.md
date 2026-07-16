---
name: srk-trend
description: "The repo's weight over time: cumulative LOC delta, shrink streak, recent scored changes"
argument-hint: ""
allowed-tools: [Bash]
---

<objective>
Show the direction of the ratchet: cumulative app/test LOC across all scored
changes, the current shrink streak, and the last ten entries.
</objective>

<execution_context>
Locate the shrinkage skill dir ($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else `.claude/skills/shrinkage` or `~/.claude/skills/shrinkage`), then run:
`python $SKILL/scripts/diffstat.py --trend`
Empty log → explain that scoring with `--log` (or `/srk-score --log`) feeds
the trend, and offer to enable it habitually. Report the summary line and, if
the cumulative app LOC is negative, celebrate — that's the ratchet working.
</execution_context>
