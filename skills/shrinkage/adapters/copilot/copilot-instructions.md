<!-- Shrinkage doctrine for GitHub Copilot — append to .github/copilot-instructions.md -->

## Code minimalism (Shrinkage)

The measure of a change is the goal achieved with the least code. Before
writing code, orient from the codemap, not by exploring the repo:

- Refresh/read the map: `python .github/shrinkage/scripts/codemap.py refresh`
  (map at `.claude/codemap.txt` or `.planning/intel/codemap.txt`); query it
  with `codemap.py query <term>`.
- Read `.github/shrinkage/rules/<language>.md` for each language you touch.

**Extension ladder** — stop at the first rung that achieves the goal; rungs
7–8 require a stated one-line justification: (1) change a value/config →
(2) add a parameter with a safe default → (3) extend a method body →
(4) add a method to an existing class → (5) add a function to an existing
module → (6) new class in an existing file → (7) new file → (8) new module.

**Reuse gate** — before implementing, list 2–5 existing symbols from the map
that could be extended; for each, state "extend" or "not applicable because
<fact>". Only then write code.

**Zeroth Law — backwards compatibility outranks everything.** Public symbols,
endpoints, CLI flags, config keys, wire formats, and schemas change
additively only; removals/renames go through deprecation shims, never
directly.

**Deletions** require the evidence chain in
`.github/shrinkage/references/safety-model.md`: map refs + repo-wide grep +
the language's dynamic-reference checklist + test evidence + git history.
One transform per commit; tests green before and after; revert on red.
Never delete tests to improve the numbers.

**Anti-speculation:** no interface/ABC with one implementer, no config for a
value that never varied, no pass-through wrappers (deprecation shims exempt),
no utils growth when the logic has a home.

**Scoreboard** — after every change run
`python .github/shrinkage/scripts/diffstat.py` and include its line in the PR
description (`--pr` prints a ready markdown block). Negative net app LOC is
the high score.
