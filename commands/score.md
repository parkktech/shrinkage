---
name: score
description: "The minimalism scoreboard: net app/test LOC, new/removed symbols; PR block and trend log"
argument-hint: "[REF] [--pr] [--log]"
allowed-tools: [Bash]
---

<objective>
Grade the current diff on the metric that matters: goal achieved with how much
code. App and test LOC count separately; negative app LOC is the high score.
</objective>

<execution_context>
Run this inline — do NOT spawn a subagent for scoring; it is one script call.
Locate the shrinkage skill dir ($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else `.claude/skills/shrinkage` or `~/.claude/skills/shrinkage`), then follow
`$SKILL/workflows/score.md`: run `python3 $SKILL/scripts/diffstat.py
$ARGUMENTS`, report the line verbatim (quip included), interrogate unjustified
new symbols and any test-LOC drop, and publish to the configured outputs (PR
block / GSD SUMMARY.md / trend log).
</execution_context>

<success_criteria>
- [ ] Scoreboard line reported verbatim
- [ ] Every new symbol traceable to a gate justification
- [ ] Test-LOC reductions flagged and justified, never silent
</success_criteria>

<next>
Next:
• /srk:score --pr     — emit the PR-description block
• /srk:trend          — see cumulative weight + shrink streak
• /srk:shave          — if the diff left removable code behind
</next>
