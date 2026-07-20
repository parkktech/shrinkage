# Changelog

## 0.41.0
- **Installed-but-not-loaded now announces itself.** A correct install could
  still leave `/srk` empty when the running session hadn't registered the
  plugin — and nothing said so, to the user or to Claude, who would report the
  install as healthy. A watchdog at a stable path outside the plugin cache
  (`~/.claude/shrinkage/watchdog.py`), registered on `SessionStart` and
  `UserPromptSubmit`, now reports the state in-conversation and recommends
  `/reload-plugins` before a relaunch. It self-uninstalls when Shrinkage is
  removed. Hooks inside the plugin can't catch this — they don't run when the
  plugin doesn't load.
- Measured on Claude Code 2.1.215: `--continue` reuses `session_id` and
  `SessionStart` still fires, which is why the watchdog re-arms per boot rather
  than trusting a session-keyed marker.
- The planter keeps a one-time `~/.claude/settings.json.srk-bak` before its
  first write.

## 0.40.3
Onboard must ASK about a missing oracle and RUN it on yes — never end by just
printing a command. A field re-onboard on 0.40.2 did exactly the forbidden
thing: it showed "the one-line install if you want it: …" and moved on,
without ever asking. The instruction was there; it wasn't emphatic enough to
survive a "nothing drifted" re-run.

- **Onboard step 6 rewritten as an action with one forbidden outcome.** Default
  stays ask-first (`oracle_autoinstall` false): for each worth-it missing
  oracle, ask a single yes/no and — on yes — run the install itself; with the
  flag true, just run it. The one thing it may never do in an interactive
  session is end having only *shown* a copy-paste command. Runs on every
  onboard, including re-runs, so a missing oracle is a live decision, not a
  status line. (`oracle_autoinstall` default unchanged: false.)

## 0.40.2
The install flow now fails gracefully and specifically: try → if it can't,
tell you exactly what to hand your server admin → move to the next language.

- **Permission walls are caught, not dumped.** When a package manager fails
  for lack of privilege (only `npm i -g` against a system prefix can — pip
  `--user`, pipx, go, rustup are all user-level), `lsp_refs.py install` now
  says so plainly and prints two escape hatches: the **no-admin fix** (point
  npm at a user prefix, retry) and the **exact command to forward to a server
  admin**. Non-permission failures still surface the real error tail. A
  permission classifier (EACCES/EPERM/"permission denied"/root) distinguishes
  "ask your admin" from "the install is just broken".
- **Languages are independent.** One language failing never aborts the rest —
  the loop reports each outcome and moves on, so `install php javascript go`
  handles all three even if the first hits a wall. +2 tests (permission→admin
  message, continue-after-failure); the fake-package-manager harness gained an
  EACCES mode.

## 0.40.1
Onboard now DRIVES the oracle install instead of handing you a command. From
a field re-onboard: it detected PHP ✓ / JS ✗ (151 files) but buried the offer
under the status report, showed a raw `lsp_refs.py install` incantation, and
silently skipped Python without saying why — so it read as homework, not help.

- **Onboard drives, doesn't delegate.** The oracle step now: (1) decides which
  missing oracles are worth it by the map's file counts — skips 1–2-file
  languages and NAMES the skip so you're not left wondering about the other ✗;
  (2) asks ONE decisive question in plain language, not a per-language quiz and
  not a pasted command; (3) runs `lsp_refs.py install` *itself* on yes. The
  user never copies a command — the whole point is that Claude does it.
- **`oracle_autoinstall` setting (default false).** Set it `true` and onboard
  installs the oracle for your repo's main languages with no prompt at all —
  the hands-off switch. Still interactive-only: a background `npm i -g` never
  fires on a scheduled/unattended run, flag or no flag. +3 settings tests.

## 0.40.0
The oracle installs itself now — onboarding asks first, and nothing installs
behind your back.

- **`lsp_refs.py install [lang ...] [--dry-run]`.** For each missing oracle it
  picks the language's real package manager (npm for intelephense/tsserver,
  pipx→pip for pylsp, go, rustup), **gated on that tool actually existing**,
  runs it, then **re-checks the binary is on PATH** — a package that installs
  off-PATH is reported as a warning with the directory to add, never as a
  false ✓. Bare `install` does every missing language; `install php` scopes
  it. HARDCODED command table — it never runs a user-supplied string. +6 tests
  incl. a fake package manager exercising the run→verify→PATH-check loop, the
  off-PATH warning, honest failure surfacing, and prereq-missing.
- **Onboarding offers to install.** `/srk:onboard` now cross-references the
  ✗ oracles against the languages the repo actually uses and, in an
  interactive session, **asks per language and runs the install on yes**
  (unattended sessions print the line instead — a background `npm i -g` must
  never hang a scheduled run on a sudo prompt). Passive detection —
  `servers`, `check`, the audit itself — still never installs anything.
- **Storefront description refreshed.** plugin.json + marketplace.json blurbs
  were a release or two stale (no `/srk:coverage`, no mention of the oracle or
  probes) — the plugin was failing its own doc-truth rule. Now current.

## 0.39.1
README: the evidence engine gets its own section. v0.39's two capabilities
were only visible as flipped Roadmap entries — the wrong shelf for shipped
features. Now: a "What it does" bullet (proves it before deleting it), a
dedicated "The evidence engine" section stating the actual advantages in
field terms (the oracle removes the biggest first-audit cost line — ~100 of
154 x0s hand-cleared — and can't make the tool more credulous, only faster;
the probe turns the deferred-T2 graveyard into a queue with a clock on it),
and a Roadmap trimmed to what's genuinely still future (self-driving
deprecation PRs, more probe languages).

## 0.39.0
The two revolutionary-ceiling stones, design-first: the map gets an oracle,
and the deprecation cycle gets a heartbeat.

- **LSP-grade reference resolution — `lsp_refs.py`.** A minimal, dependency-free
  LSP client (Content-Length framed JSON-RPC over stdio) that asks a real
  language server the audit's exact question: `check <file> <symbol> …` runs
  `textDocument/references` on every map-x0 candidate. Server registry by
  language — pylsp/pyright, typescript-language-server, intelephense, gopls,
  rust-analyzer — one server session reused across the batch, rootUri at the
  git toplevel, interleaved server noise (notifications, server→client
  requests) handled without stalling. The verdict is deliberately asymmetric:
  **refs found → the false x0 is KILLED in seconds** (the class that cost a
  field run ~100 hand-cleared candidates out of 154); **zero found →
  `oracle-confirmed x0`, and the dynamic-reference checklist still runs** (LSP
  can't see DI containers, config strings, reflection, routes). No oracle →
  loud install hint, never a silent skip. `servers` shows what's installed.
  Wired into: audit step 3 (mandatory for x0s when an oracle exists), the
  auditor brief (killed false-x0s reported, not shipped), onboard (oracle
  check + install offer). +6 tests incl. a fake framed-protocol server and a
  live pylsp round trip.
- **Runtime deprecation telemetry — `probe.py`.** Safety-model §5, mechanized
  end-to-end minus the auto-PR: `add <file> <symbol> [--window N] [--logs G]`
  inserts a one-line entry counter (PHP `error_log`, Python `logging`) at the
  exact body entry via the surgery engines — after the docstring, balance/
  parse-checked, abstract/one-liner/K&R-brace bodies refused with the fix —
  registers it in committed `.shrinkage/probes.json`, and adds the
  DEPRECATIONS.md row. `status` scans the log globs and refuses to flatter:
  ALIVE (production caller found → keep the symbol), window open, **BLIND
  (zero log files matched → the zero means nothing — fix telemetry first)**,
  CLOSED-ZERO (window elapsed over real logs → chain closed empirically;
  remove the symbol citing the probe id). `remove <id>` restores the file
  byte-exact and ticks the row. Wired into: audit step 0 probe harvest
  (CLOSED-ZERO promotes the row, ALIVE flips it to a keep), the deferred-T2
  section, the shave halt menu, the auditor brief. Non-PHP/Python languages
  refuse toward the oracle + checklist. +7 tests.

## 0.38.0
The queue, drained — plus the ecosystem stone. Five capabilities from the
standing backlog, each field-motivated.

- **#10 — `/srk:coverage`** (`coverage_check.py bootstrap [--run]`): detects the
  repo's test ecosystem (pest/phpunit with a pcov/xdebug driver check,
  pytest-cov, vitest/jest, go + the gcov2lcov note, cargo-tarpaulin) and prints
  the exact one-command upgrade from suite-gated to coverage-aware tiering;
  --run executes it with user confirmation. Both deployments ran suite-gated
  forever for want of exactly this. +3 tests.
- **#7 — Staging guard self-cleans.** Stale markers from crashed shaves are
  deleted on sight (the 2h TTL already stopped them guarding; now they can't
  linger or re-arm), and the workflow arms the guard with forensic content
  (session id + timestamp), not a bare touch. +1 test.
- **#6 — Structured bugs table + `plan.py bug-done`.** `## Bugs found` is a
  table with B-ids; `bug-done B-1 HEAD` strikes the row with sha + derived LOC
  — the fix-first pipeline is as auditable as the shave pipeline. +1 test.
- **#2 — Identical-failure-set gate.** `plan.py failset record|compare --
  <suite cmd>`: capture the exact failing-test names of a permanently-red
  corner (phpunit/pest, pytest, go), then require the IDENTICAL set after a
  transform — new failures exit 1 as your break, vanished ones demand
  verification. Safety-model §4 defines the mode; never shave the failing
  tests' own subject. +1 test.
- **#9 — The growth gate.** `diffstat.py <range> --ci-gate [--strict]`:
  diff-sized checks on every push — net growth, public signature changes,
  unjustified new symbols, and dupe-shaped new symbols (a name already living
  elsewhere in the map: C1/C9 being born). Pre-push snippet + ci/growth-gate.yml
  Actions example. Closes the front door the 78k-line commit walked through.
  +1 test.
- **Ecosystem self-defense** (new, from the GSD collision): every plan.py
  operation stamps a content hash and warns — non-blocking — when the plan was
  modified outside plan.py since the last srk write. +1 test.

Deliberately NOT in this wave: LSP-grade reference resolution and runtime
deprecation telemetry — the two revolutionary-ceiling items — each needs its
own design-first pass, not a slot in a batch. They stay top of the roadmap.

## 0.37.1
README articulates the field-tested value, not the marketing value.

- **"Where the value actually is"** — three layers, ranked honestly: the
  one-time backlog drain (real, but once), the compounding steady-state habit
  (gate + scoreboard + ratchet + per-milestone re-audits, with the token cost
  stated plainly), and the surprise dividend — evidence-first auditing keeps
  finding production bugs nothing else caught, with the field list (the inert
  kill-switch, the no-op cache invalidation, prior-day dates, lying test
  gates). Duplication divergence is a bug detector.
- **Safety machinery framed as field-scarred** — every mechanical guard traces
  to a real incident, named.
- **Roadmap section** from the field verdicts: LSP-grade reference resolution
  (kill the false-x0 class, cut audit cost), runtime deprecation telemetry
  (auto-instrument → zero-hit window → the removal PRs itself), CI-native
  continuous sweeps, divergence-as-bug as a first-class product, ecosystem
  awareness (co-installed tooling that shares .planning/).
- Stale bits fixed: six→seven sweeps, status-line extras updated (chaining,
  update nudge, onboard-first). Doc-only.

## 0.37.0
The meta-gaps: what two deployments' worth of transcripts show the audit still
doesn't ask for.

- **`## Rails (make recurrence impossible)`** — new standard plan section. Every
  violation CLASS found or fixed (local copies of a canonical util, raw `fetch`
  beside an axios convention, hand-rolled cookie/cache-key formats) gets the
  mechanical enforcement that ends the class — an ESLint
  no-restricted-syntax/globals rule, a phpstan rule, a wrapper-as-only-import —
  not just fixed instances. Fixed is good; impossible is better. A field
  instance produced exactly this table by judgment; now it's doctrine.
- **`## Coverage gaps (what blocks future shaves)`** — the untested-but-critical
  surfaces (money paths, webhooks, unattended jobs first), each with what its
  test UNLOCKS (the T2 rows that become T1). The audit's answer to "why is half
  the backlog deferred?", promoted from prose to schema.
- **Suite-health flags SELF-NEUTRALIZING tests** — assertions wrapped in a
  conditional on the thing under test (`if ($finding) { expect(...) }`) pass
  vacuously when fixtures drift; a field run found one already hollow and 7
  siblings primed. Grep named suites for conditional-assertion shapes; each is
  a bugs-found entry (assert existence FIRST).
- **Doc-truth check** — agent-facing docs (CLAUDE.md/AGENTS.md) are audit
  inputs; verify their cheap claims (test counts, named suites, commands)
  before trusting them. A stale AGENTS.md ("131 tests" vs a real 1,433) misled
  two audit agents in the field; stale agent docs are a bugs-found entry.
- **Self-instrumenting field reports** — every --auto/--full-send run writes
  `.planning/srk-field-report-<date>.md`: incidents, WORKAROUNDS (each one a
  missing feature wearing a disguise), refusals hit and whether they were
  right, gaps improvised, versions. Seven hand-pasted field reports built the
  last twenty releases; the loop now feeds itself. Doc-only.

## 0.36.2
Close-out lessons from the fresh-codebase run's final stretch.

- **Surgeons mark their own rows done — immediately.** The workflow said
  surgeons mark plan rows; the surgeon BRIEF never listed it as a step, so a
  33-row run ended with zero rows struck and the orchestrator reconstructing
  every sha↔row pair from memory at close (after reading plan.py's source to
  debug why). New brief step 7: `plan.py done <row-id> HEAD` right after the
  commit; batch-reconciling at close-out is forbidden — one transposed sha
  silently corrupts calibration data.
- **Suite-health flags live-external-API suites.** The run found 4 suites
  hitting the real Anthropic API every run and surfaced it ad hoc; now it's a
  standard suite-health category — each becomes an owner TODO with the
  fake-or-record/replay recommendation (cost-per-run, flaky by weather, a
  secrets surface, and it slows every gate that names it).
- **Full-send leftovers carry recommendations.** The completion report's ⚖
  list follows the decision-blocked format — recommended answer + evidence
  rationale + reply syntax — not bare "which is intended?" questions. Doc-only.

## 0.36.1
The symlink guard — from the CLAUDE.md → AGENTS.md incident.

- **`safe_commit.py` refuses type changes.** A surgeon edited `CLAUDE.md` and
  silently converted it from a tracked symlink (→ AGENTS.md) into a regular
  file — editing *through* a link replaces the link itself. safe_commit now
  detects symlink ↔ regular-file typechanges among the declared paths, unstages
  them, and refuses with the fix (`readlink <path>`, edit the TARGET, keep the
  link); the deliberate-restore path stays available via `--allow-typechange`.
  The surgeon brief gains the pre-edit rule: `test -L` before editing any file
  — a link means you edit its target, never through it. The field run caught
  and repaired the decoupling itself; now the guard refuses it at commit time
  instead. +1 test.

## 0.36.0
Autonomy boundaries, from the first fresh-codebase field run (seventh report):
the run was excellent — and crossed three lines the doctrine had never drawn.

- **Fix-first bugs get an autonomy boundary — even under `--full-send`.**
  Mechanical fixes (fetch→axios consistency, cookie-domain alignment, missing
  imports, wrong cache keys) may auto-execute. A fix that CHANGES OBSERVABLE
  BEHAVIOR — what a findings/detection engine emits, money math, displayed
  numbers/dates, response shapes, an assertion flipped from conditional to
  mandatory — is a ⚖ operator fork, exactly like removing public surface. In
  the field run, `loanServicer: true` made a tax product always emit a finding
  that was previously conditional, decided solo mid-audit. Full-send authorizes
  autonomous subtraction; it never authorizes choosing new behavior.
- **The tool never commits the user's WIP.** A `wip:` commit made by the tool
  decides message, grouping, and whether half-done work is coherent — the
  user's calls. Sanctioned paths: hand it back, park/precheck/unpark per file,
  or an explicit user instruction (then ONE plain wip: commit, never pushed).
- **The TODO gate is the user's gate.** The tool may check off mechanical items
  it completed; decision/behavioral items are checked only after the user's
  ruling — full-send doesn't transfer the gate. (The field run self-cleared all
  7 items in one heredoc.)
- **Build-only gates are named honestly.** `npm run build`/`tsc`/`php -l`
  prove compilation, not behavior — rows carry `gate: build-only`, and a
  behavior-relevant frontend change on one deserves a runtime check or an
  explicit note that none exists.
- **`plan.py todo-check` takes several items or `--all`** — the field run
  bypassed the one-at-a-time CLI with a hand-rolled heredoc; the limitation is
  gone. +1 test.

## 0.35.1
Onboard is unmissable in the command picker — within what a plugin controls.

- **`/srk:onboard` description now leads with `▶ START HERE`.** The picker's
  ordering is host-controlled and undocumented (observed: usage-based, so a
  veteran's picker correctly demotes onboard; a plugin has no priority/pin
  field — pinning is filed upstream as anthropics/claude-code#58593). The one
  plugin-owned pixel in that list is the description text, so the entry point
  now reads as the entry point wherever it sorts. The rest of the funnel
  already routes new users there without the picker: the session-start nudge,
  `/srk:help`'s opening banner, the Next-menu rule, and the status line.

## 0.35.0
Language-matrix parity: the PHP-era improvements now cover every supported
language, template family, and test ecosystem.

- **`extract_method.py` goes multi-engine.** Java, C#, Kotlin, Go, and Rust get
  per-language exact tokenizers (each language's traps handled or refused: Java
  text blocks, C# interpolated/verbatim strings, Kotlin `${}` templates and raw
  strings, Go backtick raw strings, Rust lifetimes-vs-char-literals, NESTED
  block comments, and raw strings). Python gets a stdlib-`ast` engine — exact
  spans including decorators and leading comments, and a stronger comment-only
  verdict (AST-identity with docstrings stripped) — plus `wire --mixin
  'pkg.mod.Class'` (import + first-class bases). JS/TS gets the tree-sitter
  engine (the plugin's existing optional exact path): JSDoc-inclusive spans,
  auto-`export` on extraction, `wire --import`; absent tree-sitter → loud
  install-hint refusal, and JS class methods refuse extract (`this`-binding is
  behavior). Templates (Blade markup, Twig, Vue/Svelte/…) refuse with the real
  guidance — dedupe there is partial/component extraction, gated by the
  template compile. `wire --import '<verbatim>'` works across Java/C#/Kotlin/
  Go/Rust/Python/JS. Cross-language extract refuses. +6 language tests (the
  JS test runs live against tree-sitter and skips when it's not installed).
- **`plan.py verify-gates` learns every test ecosystem.** Suite tokens now
  match `FooTest.java`/`FooTests.cs`/`FooTest.kt`, `*_test.go`,
  `*.test|spec.[jt]sx?` alongside phpunit/pytest paths; runner auto-detect adds
  gradlew, `go test`, `cargo test`, `dotnet test --filter`, and `npm test --`
  (with per-runner argument adaptation — gradle wants a class name, go wants
  `./pkg`); output classification reads go/cargo/gradle/jest/dotnet results
  (and "0 failed" no longer reads as red). +1 matrix test.
- **Compat-watch knows Go and Rust visibility.** Go: unexported (lowercase)
  functions no longer warn on signature change; Rust: `fn` without `pub` on
  both sides is internal. Keyword languages were already covered; Python stays
  conservative. +1 test.
- **Gate recipes for the other frameworks.** `rules/frameworks/{android,
  magento2,drupal}.md` gain the same file-type → cheapest-sufficient-gate
  section Laravel got: `compileDebugKotlin`/`lintDebug`/`testDebugUnitTest`,
  `setup:di:compile`/`module:status`/`cache:clean`, `drush cache:rebuild`/
  `config:status` — framework institutional memory, not session memory.

## 0.34.1
The PHP-only boundary of extract_method is now mechanical, not just documented.

- **Language guard.** The doctrine said "PHP" but the tool accepted any file —
  and its tokenizer would be actively WRONG on other languages (JS backtick
  templates with `${}` braces, regex literals, `#` private fields all fool the
  span). Every command now refuses non-`.php`/`.phtml` paths (source AND
  destination) with exit 2 before touching anything. The shave workflow gains
  the cross-language rule: other languages run the same check→extract→remove→
  wire loop manually (identity verified before any copy is deleted) until
  per-language engines land — Python via stdlib `ast`, JS/TS via the existing
  optional tree-sitter path. A loud single-language tool beats a quiet
  multi-language liar. +1 test.

## 0.34.0
Field-report item #3, as its own focused release: scripted C1/C9 surgery.

- **`scripts/extract_method.py`** — the extract → check → remove → wire loop
  that was hand-scripted twice in production (aggregateGuardResults, credential
  accessors), including one mid-flight abort from an indentation-slicing bug —
  now a tool the cheap surgeon model can run safely:
  `find <file> <method>` (span: attributes + docblock + brace-matched body) ·
  `check <method> <hostA> <hostB> […]` (identity verdict: identical /
  indent-shifted / comment-only / **DIVERGENT exits 3** — two copies that differ
  are two behaviors) · `extract … --to HOME` (byte-exact copy; scaffolds a
  namespaced trait when the home is new; `--namespace` required across
  directories — no PSR-4 guessing) · `remove` · `wire --use '\FQ\Trait'`
  (idempotent). Safety properties are the point: brace matching runs on a real
  tokenizer (strings, escapes, comments, `{$interpolation}` can't fool the
  span), heredocs and ambiguous names are refused loudly, and every mutation is
  built whole + balance-checked before a single byte is written — a failed
  check writes nothing. The shave workflow, surgeon brief, and catalog C9 now
  mandate it for PHP method merges: never hand-sliced again. +6 tests, fixtures
  shaped like the production cases (braces in strings/comments/docblocks).

## 0.33.0
Field-report wave 4 (sixth production day): gates that are actually run, a plan
CLI that touches everything, and churn-proof paths. Items #1/#2/#4/#5/#6/#7 of
the report; #3 (`extract_method.py` surgery helper) ships next as its own
focused release — it edits production code and deserves an undivided pass.

- **#1 — Suite-health, the seventh audit sweep.** The day's biggest find wasn't
  dead code — three named gate suites were lies (a 21-error/0-assertion suite
  guarding live-money risk guards; a born-red shell; 5F asserting retired
  behavior), and row 9 was applied-then-reverted purely because its gate was
  recorded green without being run. The audit now RUNS every named gate.
- **#2 — `plan.py verify-gates [--runner CMD]`.** The mechanization: every open
  row's named suite runs in its OWN process (suites green individually errored
  together — process pollution), and the ACTUAL color is stamped into the row
  (`verified: green|RED|0-ASSERT|SKIPPED <date>`); exit 1 on RED/0-ASSERT.
  Runner auto-detected (phpunit/pest/pytest). +1 test, offline fake-runner.
- **#4 — Ledger `## red-baselines`.** Known-red/quarantined suites become
  institutional memory: audits stop re-discovering them, shaves treat rows
  gated on them as repair-first, the entry is removed when fixed.
- **#5 — `plan.py` reaches the whole plan.** `done D-30 HEAD` strikes
  deferred-table rows (sha + actual derived as usual), `todo-check <n|text>`
  ticks TODO-gate checkboxes and reports remaining/CLEAR, `adjudicate D-32
  "<ruling>"` records operator rulings durably in the row — four hand-edit
  sessions' worth of sed, gone. +2 tests.
- **#6 — `$SKILL` resolves fresh per invocation.** Five mid-session updates
  stranded version-pinned cache paths in every command. All command files now
  resolve churn-proof: `${CLAUDE_PLUGIN_ROOT}`, else the newest installed copy
  (`ls -dv … | tail -1`), else vendored — never a remembered path.
- **#7 — Status line shows the gate.** `srk ▼-6189 · streak 7 · TODO 3` (or
  `· TODO clear`) — whether shaving is unblocked, at a glance. +1 test.

## 0.32.3
The decision-blocked close: when only your calls remain, the tool says so.

- **"Nothing left to run — the next step is a decision, not a command."** The
  last uncovered Next-state: backlog drained, only ⚖ adjudications left, and
  the close still offered commands (`/srk:trend`) that read like the expected
  next step. New format (SKILL.md response style + shave workflow): lead with
  the no-command statement, then a **Your call** list — each decision as a
  one-line question WITH a recommended answer + one-line evidence rationale
  whenever the evidence supports one (or an honest "genuinely your judgment"),
  and the exact reply syntax so answering costs one line. At most one optional
  line, explicitly labeled "doesn't advance the backlog". Doc-only.

## 0.32.2
Compat-watch stops flagging private methods (reported from the fifth field run).

- **Visibility-aware signature warnings.** The scoreboard's Zeroth-Law watch
  flagged ANY changed signature — including a private method (`estimateFees`),
  which is internal refactoring, not a compatibility concern. diffstat now
  checks the declaration site in both file versions and suppresses the warning
  only when the symbol is explicitly `private`/`protected` on BOTH sides with no
  same-name public declaration; public, ambiguous, or convention-only visibility
  (Python underscores) keeps the warning. Works on both parser paths (regex and
  tree-sitter) since it reads the source text, not parser metadata; applied to
  working-tree/range scoring and `--shave-only` alike. +2 tests.

## 0.32.1
The mission, stated where the AI reads it.

- **SKILL.md opens with the three-goal operating test:** (1) a small,
  super-efficient codebase, (2) the highest-quality cleanup possible — size is
  never bought with quality, (3) keep the AI on track while working in,
  building, and maintaining the codebase. Pillar 3 was always load-bearing
  (map vs exploration drift, gate vs scope creep, plan/ledger vs fresh-context
  drift, TODO/tier/red-baseline gates vs pushing through) but never stated;
  now every session reads it as the test each action must pass. README leads
  with the same mission. Doc-only.

## 0.32.0
Domain conformity: dedup never crosses class-type boundaries the wrong way.

- **The cross-domain home-selection rule** (consolidation catalog). Same bytes ≠
  same concept: byte-identical methods on, say, `UserProfile` and `StockType`
  are exactly one of — *neutral concept* (hoist to a domain-neutral home named
  for the concept, `Support\MoneyFormat` not `UserProfileHelper`; BOTH domains
  depend on it, arrows point domain → shared only), *one true owner*
  (T2/adjudication — never auto-merge, and never "just call the other domain's
  method"), or *coincidental twins* (identical today, different reasons to
  change → do NOT merge; ledger keep "will diverge"). The change-reason test
  decides: "would A's copy ever need to change differently from B's?" — yes or
  unsure → keep the duplication; it's cheaper than the wrong abstraction. The
  neutral home still pays the full quality bill: ladder-governed creation, no
  grab-bag utils, C9's honest defs-collapsed pricing.
- **Wired at both ends.** The duplication sweep + auditor brief classify every
  cross-domain pair and must quote their change-reason answer (neutral-home
  candidates name the proposed home; one-owner → design note; coincidental →
  proposed keep). The reuse gate gets the write-time mirror: a candidate from
  another domain is never "extendable" across the boundary — either the concept
  is neutral (hoist + both call it) or the verdict is "not applicable:
  cross-domain", even on a perfect byte match. C1/C9 gotchas point at the rule.
  Doc-only.

## 0.31.0
The status line composes with what you already have — never replaces it.

- **Chained mode (`--segment`).** settings.json has ONE statusLine slot; a user
  with GSD's bar (model, phase progress, context %) would have LOST it by
  installing Shrinkage's. Now: an existing status line is never replaced —
  setup wraps their command verbatim and appends the srk segment on its own
  line beneath (multi-line bars are supported; stdin is tee'd to both).
  `statusline.py --segment` prints just the srk part for exactly this.
- **Standalone mode renders the session basics.** When Shrinkage's bar IS the
  status line, it now reads the stdin session JSON and shows model │ directory
  │ `ctx ███░░░░░░░ 31%` │ srk … — so choosing it never loses what a
  general-purpose bar would have shown.
- **Three-state setup detection.** The SessionStart hook distinguishes: no
  status line → nudge setup in every Next menu; a foreign status line without
  the srk segment → offer the chain ONCE (a single Next-menu line, never a
  recurring nag); srk present → silent. Onboard checks the slot first and shows
  a before/after confirmation before rewrapping a setting another tool
  installed. +2 tests (standalone bar renders basics; segment prints only srk).

## 0.30.1
The status line becomes unmissable until it's on.

- **Onboard asks it FIRST.** The status-line offer moves ahead of every other
  preference — it's the always-visible layer (trend, streak, `⬆ /srk:update`
  alerts), and a user without it goes releases-blind.
- **Every Next menu nudges while unconfigured.** The SessionStart hook now
  checks the project + user settings for `statusLine` and, when absent, tells
  the session so — every command's Next menu then carries "turn on the
  Shrinkage status line" as the first suggestion after the primary action
  (SKILL.md response-style rule). The nudge disappears the moment it's
  configured.
- **`/srk:help` leads with it.** When unconfigured, the help screen opens with
  one line — `⬆ Status line off — say "set up the status line" or run
  /srk:onboard` — above the command list, and onboard's help entry now names
  the status line. Doc/config-only.

## 0.30.0
Visibility release: the status line finally shows up, tells you when you're
behind, and the audit stops re-sweeping unchanged trees without asking.

- **Status line update nudge (GSD-style).** The status line appends
  `⬆ /srk:update to vX.Y.Z` when the marketplace has a newer release than the
  installed plugin. Renders never block: displays read a 6h-TTL cache; a stale
  cache spawns a detached background worker that runs `git ls-remote --tags`
  against the marketplace clone's ORIGIN — catching new tags even when the
  local marketplace clone is stale (the lag that kept a deployment on 0.26.2
  through three releases). +4 tests, fully offline.
- **Onboard now offers the status line.** Field report: it "has never shown."
  Correct — Claude Code renders a status line only when settings.json defines
  one, a plugin cannot set that for itself, and onboarding never offered it, so
  `statusline.py` shipped dormant since v0.5. `/srk:onboard` now asks and, on
  yes, merges a version-agnostic command (`ls -dv … | tail -1` — survives plugin
  updates) into `.claude/settings.json`.
- **Audit freshness gate.** Re-running `/srk:audit` over an unchanged tree
  produced an unclear skip-and-restamp narration. New step 0: when a current
  plan exists and nothing changed, ASK — work the plan / re-verify only /
  `--force` a full re-sweep (unattended runs default to re-verify and say so);
  code moved → full audit with carry-over. Every path, sweeps or not, ends with
  the same `Results:` / `TODO before advancing:` close so the next action is
  never ambiguous.

## 0.29.1
Readable reports: spacing and short lines, no walls of text.

- **Audit report template reformatted.** `Results:` is now label-left/value-
  right, one fact per line (the scoreboard's one-metric-per-line discipline),
  with the top 3 on a line each instead of chained ①②③ clauses. TODO items get
  a blank line between them and two short lines each — headline (tag + what),
  then the `→ action` on its own line. The plan's `## TODO before shaving`
  checklist uses the same two-line-per-item shape.
- **General layout rule in SKILL.md response style**, applying to every
  command's output: one fact per line, blank line between multi-line list
  items, headline-then-indented-action, and never a packed multi-clause line
  (`a — b · c → d; also e`) where a split would read cleaner. Doc-only.

## 0.29.0
The audit report becomes a handoff, not a findings dump — and the shave enforces
it.

- **Two-section audit report: `Results:` / `TODO before advancing:`.** Results
  stays lean (counts, tier mix, top 3 by payoff, plan pointer). The TODO section
  lists the genuine blockers — fix-first bugs, security hazards (a secrets file
  in the webroot), tooling/environment issues (a stale plugin, a red baseline a
  planned gate needs) — each written as a paste-able imperative with the exact
  action, ending with the rule: **do NOT start `/srk:shave` until the list is
  clear** (explicit "shave anyway" waives it). Empty list → "no blockers — shave
  when ready".
- **The plan carries the gate: `## TODO before shaving`.** The audit writes the
  same items into SHRINK-PLAN.md as a checkbox list, so the gate is durable
  state, not chat prose. Only genuine blockers qualify — deferred ⚖ decisions
  that gate nothing executable stay in their own section, so the list stays
  short enough to respect.
- **The shave checks it.** New step 0 of the shave workflow (and the command +
  Copilot prompt): any unchecked `- [ ]` under `## TODO before shaving` → stop,
  report the open items verbatim, execute nothing, unless the user explicitly
  waives. Items get checked off (`- [x]`) as they complete so the gate clears
  itself. Rationale is stated where it gates: shaving over an unfixed bug bakes
  it into consolidated code; an open hazard outlives the batch. Doc-only.

## 0.28.0
First-class GitHub Copilot support via the Agent Skills standard.

- **Skills-native install.** Copilot (cloud agent, code review, CLI, VS Code/
  JetBrains agent mode) now loads SKILL.md agent skills, discovering them from
  `.claude/skills`, `.github/skills`, and `~/.copilot/skills` — so ONE vendored
  copy at `.claude/skills/shrinkage/` serves Claude Code and every Copilot
  surface. The adapter README is rewritten around this path; the old
  instructions-append + prompt-files install remains as the fallback/extras.
- **SKILL.md "Other runtimes" portability section.** How the skill degrades
  outside Claude Code: $SKILL = the skill folder, workflows stand in for
  `/srk:*` commands, agent briefs run inline — and with no PreToolUse
  staging-guard hook, `safe_commit.py` and the `dirty_apply.py park → precheck →
  unpark` cycle are mandatory discipline, not belt-and-suspenders.
- **Copilot doctrine caught up to the field hardening.** The always-on
  instructions file (stuck at v0.5-era rules) now carries the P0/P1 rails:
  path-limited commits via `safe_commit.py` (never `git add -A` — Copilot has no
  hook to save you), the frozen/excluded/keeps ledger, the dirty-target
  protocol, the plan CLI (`done <id> HEAD` derives actuals), and suite-gated
  tiering. Shave/audit prompt files refreshed to match; all adapter paths
  re-anchored from `.github/shrinkage/` to the vendored skill at
  `.claude/skills/shrinkage/`. No `allowed-tools` pre-approval on purpose —
  keep Copilot's command confirmations for a tool that deletes code.

## 0.27.0
Field-report wave 3 (second production day, edge-trades): the four highest-impact
gaps, each hit as a real incident, plus a pre-release review pass that corrected
its own math.

- **#1 — Pre-flight disjointness (`dirty_apply.py precheck`).** Not-disjoint
  edits were discovered only at unpark time — AFTER the shave commit existed,
  leaving a committed shave to hand-revert (the QuantDiscoverService incident).
  New mandatory step between the surgeon's edit and the commit: `precheck` stages
  the shave, dry-runs the exact 3-way merge unpark would perform, and on conflict
  restores the user's pre-shave file and exits 3 with NO commit made; on success
  it unwinds so the pending commit stays shave-only. Disjointness is proven
  against the ACTUAL edit shape, not the plan's stated region (an import-block
  edit can collide even when the plan's target lines were disjoint). Sequence is
  now park → edit → precheck → safe_commit → unpark. +3 test scenarios.
- **#3 — CLI characterization output-diff, a named gate.** A missing class-body
  `use` passed `php -l` and would have thrown at runtime; an ad-hoc `--dry-run`
  output diff caught it pre-commit. Now first-class: for a command target
  exposing a read-only/`--dry-run` mode, capture its output before and after and
  require it byte-identical. Laravel gate recipes auto-prescribe it when
  `$signature` contains `--dry-run`; generalized in safety-model §4; surgeon
  brief instructs it. Doc-only.
- **#4 — Honest C1/C9 estimates; rank dedups by value, not LOC.** Row 5
  estimated −70 and netted +1 because the documented shared home costs what the
  naked duplicates saved. Catalog + audit now price the new home —
  `N × block − (merged body + docblock + N call-lines)` — and rank C1/C9 by
  duplicate definitions collapsed and bug-surface removed, so a near-zero
  realization factor doesn't bury genuinely valuable merges. Doc-only.
- **#5 — `plan.py done` derives actuals from git.** `done 5 HEAD` stored the
  literal string "HEAD" and no actual unless the operator remembered the number
  — the calibration loop silently starved. `done <id> <ref>` now resolves the ref
  to a real sha and derives the actual net app LOC via diffstat's single-commit
  scorer, feeding calibration automatically (pass an explicit actual only to
  override); recording at done-time also makes the datapoint amend-proof. +1 test.
- **Review pass before release:** corrected the C1/C9 formula (the first draft
  double-subtracted the merged body — over-pessimistic by one full block), fixed
  `park`'s printed guidance to include the mandatory precheck step, and hardened
  the abort path (a follow-on unpark after a precheck abort refuses cleanly).

Queued from the same report: #2 identical-failure-set gate, #6 structured bugs
table, #7 staging-guard TTL, #9 pre-push growth gate, #10 coverage bootstrap.
(#8 is solved today by adding `.agent/**`, `.codex/**`, `.gemini/**` etc. to the
ledger's `## excluded`.)

## 0.26.3
Response-style fix: every command ends with a clear directive, not a command menu
you have to decode.

- **The Next block leads with the one concrete action, plainly.** Commands were
  ending on a list of `/srk:` options with the real next step buried in a
  condition ("row 5 becomes executable after…", "the natural next sweep"),
  leaving the user to work out what to actually do. SKILL.md's response-style
  convention, both the audit and shave workflows, and the shave/audit/trend
  `<next>` blocks now require leading with the single clearest action as a plain
  imperative — including a non-`srk` step (commit or stash in-flight work, land
  the branch, adjudicate a ⚖ decision, fix a flagged bug) when that's the real
  move — and phrasing any future step as an explicit condition → action ("When
  your branch lands, run `/srk:audit`"). When the ball is in the user's court and
  no command is the move, the tool now says so outright instead of padding the
  slot. Doc-only.

## 0.26.2
Fix `dirty_apply.py unpark` false-refusing genuinely disjoint hunks — caught
empirically before the first production park/unpark on the edge-trades WIP.

- **`unpark` re-applies with a 3-way merge, not fragile context matching.** Plain
  `git apply --recount` matched the parked hunk by its few lines of surrounding
  diff context, so when the shave deleted lines that fell inside that context the
  re-apply failed and the tool wrongly reported "NOT DISJOINT" — refusing exactly
  the disjoint case `--allow-dirty-disjoint` exists to handle (reproduced: a WIP
  edit two lines above a removed cluster). It now uses `git apply --3way --recount`,
  merging against the base blob the patch was cut from: a genuinely disjoint hunk
  re-applies cleanly even when its context was shaved, while a true overlap still
  conflicts and triggers the byte-exact restore. Unmerged index residue from a
  conflicting 3-way is cleared, and the restored WIP is kept unstaged so it can't
  slip into the next commit. Nothing was ever unsafe — the backup/restore
  guarantee held throughout — but the tool now actually works for its intended
  case. +1 test (disjoint hunk adjacent to the shave region).

## 0.26.1
Hotfix for the ledger reader (reported from the edge-trades deployment).

- **Ledger read is now lenient.** `ledger.py` read `.shrinkage/ledger.md` as
  strict UTF-8 and caught only `OSError`, so a hand-authored ledger saved as
  Windows-1252 / Latin-1 (e.g. an em-dash in a reason line) raised an uncaught
  `UnicodeDecodeError` — a `ValueError`, not an `OSError` — and crashed every
  `codemap` build and audit that reads it. It now reads with `errors="replace"`
  and treats any read/decode error as "no entries", so a mis-encoded or CRLF
  ledger degrades gracefully instead of taking the map down; the first path/glob
  token per row is still recovered exactly. +2 tests.

## 0.26.0
Second wave of the production field-report hardening (items P1.4–P2.12; P0.1–P1.3
shipped in 0.25.0). Institutional memory the tool owns rather than the session —
estimate calibration and a plan-file CLI — plus a batch of tooling-correctness
fixes: the trend log moves out of the working tree, coverage-absent repos get a
real tiering mode, framework gate recipes and a bugs-found plan section become
first-class, `codemap scope` stops littering the tree, and the scoreboard can
isolate the shave commits in an entangled range.

- **P1.4 — Estimate calibration.** `/srk:score --log --cat C9 --est -140` now
  records the catalog + estimate alongside the actual net LOC; `/srk:trend`
  prints a per-catalog realization factor (actual ÷ estimate). Audit tells
  auditors to scale C1/C9 estimates by the observed factor — byte-identical
  output constraints make dedupe merges realize well under the naive line count
  (the deployment saw ~40% twice). +2 tests.
- **P1.5 — `plan.py` CLI.** `scripts/plan.py open|done|restamp|carry` edits
  SHRINK-PLAN.md reliably instead of by sed: `open` lists open rows, `done <id>
  <sha> [actual]` strikes + annotates the row and feeds the P1.4 calibration
  loop, `restamp` refreshes map-fp + recomputes est-savings from the open rows,
  `carry <old-plan>` emits a new plan skeleton of the still-open rows. The
  markdown stays the source of truth. Audit + shave workflows call it. +3 tests.
- **P2.6 — Trend log out of the working tree.** The log now lives at
  `.git/info/shrinkage-log.jsonl` (the git common dir), not `.claude/` inside the
  tree — so it can never block a `git checkout` during a revert, get swept into a
  commit, or show up as a dirty file. Transparent one-time migration moves any
  existing `.claude/shrinkage-log.jsonl` on first read; the status line reads the
  new location first, falling back to the old. Off-git repos still use `.claude/`.
  +2 tests.
- **P2.7 — Suite-gated mode for coverage-absent repos.** safety-model §4 now
  defines a fallback tiering for repos with no coverage artifact at all: instead
  of capping every target at T2 (which flattens the tier system), a target keeps
  its earned T0/T1 tier when the plan row names the specific suite that would
  observe a regression in it and that suite runs green before+after. No nameable
  observing suite → the row stays T2. The audit workflow declares the standing
  condition once in the plan header (not per-row noise) and records each row's
  `gate: <suite>` in the coverage column. Doc-only.
- **P2.8 — Framework gate recipes (Laravel).** `rules/frameworks/laravel.md`
  gains a "gate recipes" section mapping each file type to the cheapest
  sufficient gate, field-proven: Blade → `view:cache` + `view:clear`, routes →
  `route:list`, heavy views → a `view()->addLocation` fixture harness (not the
  controller/HTTP path, which times out), plus detecting the repo's real test
  runner (Pest vs raw phpunit) and a `config:cache`/`clear` check for config
  edits. The surgeon brief now picks gates from the rules file per file type
  instead of improvising. Doc-only.
- **P2.9 — `codemap.py scope` artifact placement.** `scope <dir>` wrote
  `.codemap-scope.txt` *inside* the scanned subtree, polluting the tree and
  leaving auditors to clean up a stray file. It now writes to the main map's
  intel dir (`.planning/intel/` or `.claude/`) as `codemap-scope-<subtree>.txt`,
  named per subtree so scopes don't collide, and gitignored. +1 test.
- **P2.10 — "Bugs found" plan section.** Audits routinely surface real defects
  that are explicitly *not* subtractions (a missing filter double-counting, a
  config key mismatch, a bug copied across N twins). The audit template now has a
  standard `## Bugs found (not shaves — fix-first, separate labeled commits)`
  section so a fix never gets folded into a `shrink:` commit and downstream
  planners have a stable place to harvest fix work. A dedupe row touching buggy
  twin code must name that bug as a blocking prerequisite (fix first, then merge).
  The lean report now surfaces the bug count. Doc-only.
- **P2.11 — Scoreboard shave-only filtering.** `diffstat.py <range> --shave-only`
  (or `--prefix shrink:,fix:`) scores only the commits in a range whose subject
  matches the shave/fix templates, so a range entangled with unrelated work (a
  feature landed mid-batch, or the WIP-sweep incident) can be scored honestly
  instead of drowning the board. It shows both totals — the isolated shave and
  the whole-range delta with the non-shave contribution called out — so
  entanglement stays visible rather than hidden. Symbol/signature analysis is
  likewise restricted to the matched commits (compat-watch no longer flags the
  user's WIP). +3 tests.
- **P2.12 — Auditor re-verify pattern (systematic carry-over).** On a re-audit,
  the audit workflow now lists the prior plan's still-open rows with `plan.py
  open` and partitions them among the matching sweeps as explicit RE-VERIFY
  items; the auditor brief re-confirms each and reports a `status:` (still-open /
  now-executable / gone / changed) — so a baseline that went red→green or a
  target that went dirty→clean is re-checked every audit instead of relying on a
  hand-written "RE-VERIFY these" list. Doc-only.

## 0.25.0
Field-report-driven hardening from a production Laravel deployment (~2,900 files
/ ~17,800 symbols, ~−5,500 app LOC banked in one day, one near-miss incident).

- **P0.1 — Staging guard (mechanical, not just prose).** New
  `scripts/safe_commit.py` stages + commits ONLY an explicitly declared file
  list (deletions included) and verifies nothing else landed; a scoped
  PreToolUse hook (`hooks/guard_staging.py`) rejects `git add -A|.|--all|-u` and
  `git commit -a|--all` while a shave is active (marker `.claude/srk-shave-active`
  the shave workflow writes/removes), leaving normal sessions untouched. Closes
  the hole where a surgeon's broad `git add` swept 220 files / +85,027 insertions
  of the user's in-flight work into a shave commit. Surgeon briefs, shave
  workflow, and safety-model §6/§7 updated; the incident is now a named
  never-list failure mode.
- **P0.2 — Dirty-target protocol (first-class).** Auditors run
  `git status --porcelain` per candidate and mark DIRTY targets; the shave now
  SKIPS dirty targets by default and reports them as blocked on the user's
  in-flight work (was improvised per-session). Opt-in `--allow-dirty-disjoint`
  uses a new `scripts/dirty_apply.py` (park/unpark) that shaves a dirty target
  only when the user's hunk is disjoint from the shave region — never entangling
  or losing it; a failed re-apply restores the byte-exact pre-shave file. +2
  tests.
- **P1.3 — Durable ledger (`.shrinkage/ledger.md`).** New `scripts/ledger.py`
  reads three sections the tool now owns instead of re-receiving them every
  session: `## frozen` (paths never edited — `safe_commit.py` hard-refuses a
  commit touching one, e.g. hash-sealed subsystems), `## excluded` (globs the
  codemap drops natively, so a stale clone can't inject phantom files or token
  cost), and `## keeps` (settled decisions the auditor won't re-flag). Audit
  injects it into every sweep; format documented in `references/ledger.md`. +3
  tests.

## 0.24.2
- Point users to auto-update — the real one-time answer to update friction.
  `/srk:update`, the update command, and the README now lead with: enable
  auto-update for the `parkktech` marketplace once (`/plugin` → Marketplaces →
  parkktech → Enable auto-update). Third-party marketplaces ship with it OFF;
  once on, Claude Code updates the plugin in the background after startup
  (prompting `/reload-plugins`) — no uninstall/install dance. The manual
  uninstall→install→relaunch path stays documented as the fallback.

## 0.24.1
- Scoreboard header names the commit count for a range: `Shrinkage · 41 commits
  · da0b0f15..HEAD` (was just `da0b0f15..HEAD`, which read like a single commit).
  A range `A..HEAD` is the NET of every commit in it — the whole sweep, not one
  commit. Working-tree scores now say `working tree (uncommitted) vs HEAD`.

## 0.24.0
- Scoreboard + trend rewritten for plain-language clarity — every number on its
  own labeled line. `/srk:score` now reads: code removed / code added / net
  change (▼ smaller) / files changed / definitions removed (functions, methods,
  classes) / definitions added / the plan breakdown as "N dead-code removals · N
  duplicate merges · N cleanups" / test code. No more cryptic "files 65 ·
  symbols 123 removed, 50 added · plan 17 removed" with no nouns. The ⚠ flags are
  plain English: "N public method signatures changed — make sure everything that
  calls them still works: <names>" and "test code shrank N lines — deleting tests
  can quietly drop coverage."
- `/srk:trend` matches the same style: net change, code removed, shave commits +
  since-date, and the by-type breakdown, one per line.
- Full-send completion no longer suggests another shave. When `--full-send`
  finishes, everything still open is by definition something autonomy must NOT
  do (targets dirty with your in-flight work, a red baseline, or a human
  adjudication). The report now frames that as completion and points to the real
  unblockers (commit/stash in-flight work → re-audit; decide the divergences)
  instead of a bare `/srk:shave <n>` that reads like it didn't finish.

## 0.23.0
- Surgeons commit by explicit file path. The shave protocol now requires
  `git commit -- <target files>` (path-limited) and forbids `git add -A` /
  `git commit -am`, with a post-commit `git show --stat` check that only the
  transform's files landed. Closes the hole where a surgeon could sweep the
  user's unrelated dirty working tree into a shave commit (it happened once:
  ~220 files / +85k lines of in-flight feature work — the final scoreboard
  caught it). Codified in safety-model §6, both surgeon briefs, and the shave
  workflow.
- Clearer, shorter `/srk:trend`: a tight 3-line lifetime block — the net app-LOC
  ratchet, removed/merged/cleaned by type, commit count + date span — with the
  noisy per-entry timestamp dump removed. It reads from git history (every shave
  commit), so the number is the real cumulative regardless of manual logging.

## 0.22.0
- Lifetime total — the real cumulative number. `/srk:trend` (and
  `diffstat.py --total`) now sums EVERY shave commit in the repo's history,
  found by the `shrink:` / `catalog:` markers from the §6 commit template, into
  one figure: total removed vs added, net app/test, a removed/merged/cleaned
  breakdown from each commit's catalog tag, and the date span. Previously the
  trend showed only changes someone had manually `/srk:score --log`'d, so a big
  multi-commit cleanup read as "just the last couple changes." The number now
  reflects all of it, no logging required. `/srk:score` stays per-change (use
  `<base>..HEAD` for a committed range); `/srk:trend` is the lifetime view.
- README: document `--full-send` (alias for `/srk:shave --auto --dangerous`).

## 0.21.1
- Fix the update trap. `/srk:update` (selfupdate.py) no longer deletes the
  plugin cache — deleting it stranded Claude Code's install *registration*,
  producing the "Plugin already installed globally" + "Failed to load
  marketplace: cache-miss" loop where `/plugin install` no-ops forever. It now
  reports the version and prints the path that actually works:
  `/plugin uninstall shrinkage@parkktech` → `/plugin install shrinkage@parkktech`
  → relaunch (uninstall clears the cached files AND the registration together).
  The update command, README, and the script's own guidance are updated to
  match; the "just rm the cache folder" advice — which caused this — is gone.

## 0.21.0
- Scoreboard rebuilt for clarity. `/srk:score` now prints a short, **colored**
  block — removed vs added lines, net app (and test, separately), files, and
  symbols as COUNTS (no more inline wall of 35 symbol names) — plus, from
  SHRINK-PLAN, a `removed · merged · cleaned` tally (catalog C-codes bucketed:
  dead code/flags → removed, dedup/consolidate → merged, simplify/de-noise →
  cleaned). The command shows it once, verbatim — no prose re-render, no
  duplicated raw line.
- Score a committed range: `diffstat.py <base>..HEAD` (e.g. a shave batch) so a
  working tree dirty with unrelated feature work can't inflate the number (the
  "+1711 of stuff I didn't touch" problem). Scoring a working tree of >15 files
  prints a one-line hint to use the range instead.
- diffstat.py now reports insertions and deletions separately (was net-only);
  `--color`/`--no-color` (auto-on for a TTY); the `/srk:trend` view is colored
  too. New tests cover the removed/added split, range scoring, and the tally.

## 0.20.2
- Fix: command references now use the colon form `/srk:shave` that Claude Code
  actually invokes. The `<next>` hints, the `/srk:help` screen, the README, the
  status line, and the scripts' printed hints had been emitting the hyphen form
  `/srk-shave`, which Claude Code rejects ("Unknown command: /srk-shave. Did you
  mean /srk:shave?") — so the skill's own suggested next steps weren't runnable.
  The commands were always `/srk:<cmd>` (the `commands/srk/` subdirectory
  namespace); only the printed labels were wrong. Now they match, so every
  suggested command is paste-runnable.

## 0.20.1
- marketplace.json: add a top-level `renames` map (`{"srk": "shrinkage"}`) so
  Claude Code auto-migrates users who still have the old `srk@parkktech` enabled
  over to `shrinkage@parkktech`, instead of throwing "Plugin srk not found in
  marketplace parkktech" on load. Requires Claude Code v2.1.193+; older versions
  ignore it (harmless). This is the official fix for the post-rename load error.
- Note: the recurring "update won't apply" is Claude Code's pinned-plugin-cache
  bug (issues #14061/#16866/#29074) — `/plugin update` and `/reload-plugins`
  don't clear `~/.claude/plugins/cache/<marketplace>`. Reliable refresh =
  delete `~/.claude/plugins/marketplaces/parkktech` + `.../cache/parkktech`,
  re-add, reinstall, then fully restart Claude Code. Documented in RELEASING.md.

## 0.20.0
- New `/srk:help` — a short, clean command reference in the order you'd use them
  (setup → understand → reduce → measure → maintain), mirroring GSD's
  `/gsd-help`. `/srk:help <command>` drills into one command; `/srk:help --full`
  adds the "when to use" notes. Humor on by default.

## 0.19.0
- Commands live under the `srk:` prefix (`/srk:map`, `/srk:shave`, `/srk:audit`,
  …). Mechanism: command files moved to `commands/srk/` and `plugin.json` sets
  `"commands": "./commands/srk/"`, so the subdirectory name `srk` — not the
  plugin name `shrinkage` — is the command namespace (the same setup gsd-core
  uses). No behavior change.
- Plugin is now `shrinkage@parkktech` (was `srk@parkktech`). BREAKING install
  change — one-time migration: `/plugin uninstall srk@parkktech`, then
  `/plugin install shrinkage@parkktech`, then relaunch. (A clean reinstall was
  already required to pick the restructured commands up past Claude Code's
  pinned plugin cache.)

## 0.18.0
- Clearer --auto halt: a drained T0/T1 backlog now reports what got done, why
  it stopped, and the continue options — never a bare "0 transforms" that
  reads like a bug.
- `/srk:shave --auto --dangerous` (alias --full-send): explicit escape hatch
  that executes T2/public-surface items too (direct removal, no deprecation
  cycle). KEEPS the free safety — atomic commit + tests-green-or-revert per
  item, hard-stop on a red/absent suite. Refused when allow_dangerous:false
  (team kill-switch). Documented in the safety model as the one opt-in
  override.

## 0.17.0
- `/srk:update` + selfupdate.py: reliable updates. Reports installed vs latest
  version and clears Claude Code's pinned plugin cache (the thing that leaves
  `/plugin update` silently no-opping after a version bump or force-push),
  then prints the exact reinstall lines. Answers the recurring "update shows
  available but won't apply."

## 0.16.0
- Output discipline (anti context-rot): SKILL.md rule that the agent reports
  one result line, never reprints diffs/maps/evidence, keeps records on disk
  (gate ledger, SHRINK-PLAN.md) and references them; audit reports counts+top-3
  not the full table; subagents return structured results only; codemap query
  output capped (narrow-the-term hint) so a broad match can't flood context.
- --auto no longer needs a manual /clear: each backlog item runs in a fresh
  srk-surgeon subagent, so the main context stays flat and a long backlog
  completes in one session. Manual /clear is now optional (fresh-batch
  convenience); auto-compaction + the PreCompact breadcrumb cover the rest.
  auto_max_items default 0 (run to completion); auto_context_stop is a
  fallback, not the normal stop.

## 0.15.0
- Context monitoring & clearing for long runs. `/srk:shave --auto` is now
  context-durable: state lives in git + SHRINK-PLAN.md (not the conversation),
  it checkpoints after every item, and stops at `auto_max_items` (default 8)
  or `auto_context_stop`% context (default 75) with a clear-and-resume prompt.
  Re-running --auto after /clear continues from open plan items. New
  progress.py + a PreCompact hook write a resume breadcrumb so even automatic
  compaction knows where to continue. references/context-management.md.

## 0.14.0
- /srk:shave gains `--auto` (alias `all`): work the whole SHRINK-PLAN backlog
  top-to-bottom, one gated commit per item, halting on the first T2/public-
  surface item, first red gate, or empty plan. Single-item shaves now always
  prompt for the next item (name + tier + est LOC) so you can step through.
  Answers 'why doesn't shave do the whole project?' — it can now, safely.

## 0.13.0
- Session-start line now shows plan STATS when a SHRINK-PLAN.md exists:
  open-item count, tier mix (T0xN T1xN...), and headline '~N LOC to reclaim'
  (from an est-savings stamp the audit writes). Done-section rows excluded.

## 0.12.1
- Fix: session-start hook was doing a full file-tree fingerprint walk on
  every launch, timing out (and printing nothing) on large repos. The hook is
  now instant — reads the status line from the cached map header, builds only
  when the map is absent; staleness refresh stays at task time. Plan-staleness
  compares the plan's stamped fp to the map's fp (no walk).

## 0.12.0
- Always-on session-start status line (default): `[shrinkage] active · N
  symbols · <next step>`. Adapts to audit state — prompts to run /srk:audit
  when none exists, shows open SHRINK-PLAN.md items, or flags a stale plan
  when code moved on. Silence with quiet_startup. Audit stamps map-fp; shave
  updates the plan so it stays current.

## 0.11.0
- Kotlin parser + Android support (manifest/layout/gradle/ProGuard indexed
  reference-only; Jetpack seams in rules/frameworks/android.md)

## 0.10.0
- Template support: .phtml/Blade via PHP adapter, Twig blocks+macros,
  Vue/Svelte/Astro via JS adapter; reference-only indexing for
  Handlebars/EJS/Jinja/Smarty/Latte/ERB/Liquid + framework XML/YAML config

## 0.9.0
- Composer platform map (vendor classmap search), framework detection + rules
  for Laravel / Magento 2 / Drupal; zero-init SessionStart hook; statusline

## 0.8.0
- Gate ledger (gatelog.py + diffstat cross-check), compat-watch (signature
  changes), shave --dry-run, DEPRECATIONS.md ledger, shrink badge, coverage-
  joined audits; 5 bug fixes (deletion-aware refresh, rename-safe diffstat,
  comment-stripped refcounts, api-map merge, string-safe braces); pytest
  suite + CI; context trims (lite gate, rules-once, script-only score)

## 0.7.0
- Economy mode (Haiku surgeon / capable auditor+verifier), README rewrite,
  scoreboard doc/config exclusion fix, Copilot adapter refresh

## 0.6.x
- Plugin + self-hosted marketplace (/srk: namespace), GSD-style terse output

## 0.5.0
- Initial full skill: codemap (7 languages), safety model, consolidation
  catalog, workflows, agent briefs, GSD integration, Copilot adapter, evals
