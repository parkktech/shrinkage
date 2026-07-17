---
name: srk:query
description: "Query the codemap for symbols matching a term instead of grepping the repo"
argument-hint: "<term> [--deep]"
allowed-tools: [Bash, Read]
---

<objective>
Find existing symbols related to a term at map cost, not repo-exploration cost.
</objective>

<process>
1. Locate the shrinkage skill dir — `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else `.claude/skills/shrinkage` or `~/.claude/skills/shrinkage` — call it $SKILL.
2. Run: `python3 $SKILL/scripts/codemap.py query $ARGUMENTS`
   (map missing? run `/srk:map` first).
3. Present the hits grouped by file. If a relevant file shows as collapsed,
   re-run with `--deep`. Open only the files the hits point at.
</process>

<next>
Next:
• /srk:gate "<task>"  — turn candidates into an extend-or-justify plan
</next>
