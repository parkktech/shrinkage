---
name: onboard
description: "One-shot Shrinkage setup: build the map, capture every preference (gate, map policy, PR scoreboard, comedy), print the quickstart"
argument-hint: ""
allowed-tools: [Bash, Read, Write]
---

<objective>
Set up Shrinkage in this repo in one pass — map built, all settings captured
as conscious choices, user ready to work.
</objective>

<process>
1. Locate the shrinkage skill dir ($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else `.claude/skills/shrinkage` or `~/.claude/skills/shrinkage`). Run
   `python $SKILL/scripts/codemap.py build` and show the summary (files,
   symbols, ~tokens, languages, any unsupported languages worth an adapter).
2. Walk the user through every setting, one question with a recommended
   default (interactive sessions — unattended runs take defaults silently):
   - **commit_map** — commit the map (team-shared) or keep it gitignored
     (default; always fresh)?
   - **gate** — soft (justifications suffice, default) or hard (confirm
     before any new file/module)?
   - **pr_scoreboard** — put the scoreboard block in PR descriptions? (great
     for teams; default off)
   - **budget** — map token budget; default 4000, raise for big repos, or
     plan to use `scope` in monorepos.
   - **humor** — the comedy setting. Quips on (default) or straight-faced?
     Ask with a straight face.
3. Write the answers to `.claude/shrinkage.json`; re-run
   `codemap.py refresh` so map location/gitignore reflect the choices.
4. GSD project detected → point out the auto-integration (map + api-map.json
   in `.planning/intel/`, SHRINK-PLAN.md target, SUMMARY.md scoreboard lines).
5. Print the quickstart: `/srk:gate "<task>"` before coding, `/srk:score`
   after, `/srk:audit` when they want the backlog, `/srk:trend` to watch the
   ratchet move.
</process>

<success_criteria>
- [ ] Map built and location policy applied
- [ ] All five settings written as explicit choices
- [ ] Quickstart delivered; GSD integration noted when applicable
</success_criteria>
