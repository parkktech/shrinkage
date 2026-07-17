---
name: shave
description: "Safe subtraction pass: remove/consolidate code with evidence chains, atomic commits, and zero behavior change"
argument-hint: "[plan item # | --auto [--dangerous] | dir | file] [--dry-run]"
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

<execution_context_extra>
Targets: a plan item number (default one-at-a-time), `--auto`/`all` (work the
whole backlog until a stop condition), a dir/file path, or nothing (current
diff). After a single item, ALWAYS prompt for the next one (name it + its
tier + est LOC); `--auto` runs without prompting and halts on the first T2/T3 item,
first red gate, or empty backlog. `--auto --dangerous` (alias --full-send)
proceeds THROUGH T2/public-surface too (direct removal, no deprecation cycle) —
still atomic + tests-green-or-revert per item, still hard-stops on a red/absent
suite; refused if allow_dangerous:false. When --auto halts safely, report what
got done + why it stopped + the two continue options (never a bare '0 done').
</execution_context_extra>

<success_criteria>
- [ ] Suite green before, after every transform, and at the end
- [ ] One atomic commit per transform with the evidence template
- [ ] T2 candidates escalated with evidence, never executed silently
- [ ] Compatibility surface intact; net app LOC negative or justified
- [ ] Single item → prompted for the next; `--auto` → ran to a stop condition
</success_criteria>

<next>
Next:
• /srk:shave <next #>  — the item just named (one more reviewable step)
• /srk:shave --auto    — run the rest of the backlog until it needs you
• /srk:shave --auto --dangerous — full send: execute T2/public items too (risky)
• /srk:score           — confirm the shave came out net-negative
</next>
