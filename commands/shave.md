---
name: shave
description: "Safe subtraction pass: remove/consolidate code with evidence chains, atomic commits, and zero behavior change"
argument-hint: "[dir or file...]"
allowed-tools: [Bash, Read, Grep, Edit, Write, Agent]
---

<objective>
Execute a subtraction pass on $ARGUMENTS (or the files touched by the current
change) with zero behavior change. Deleting is part of the feature — and it
follows the safety model to the letter.
</objective>

<execution_context>
Locate the shrinkage skill dir ($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else `.claude/skills/shrinkage`,
`~/.claude/skills/shrinkage`, or `.agents/skills/shrinkage`), then follow
`$SKILL/workflows/shave.md` exactly. Required reading first:
`$SKILL/references/safety-model.md` and
`$SKILL/references/consolidation-catalog.md`.
</execution_context>

<success_criteria>
- [ ] Suite green before, after every transform, and at the end
- [ ] One atomic commit per transform with the evidence template
- [ ] T2 candidates escalated with evidence, never executed silently
- [ ] Compatibility surface intact; net app LOC negative or justified
</success_criteria>
