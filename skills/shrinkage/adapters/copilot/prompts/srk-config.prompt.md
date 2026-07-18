---
name: srk-config
description: View or change Shrinkage settings (gate, map policy, PR scoreboard, budget, comedy)
argument-hint: "[key value]"
agent: agent
---

Manage `.claude/shrinkage.json`: no args -> show effective settings (defaults:
gate=soft, commit_map=false, pr_scoreboard=false, budget=4000, humor=true)
with one line of meaning each; with `key value` -> validate, write, confirm.
Side effects per `.claude/skills/shrinkage/commands/srk-config.md` (gitignore sync on
commit_map changes).
