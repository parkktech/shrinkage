---
name: srk:gate
description: "Run the reuse gate for a task: candidate symbols, extend-or-justify, minimal-diff proposal"
argument-hint: "<task description>"
allowed-tools: [Bash, Read, Grep]
---

<objective>
Before any code is written for the task in $ARGUMENTS, decide what will be
EXTENDED rather than added — growth stopped at the door costs nothing to
remove later.
</objective>

<execution_context>
Run this inline in the main context — do NOT spawn a subagent for the gate; the map and rules are already loaded here.
Locate the shrinkage skill dir ($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else `.claude/skills/shrinkage` or `~/.claude/skills/shrinkage`), then follow
`$SKILL/workflows/gate.md` exactly: size the gate first (lite path for small
low-risk changes or near-empty maps) → map current → harvest candidates from
the map → extend-or-justify each → ladder walk → catalog-in-reverse check →
compatibility pass → emit AND persist the gate record
(`python3 $SKILL/scripts/gatelog.py add ...` — the scoreboard cross-checks
it). Honor `gate: "hard"` in `.claude/shrinkage.json` (user confirmation
before rungs 7–8). Don't re-read rules files already loaded this session; do
not load safety-model.md here. Ambiguous calls:
`$SKILL/references/extend-vs-add.md`.
</execution_context>

<success_criteria>
- [ ] Gate sized (lite vs full) and the choice stated
- [ ] Full path: 2–5 candidates with extend / not-applicable-because verdicts
- [ ] Every change names its ladder rung; 7–8 carry justifications
- [ ] No planned change recreates a catalog smell (C1/C2/C3/C9)
- [ ] Compatibility surface changes are additive-only
- [ ] Gate record persisted via gatelog.py
</success_criteria>

<next>
Next:
• implement the chosen rung, then /srk-score
• /srk-query <term>   — if you need more candidates first
</next>
