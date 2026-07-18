# Changelog

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
