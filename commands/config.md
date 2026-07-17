---
name: config
description: "View or change any Shrinkage setting: gate hardness, map commit policy, PR scoreboard, token budget, comedy"
argument-hint: "[key value]"
allowed-tools: [Bash, Read, Write]
---

<objective>
Manage `.claude/shrinkage.json` for this repo — every setting, including the
important ones and the comedy one.
</objective>

<process>
1. No arguments: show current effective settings (file merged over defaults)
   with one line of meaning each:
   - `gate` — `soft` (default): new files/modules need a stated
     justification. `hard`: also confirm with the user first.
   - `commit_map` — `false` (default): codemap auto-gitignored, rebuilt
     fresh. `true`: committed and shared with the team.
   - `pr_scoreboard` — `true`: `/srk:score` always emits the PR description
     block. Default `false` (use `--pr` ad hoc).
   - `budget` — map token budget (default 4000). Raise for big repos; prefer
     `codemap.py scope <dir>` in monorepos.
   - `humor` — `true` (default): the scripts crack one joke per run and the
     agent matches the tone. `false`: everyone plays it straight.
   - `auto_max_items` — items `/srk:shave --auto` does before it checkpoints
     and stops (default 8).
   - `auto_context_stop` — `--auto` stops when the context window passes this
     percent (default 75), so long runs stay resumable.
   - `quiet_startup` — `true`: suppress the session-start [shrinkage] line.
2. With `key value`: validate (gate ∈ soft|hard; commit_map, pr_scoreboard,
   humor/quiet_startup ∈ true|false; budget/auto_max_items/auto_context_stop = positive int), update the file, confirm the
   change in one line.
3. Side effects: `commit_map` → true: remove the map path from `.gitignore`;
   → false: re-run `/srk:map` so the ignore entry is restored. `humor` →
   false: deliver the confirmation with a perfectly straight face.
</process>

<next>
Next:
• /srk:map            — rebuild with the new settings if you changed budget/commit_map
</next>
