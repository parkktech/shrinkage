---
name: srk-map
description: Build/refresh the Shrinkage codemap; report detected languages and rules to load
agent: agent
---

Run `python3 .claude/skills/shrinkage/scripts/codemap.py refresh`, report the summary
(files, symbols, ~tokens, languages), then read the `rules/<lang>.md` files it
names under `.claude/skills/shrinkage/rules/`. Full process:
`.claude/skills/shrinkage/workflows/map.md`.
