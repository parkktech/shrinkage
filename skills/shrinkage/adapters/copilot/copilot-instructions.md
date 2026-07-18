<!-- Shrinkage doctrine for GitHub Copilot — append to .github/copilot-instructions.md -->

## Code minimalism (Shrinkage)

The measure of a change is the goal achieved with the least code. Before
writing code, orient from the codemap, not by exploring the repo:

- Refresh/read the map: `python3 .claude/skills/shrinkage/scripts/codemap.py refresh`
  (map at `.claude/codemap.txt` or `.planning/intel/codemap.txt`); query it
  with `codemap.py query <term>`.
- Read `.claude/skills/shrinkage/rules/<language>.md` for each language you touch.

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
`.claude/skills/shrinkage/references/safety-model.md`: map refs + repo-wide grep +
the language's dynamic-reference checklist + test evidence + git history.
One transform per commit; tests green before and after; revert on red.
Never delete tests to improve the numbers.

**Commit discipline (no hook protects you here).** Claude Code runs a hook that
blocks broad staging during a shave; Copilot has no such rail, so it is a hard
rule: NEVER `git add -A`, `git add .`, or `git commit -a` while shaving — commit
through `python3 .claude/skills/shrinkage/scripts/safe_commit.py -m "<msg>" --
<files>`, which stages and commits ONLY the declared paths and verifies nothing
else landed (a broad `git add` once swept 220 files of a user's in-flight work
into a shave commit). A target with uncommitted changes is SKIPPED by default;
the opt-in exception is the scripted `dirty_apply.py park → precheck →
safe_commit → unpark` cycle — precheck runs BEFORE the commit and aborts if the
user's hunk isn't disjoint from your actual edit.

**The ledger** (`.shrinkage/ledger.md` or `SHRINK-LEDGER.md`) is durable
institutional memory: `## frozen` paths are NEVER edited (safe_commit refuses
them), `## excluded` globs never enter the map, `## keeps` are settled — do not
re-flag them. **The plan CLI** keeps SHRINK-PLAN.md honest: `plan.py open` /
`done <id> HEAD` (derives the sha + actual net LOC from git) / `restamp` /
`carry` — never sed. **No coverage report?** Use suite-gated mode
(safety-model §4): a T0/T1 row executes only when it names the specific suite
that would observe a regression, green before and after; no nameable suite → T2.

**Anti-speculation:** no interface/ABC with one implementer, no config for a
value that never varied, no pass-through wrappers (deprecation shims exempt),
no utils growth when the logic has a home.

**Scoreboard** — after every change run
`python3 .claude/skills/shrinkage/scripts/diffstat.py` and include its line in the PR
description (`--pr` prints a ready markdown block). Negative net app LOC is
the high score.

**Reducing existing code** — to shrink a project: build the map
(`codemap.py build`), find candidates via the audit sweeps (`codemap.py dupes`,
`codemap.py clones`, plus zero-reference symbols), then remove them following
`.claude/skills/shrinkage/references/safety-model.md` and `consolidation-catalog.md` —
one revertible commit per transform, tests green before and after, never
touching the compatibility surface.

**Economy** — when delegating: the mechanical edits (applying a decided
transform) can run on a cheaper/faster model; reserve the capable model for
deciding *what* to change and for verifying nothing broke. The test gate, not
the model, guarantees safety.
