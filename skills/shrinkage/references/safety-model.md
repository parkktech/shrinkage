# The Safety Model — how Shrinkage removes code without breaking anything

The prime directive: **a reduction that breaks behavior is worse than no
reduction.** Every rule in this document exists to make deletion *provably*
safe, because the failure mode of a minimalism tool is not "didn't shrink
enough" — it's "deleted something that was load-bearing."

Read this before any shave, audit execution, or consolidation. The surgeon and
verifier agent briefs assume it.

## 0. The Zeroth Law: backwards compatibility

No matter how much is added or removed, **backwards compatibility outranks
every reduction goal in this skill.** Shrinking is what we do; compatibility
is what we are. Concretely:

**The compatibility surface** — anything a consumer outside your control may
depend on: exported/public functions and their signatures, API endpoints and
response shapes, CLI flags, config keys and file formats, serialized data and
wire formats, DB schemas, published events, URLs, environment variables, error
codes/types that callers catch.

**The standing rules:**

- Changes to the compatibility surface are **additive-only**: new parameters
  get safe defaults, new fields are optional, new behavior is opt-in. This is
  why ladder rung 2 says "with a safe default" — an added parameter that
  changes existing call sites' behavior is a break, not an extension.
- Nothing on the surface is ever removed directly — removal happens only
  through the deprecation cycle (§5): alias/shim → warn → observe → remove.
- Renames on the surface are additions: the new name arrives, the old name
  becomes a delegating shim marked deprecated. (Yes, the anti-speculation
  rules forbid permanent single-delegation wrappers — a *deprecation shim* is
  the sanctioned exception: it is labeled, scheduled for removal, and exists
  precisely to protect callers.)
- Consolidations must leave every pre-existing entry point working: merge the
  bodies, keep the old signatures delegating until their deprecation window
  closes.
- When you can't tell whether something is on the surface, it is (treat as T2).

Internal code — private helpers, module-local functions, unexported symbols —
carries no compatibility promise, which is exactly why the evidence chain (§3)
works hardest at proving something is truly internal before touching it.

## 1. Why static evidence is never enough

The codemap's reference count (`xN`) is a *signal*, not proof. Real codebases
reference symbols in ways no static scan of source text sees:

- reflection and string-built lookups (`getattr`, `$class::$method`, `obj[name]`)
- dependency-injection containers wiring classes by string or convention
- route tables, event maps, cron configs, serializer registries
- templates (Blade, JSX-in-strings, Jinja) calling into code
- ORM conventions (model discovered by filename, magic accessors)
- external callers: published packages, webhooks, other repos, cron jobs

Therefore every removal must build an **evidence chain** (§3), and every
language rules file carries a **dynamic-reference checklist** naming that
ecosystem's specific hiding places. A deletion is only as safe as the weakest
link you actually checked.

## 2. Risk tiers

Every candidate transformation gets a tier before anything is touched. The
tier decides how much autonomy is allowed.

| Tier | What | Autonomy |
|---|---|---|
| **T0** | Textually inert code: commented-out blocks, unused imports, unreachable branches after a constant condition, exact-duplicate private functions | Remove directly; tests must pass |
| **T1** | Internal symbols with a complete evidence chain: dead private/module-local functions, single-use wrappers, single-implementer interfaces, near-duplicate siblings to consolidate | Remove/merge after full §3 chain + §4 gates |
| **T2** | Anything visible outside the module: exported/public symbols, API endpoints, shared library code, anything a template/config/reflection *might* reach where the checklist can't be fully closed | Propose with evidence; human confirms; prefer a deprecation cycle (§5) |
| **T3** | Behavior-changing "improvements": rewriting an algorithm smaller, changing data shapes, swapping dependencies | Out of scope for a shave. These are features — run them through the normal gate/plan flow with their own tests |

When in doubt between two tiers, take the higher one. The cost of asking is a
sentence; the cost of guessing is an outage.

## 3. The evidence chain (required for any T1 removal)

Collect ALL of these, in order — each step is cheap because the previous one
filtered:

1. **Map evidence** — symbol shows `x0` (or only self-references) in the codemap.
2. **Repo-wide textual search** — grep the *whole* repo for the symbol name,
   including non-code files: configs, YAML/JSON, templates, docs, migration
   files, CI pipelines, Dockerfiles. Zero hits outside the definition.
3. **Dynamic-reference checklist** — walk the language's checklist in
   `rules/<lang>.md`. For each item, either verify it doesn't apply or record
   why it can't (e.g. "no DI container in this project").
4. **Test evidence** — the symbol's file is exercised by the suite (so its
   removal will be *felt* by tests if anything is wrong), OR characterization
   tests are written first (§4).
5. **History check** *(cheap, revealing)* — `git log -1 --format='%ar %s' -- <file>`
   and a quick `git log -S<symbol> --oneline | head -5`. Code touched last week
   is suspicious to call dead; code untouched for 3 years whose feature flag
   shipped in 2022 is a strong candidate.

Record the chain in the commit message (see §6 template). A removal whose
evidence can't be written down in four lines isn't ready.

## 4. Test gates

- **Coverage-aware tiering**: before starting, run
  `python <skill>/scripts/coverage_check.py <target files>` against the
  project's coverage report (lcov / Cobertura / Clover / coverage.py JSON —
  auto-discovered, or `$SHRINKAGE_COVERAGE`). A target that is unreported or
  below the low-water mark is auto-escalated to **T2** — test gates cannot
  protect code the tests never execute. The path back to T1 is writing the
  characterization tests, not arguing with the tier. No coverage report at
  all → every deletion target is T2 until one exists, **unless the repo runs in
  suite-gated mode** (next bullet).
- **Suite-gated mode (no coverage artifact at all).** Some real repos have no
  coverage report and no cheap way to produce one — by the letter of the rule
  above, *every* target caps at T2, which flattens the whole tier system and
  makes the tool useless there. The sanctioned substitute: a target keeps its
  earned tier (T0/T1) **only if the plan row names the specific suite(s) that
  would observe a regression in it, and those named suites run green immediately
  before and immediately after the transform.** The named suite stands in for the
  coverage line — you're proving the change is *felt* by a test, which is what
  coverage was buying. Hard conditions, none optional: (a) the gate suite is
  named per row (a bare "the tests" doesn't qualify — name the file/group that
  actually exercises the target); (b) **no named observing suite for a target →
  it stays T2**, no exceptions; (c) the suite is green *before* — a red or absent
  baseline still hard-stops (§6b); (d) this is behavior-preservation only, so the
  suite must assert current behavior, characterization tests written first if the
  observing suite is thin. This is a deployment-wide standing mode, not a per-row
  override: the audit records the "no coverage → suite-gated" condition **once**
  in the plan header (not as per-row noise) and every row then carries its gate
  suite. Where a report is one command away (`pytest --cov`, `php artisan test
  --coverage`, etc.), prefer bootstrapping real coverage over suite-gating.
- **Green-before**: the full relevant suite passes before the first transform.
  If it's already red, stop — you cannot detect breakage against a red baseline.
- **Identical-failure-set mode (permanently-red corners).** Real repos have
  suites that are red for known, pre-existing reasons (ledger
  `## red-baselines`). Hard-stopping forever makes those corners unshavable;
  the sanctioned substitute: **record the exact failing-test names before,
  require the EXACT same set after** — `plan.py failset record -- <suite cmd>`
  → transform → `failset compare -- <suite cmd>` (exit 1 lists NEW failures =
  your break, and VANISHED ones = verify whether fixed or no-longer-running).
  Hard conditions: a shave whose target is the SUBJECT of the failing tests is
  still blocked (you'd be editing what the red tests test — repair first), and
  the corner carries a repair-first TODO regardless; this mode makes the corner
  workable, not acceptable.
- **Characterization first**: if the code being consolidated has no meaningful
  coverage, write golden-master tests for CURRENT behavior before changing it
  — including current quirks. You're preserving behavior, not fixing it; fixes
  are a separate, labeled commit. **For a CLI/command target the cheapest
  characterization is an output diff**: capture the command's read-only /
  `--dry-run` output before and after and require it byte-identical. This catches
  runtime method-resolution breaks — a missing trait `use`, a renamed call — that
  syntax checks and linters pass straight over (a paper-command dedup nearly
  shipped a `BadMethodCallException` that only an ad-hoc dry-run diff caught).
  When the target's `$signature`/arg parser advertises a dry-run mode, prescribe
  this gate automatically; framework rules carry the exact invocation.
- **Green-after, per transform**: run the gate after each atomic transform
  (§6), not once at the end of a batch. A batch with one failure and six
  entangled changes cannot be bisected cheaply.
- **Scope the suite honestly**: run the tests that could possibly observe the
  change, not just the ones in the same directory. When cheap, run everything.

## 5. The deprecation cycle (for T2, and for "probably dead but unprovable")

When the evidence chain can't be closed — reflection-heavy code, public
surface, unknown external callers — don't delete. Instrument:

1. Add a one-line deprecation log/telemetry counter at the symbol's entry.
2. Ship it. Wait an agreed observation window (a release cycle, a month of
   traffic — record the window in the audit plan).
3. Zero hits in the window → the chain is closed empirically; remove in T1
   fashion. Any hits → you just learned about a real caller for the price of
   one log line.

This converts "unprovable" into "measured" — the only honest path to shrinking
a public surface.

**Mechanized (PHP + Python):** `scripts/probe.py` runs this cycle end-to-end.
`probe.py add <file> <symbol> [--window N] [--logs GLOB …]` inserts the
counter at the body entry via the surgery engines (balance/parse-checked;
abstract bodies, one-liners, and code-on-the-brace-line are refused with the
fix), registers it in `.shrinkage/probes.json` (committed — the registry IS
the institutional memory), and adds the DEPRECATIONS.md row. The plan row
carries `probe: <id> since <date>`. **The counter only fires in RUNNING
code** — the probe commit must DEPLOY, and the window starts at arming, not
at deploy; if deploy lagged, extend the window mentally. `probe.py status`
reads the verdict per probe and refuses to flatter: **ALIVE** (marker found
in the logs → a real caller exists → keep the symbol, remove the probe),
**window open** (keep waiting), **BLIND** (zero log files matched the globs
→ telemetry is off, the zero means nothing — fix the globs or the deploy
before trusting anything), **CLOSED-ZERO** (window elapsed, real logs
watched, zero hits → the chain is closed empirically; remove the symbol
citing the probe id, then `probe.py remove <id>`). Other languages: refuse
to fake it — verify with the LSP oracle (`lsp_refs.py check`) plus the
checklist instead.

Every shim and deprecation created under this cycle is recorded in
**DEPRECATIONS.md** (repo root) as `- [ ] <old> -> <new> (remove <when>)`, and
the trend report counts unchecked entries — a shim without a scheduled,
tracked removal is just a wrapper with paperwork.

## 6. The transformation protocol

One transform = one atomic commit. Never batch unrelated removals.

```
for each approved candidate (highest payoff, lowest tier first):
  1. baseline: relevant suite green
  2. apply exactly ONE catalog transformation
  3. run gates (tests, lint/types, build)
  4. green → commit with the evidence template below
     red   → revert THIS transform entirely; record why in the audit plan
             (a failed removal is FINDINGS, not failure — you mapped a
              hidden dependency)
  5. run diffstat.py; confirm the change is net-negative or justified
```

Commit message template:

```
shrink: <transform> <symbol/file>

evidence: map x0; repo grep 0 hits (incl. templates/config);
checklist: <items verified or n/a>; tests: <suite> green before+after
catalog: <catalog entry #>, tier T<0|1>
net LOC: <n>
```

**Stage by explicit path — never the whole tree.** Commit with
`git commit -- <your target files> -m "<message>"` (path-limited); NEVER
`git add -A`, `git add .`, `git commit -a`, or `git commit -am`. The working
tree routinely holds the user's unrelated in-flight work — a path-limited commit
cannot sweep it into your shave. After committing, `git show --stat HEAD` must
list ONLY your transform's files; if anything else appears, `git reset --soft
HEAD^` and re-commit by path. (A surgeon once swept ~220 dirty files / +85k
lines of a user's in-flight feature work into one shave commit — this rule is
why that can't recur.)

The plugin enforces this **mechanically**, not just by instruction:

- Commit through `scripts/safe_commit.py -m "<msg>" -- <files>` — it stages and
  commits only the declared paths (deletions included), refuses if anything else
  is or becomes staged, and verifies after the commit that only your files
  landed.
- A PreToolUse hook (`hooks/guard_staging.py`) rejects `git add -A|.|--all|-u`
  and `git commit -a|--all` outright while a shave is active (marker
  `.claude/srk-shave-active`, which the shave workflow writes at batch start and
  removes at the end). Normal, non-shave sessions are never affected.

## 6b. The escape hatch (`--auto --dangerous`)

The safety model's autonomy limits (§2) exist to protect you by default. There
is one explicit, opt-in override — `/srk:shave --auto --dangerous` — for when
you knowingly accept the risk (you own/control every consumer of the code).
What it changes and, crucially, what it does NOT:

- **Drops:** the human-confirmation halt on T2/public-surface items, and the
  deprecation cycle — it removes public symbols directly.
- **Keeps (non-negotiable, even here):** one atomic commit per transform;
  tests green before and after each or auto-revert; a **hard stop on a red or
  absent test suite** (revertibility is meaningless without a green baseline);
  evidence re-verified per item.
- **The risk it accepts:** external consumers of your public API are not
  covered by your tests, so a direct removal can break callers outside the
  repo. That's the whole danger, and why it's named `--dangerous`.

It is refused when `allow_dangerous: false` (team kill-switch), and every run
opens with a loud banner naming the risk. This is the honest way to offer
"full send": loud, opt-in, still atomic and revertible — never a silent
loosening of the defaults.

## 7. The never-list

- Never delete on map evidence alone (§1).
- Never batch unrelated deletions into one commit (§6).
- Never remove or weaken tests to improve the scoreboard — `diffstat.py`
  counts app and test LOC separately for exactly this reason. Deleting a test
  is a T2 decision with its own justification, never a shrink win.
- Never touch public API surface autonomously (T2 by definition).
- Never "fix while shrinking" — behavior preservation and behavior change in
  one diff makes both unverifiable. Two commits, two labels.
- Never chase a percentage target at the expense of a single red test. The
  scoreboard is a compass, not a quota.
- **Never stage broadly during a shave** (`git add -A` / `git add .` /
  `git commit -a`). *The WIP-sweep incident:* on a working tree carrying ~179
  dirty files of the user's in-flight work, one surgeon's broad `git add` swept
  **220 files / +85,027 insertions** into a `shrink:`-labeled commit; only the
  scoreboard on the committed range (`app +31k`) caught it, and recovery needed
  a full history rebuild + a hash-verified restore of the WIP. Commit only your
  transform's files via `safe_commit.py`; the staging-guard hook enforces it.

## 8. What "smaller" realistically means

Set expectations with users honestly. Typical mature codebases carry roughly
10–30% removable-or-mergeable weight (dead flags, duplicated siblings,
speculative layers) — occasionally spectacular outliers more. The skill's
promise is **maximum reduction that survives the evidence chain**, compounding
over time: the gate stops new growth at the door, the shave reclaims the
backlog, the scoreboard keeps everyone honest. A one-shot "reduce by N%"
target is theater; a ratchet that only moves down is engineering.
