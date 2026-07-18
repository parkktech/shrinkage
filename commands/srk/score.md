---
name: srk:score
description: "The minimalism scoreboard: lines removed/added/net, symbols, and how many plan items were removed/merged/cleaned"
argument-hint: "[REF | BASE..HEAD] [--pr] [--log] [--shave-only]"
allowed-tools: [Bash]
---

<objective>
Grade the change on the metric that matters: goal achieved with how much code.
The script prints a short, colored scoreboard — removed vs added lines, net app
(and test, separately), symbols, and the removed/merged/cleaned plan tally.
</objective>

<execution_context>
One script call, inline — no subagent, no re-analysis. Locate $SKILL
(`${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else
`.claude/skills/shrinkage` or `~/.claude/skills/shrinkage`), then:

1. **Pick the ref so the number is honest.**
   - You just COMMITTED a shave/feature and the working tree still holds
     unrelated dirty files? Score the committed range:
     `python3 $SKILL/scripts/diffstat.py <base>..HEAD --color`
     (the shave batch's parent: `<firstShaveCommit>^..HEAD`). This is the fix
     for "the score shows +1700 of stuff I didn't touch."
   - The committed range itself got ENTANGLED — it contains non-shave commits
     (a feature landed mid-batch, or an incident swept unrelated work in)? Add
     `--shave-only` to score just the `shrink:`/`fix:` commits and still see the
     whole-range delta, so the mixing is visible instead of drowning the board:
     `python3 $SKILL/scripts/diffstat.py <base>..HEAD --shave-only --color`
     (custom subjects: `--prefix shrink:,fix:,refactor:`).
   - Otherwise score the working tree:
     `python3 $SKILL/scripts/diffstat.py --color`.

2. **Show the output verbatim — it IS the scoreboard.** Do NOT reprint it,
   reformat it into prose, or list the symbol names. The colored block already
   reads cleanly and folds in its own ⚠ flags (compat-watch signature changes,
   unjustified new symbols).

3. **Add at most ONE line, only if a ⚠ fired** — point at the compat-watch
   change to eyeball or the unjustified new symbol. A clean board needs no
   commentary.

4. **Publish only if asked:** `--pr` appends the PR markdown block; `--log`
   records the change in the trend (`/srk:trend`) — but don't `--log` a working
   tree full of unrelated work; log the committed range or after committing.
</execution_context>

<success_criteria>
- [ ] Scored the right ref (committed range when the tree is dirty with unrelated work)
- [ ] Colored scoreboard shown once, verbatim — no prose re-render, no symbol-name wall
- [ ] Only ⚠-flagged lines get a follow-up sentence
</success_criteria>

<next>
Next:
• /srk:trend          — cumulative weight + shrink streak
• /srk:score --pr     — emit the PR-description block
• /srk:audit          — find the next reductions
</next>
