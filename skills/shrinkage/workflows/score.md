# Workflow: Score

<objective>
Make minimalism visible in one glance: how much code the change removed vs
added, net (app and test separately), and — from SHRINK-PLAN — how many items
were removals, merges, or cleanups. Short, colored, honest.
</objective>

<process>
1. **Score the right ref.**
   - Working tree (default): `python3 $SKILL/scripts/diffstat.py --color`.
   - A COMMITTED shave/feature while the tree still holds unrelated dirty files:
     score the range — `diffstat.py <base>..HEAD --color` — so unrelated work
     can't inflate the number. This is the fix for a board that reads +1700 when
     your shave only removed 400.

2. **Show it verbatim.** The script IS the scoreboard — one colored block:
   `removed / added / net`, `files · symbols`, and `plan  N removed · N merged ·
   N cleaned`. Echo it as-is. Do NOT reformat into prose, do NOT reprint, do NOT
   list symbol names — the block is already clean and folds in its own ⚠ flags
   (compat-watch signature changes, unjustified new symbols).

3. **Comment only on a ⚠.** A clean board needs zero commentary. If a
   compat-watch or unjustified line fired, add ONE sentence pointing at it.

4. **Publish only if asked.** `--pr` appends a PR markdown block; `--log`
   records the change for `/srk:trend`. Don't `--log` a working tree full of
   unrelated work — log the committed range, or after committing.
</process>

End with the colored scoreboard + a **Next** menu of 1-3 `/srk:` commands. No
wall of prose — the old scoreboard's failure was burying −401 of real work under
paragraphs and a list of 35 symbol names.

<success_criteria>
- [ ] Scored the right ref (committed range when the tree is dirty with unrelated work)
- [ ] Colored scoreboard shown once, verbatim — no prose re-render, no symbol-name wall
- [ ] App vs test LOC read separately; test-LOC drops flagged
- [ ] Only ⚠-flagged lines get follow-up
</success_criteria>
