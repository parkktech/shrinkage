---
name: srk-query
description: Find existing symbols in the codemap instead of grepping the repo
argument-hint: <term>
agent: agent
---

Run `python3 .claude/skills/shrinkage/scripts/codemap.py query ${input}` (add --deep
to expand collapsed files). Present hits grouped by file; open only the files
the hits point at.
