---
name: srk:help
description: "Show every Shrinkage command in the order you'd use them, with a one-line usage guide"
argument-hint: "[command | --full]"
allowed-tools: [Read]
---

<objective>
Give the user a short, clean map of every /srk-* command — top to bottom, in
the order they'd actually reach for them (set up, understand, reduce, measure,
maintain). Default view is terse; detail is opt-in.
</objective>

<execution_context>
No heavy logic. Read the argument and respond:

- **bare** (no args): print <reference> verbatim, inside a fenced code block so
  the columns stay aligned. Nothing else — no preamble, no per-command essay.
- **<command>** (e.g. `shave`, `/srk-shave`): print that one command's line
  plus its "when to use" note from <details>. Unknown name → fall back to the
  full list.
- **--full**: print <reference>, then the "when to use" notes from <details>.

Humor setting: if `.claude/shrinkage.json` has `humor:false`, drop the tagline
and the closing line; otherwise keep them (one line each — this is a help
screen, not open-mic night).
</execution_context>

<reference>
Shrinkage — write less, delete safely, keep it working.

Setup
  /srk-onboard    one-time setup: build the map, set your preferences

Understand
  /srk-map        build or refresh the token-lean codemap
  /srk-query      find symbols in the map instead of grepping the tree

Before adding code
  /srk-gate       reuse gate: extend what exists before writing new code

Take weight off
  /srk-audit      scan the repo -> ranked SHRINK-PLAN.md of safe cuts
  /srk-shave      execute a cut: evidence chain + atomic commit per change

Watch the scale
  /srk-score      this change's net-LOC scoreboard (+ optional PR badge)
  /srk-trend      the repo's weight over time; your shrink streak

Housekeeping
  /srk-config     view or change any setting
  /srk-update     update the plugin to the latest version
  /srk-help       this screen — add a command for detail, --full for more

Typical flow:  onboard once -> gate before you add -> shave to remove -> score to prove it.
Here, shrinkage is the whole point.
</reference>

<details>
Per-command "when to use" (for --full or a single-command lookup):

- onboard — run once per repo; builds the map and captures your gate / humor / scoreboard preferences.
- map — refresh after big changes; the ~4k-token map is what every other command reads instead of walking the tree.
- query — "where is X?" without burning context on grep.
- gate — starting a feature or fix; surfaces symbols to extend so you add less code in the first place.
- audit — read-only sweep that fills SHRINK-PLAN.md with ranked, safe removals (six evidence sweeps, tiered by risk).
- shave — the actual subtraction: one plan item, a folder, or `--auto` the whole backlog; atomic commit per cut, tests-green-or-revert.
- score — after a change, see net app/test LOC and drop a PR scoreboard badge.
- trend — the long view: cumulative LOC delta and your shrink streak over time.
- config — flip any setting (gate hardness, map commit policy, humor, budget…).
- update — check installed vs latest and clear Claude Code's pinned plugin cache so the next install is clean.
</details>

<next>
Next:
• /srk-onboard        — if this repo isn't set up yet
• /srk-gate "<task>"  — before you write the next feature
</next>
