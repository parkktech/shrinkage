---
name: shrinkage
description: Write less, better code by extending what exists instead of adding new code — and safely remove code the repo no longer needs — guided by a token-lean symbol map. Use this skill whenever writing, modifying, refactoring, planning, reviewing, or cleaning up code in an existing codebase — adding a feature, fixing a bug, implementing an endpoint, extending a class, planning a GSD phase, hunting dead code or duplication, or any task that will produce a diff. Also use for any /srk:* or srk command, or when the user mentions shrinkage, reducing code, code cleanup, dead code, duplication, keeping diffs small, backwards compatibility during refactors, code maps, codebase intelligence, or token-efficient exploration. Not needed for brand-new empty projects or single-file throwaway scripts.
---

# Shrinkage

> "It shrinks?" — yes, and that's the point.

The measure of a change is the goal achieved with the least code — not the
code produced. Shrinkage attacks codebase weight from both ends: the **gate**
stops unjustified new code at the door, and the **shave/audit** loop reclaims
what's already there — all under two absolutes: **backwards compatibility is
never sacrificed** (the Zeroth Law) and **behavior is provably preserved**
(the safety model). Net-negative diffs are the high score.

## Core loop (every coding task)

1. **Map** — `python3 <skill>/scripts/codemap.py refresh` (builds on first
   run; asks the user once whether to commit or gitignore the map — default
   gitignored). Load the `rules/<lang>.md` files it names.
   → detail: `workflows/map.md`
2. **Orient** — read the map, not the repo. `codemap.py query <term>`
   (`--deep` to expand), `scope <dir>` for monorepo subtrees.
3. **Gate** — size it first: small low-risk change (or near-empty map) → the
   lite path (one query, name the owner, record, go); otherwise list 2–5
   candidate symbols to extend, extend-or-justify each, walk the extension
   ladder; rungs 7–8 (new file/module) need justification — and user
   confirmation when `gate: "hard"`. Either path, persist the record:
   `gatelog.py add` — the scoreboard cross-checks it. → `workflows/gate.md`
4. **Implement** — smallest diff, plus a subtraction pass in every touched
   file. Deletions follow the safety model — no exceptions for drive-bys.
5. **Score** — `python3 <skill>/scripts/diffstat.py` and report its line (app
   and test LOC counted separately). `--pr` for the PR block, `--log` for the
   trend log. → detail: `workflows/score.md`
6. **Re-map** — run `codemap.py refresh` again after implementing: your new
   methods, classes, and parameters fold into the map (and GSD's
   api-map.json) immediately, so the next task — or the next fresh-context
   subagent — orients against reality, not a stale snapshot. Optional
   editor hook for continuous refresh: `references/ci-integration.md`.

## The Extension Ladder

Stop at the first rung that achieves the goal; every lower rung needs a
one-line justification for why the higher rungs were insufficient:
(1) value/config → (2) parameter with a safe default → (3) extend a method →
(4) method on existing class → (5) function in existing module → (6) class in
existing file → (7) new file → (8) new module. Rung 2's "safe default" is the
Zeroth Law in miniature: existing call sites keep their behavior, always.

## The Zeroth Law and the Safety Model

**Backwards compatibility outranks every reduction goal.** The compatibility
surface (public symbols, endpoints, CLI flags, config keys, wire formats,
schemas, events) only changes additively; removals go through the deprecation
cycle; renames leave delegating shims. **Deletions require an evidence
chain** — map refs, repo-wide grep, the language's dynamic-reference
checklist, test evidence, git history — and execute one-transform-per-commit
with green gates. Read `references/safety-model.md` before ANY shave, audit
execution, or deletion. Every reduction names its entry in
`references/consolidation-catalog.md` (C1–C10).

## Anti-Speculation Rules

No interface/ABC with a single implementer; no config for a value that never
varied; no wrapper that only delegates (deprecation shims exempt — labeled and
scheduled); no `utils` growth when the logic has a home. Add the abstraction
when the second concrete case arrives.

## Subagents & economy mode

Three roles, deliberately tiered by model to keep cost down — the expensive
model decides *what and how*, the cheap model does the mechanical work:

- **srk-auditor** (`model: inherit` — capable model) — finds and evidences
  reduction candidates. Read-only. Judging what's truly removable is the hard
  part, so it runs on the session's model.
- **srk-surgeon** (`model: haiku` — cheap/fast) — executes exactly ONE
  already-decided catalog transform, revert-on-red. The "what/how" is settled;
  this is mechanical lift-and-shift, and the test gate (not the model) is what
  guarantees safety.
- **srk-verifier** (`model: inherit`) — adversarial, tries to prove the change
  broke something. A missed break costs more than the tokens.

That's the default **economy tiering**: the flagship model finds and verifies,
Haiku shifts. To run everything on the flagship (max quality, higher cost) set
the surgeon's `model:` to `inherit` in `agents/srk:surgeon.md`; to push economy
further, drop the auditor's sweeps to a mid model too. The full role protocols
live in `agents/shrink-{auditor,surgeon,verifier}.md`. The audit workflow fans
out auditors; every surgeon commit on T1+ work deserves a verifier pass.

## Composer / framework projects (Laravel, Magento 2, Drupal, ...)

When `composer.json` exists, the map build detects the framework and names the
`rules/frameworks/<fw>.md` file to read alongside the language rules. The
**platform sweep** is mandatory at the gate: `codemap.py vendor <term>`
searches Composer's prebuilt classmap (vendor/composer/autoload_classmap.php —
zero parsing, works at Magento scale) so the framework's existing classes are
candidates before any new code. Framework rules map the ladder onto sanctioned
seams — Laravel macros/listeners/FormRequests, Magento plugins/observers/view
models (preferences last), Drupal alter hooks/decorators/plugins — and extend
the dynamic-reference checklists with each framework's string-reference graph
(di.xml, services.yml, routes, generated factories, hooks), which is what
makes deletion safe there.

## Zero-init

The plugin ships a SessionStart hook that runs `codemap.py refresh --auto` —
the map builds/refreshes itself the moment a session opens in any git repo
with supported code (silent no-op elsewhere). Installing the plugin IS the
setup; the skill auto-triggers on coding tasks from that point. Every session
prints one compact status line so shrinkage's state is always visible:
`[shrinkage] active · N symbols · <next step>` — where the next step adapts:
"no audit yet — run /srk:audit" when no SHRINK-PLAN.md exists, the open-item
count when it does, or "SHRINK-PLAN.md is stale — /srk:audit to refresh" once
code has moved past the last audit. Silence it with `"quiet_startup": true`.
`/srk:onboard` is optional — preferences only.

## GSD integration

In a GSD project (`.planning/` present) everything auto-connects: the map
lives at `.planning/intel/codemap.txt` and syncs all parsed symbols into
`.planning/intel/api-map.json` (upgrading GSD's intel grounding and
API-SURFACE.md to every language here, not just JS); planners run the gate
(rules files have "When planning" sections); executors follow the ladder and
put the scoreboard line in SUMMARY.md; verifiers use the rules' "When
verifying" sections; audits write SHRINK-PLAN.md into `.planning/` for phase
planning. GSD's project-skills discovery loads `rules/*.md` automatically.

## Commands

Installed automatically with the plugin (`/plugin marketplace add
parkktech/shrinkage` → `/plugin install shrinkage@parkktech`); standalone users can
instead copy the `commands/srk/` folder into `.claude/commands/`:

| Command | Does | Workflow |
|---|---|---|
| `/srk:onboard` | one-shot setup: map + all preferences | — |
| `/srk:map` | build/refresh map, detect languages | workflows/map.md |
| `/srk:query <term>` | find symbols at map cost | workflows/map.md |
| `/srk:gate <task>` | reuse gate before writing code | workflows/gate.md |
| `/srk:score [--pr] [--log]` | the scoreboard | workflows/score.md |
| `/srk:trend` | cumulative weight + shrink streak | workflows/score.md |
| `/srk:shave [target]` | safe subtraction pass | workflows/shave.md |
| `/srk:audit [dir]` | ranked shrink backlog → SHRINK-PLAN.md | workflows/audit.md |
| `/srk:config` | all settings, comedy included | — |
| `/srk:update` | check version + clear stale plugin cache for a clean update | — |
| `/srk:help [command]` | usage guide, in workflow order | — |

Extra signals for shave/audit: `codemap.py dupes` (same-name symbols),
`codemap.py clones` (renamed copy-paste via normalized shingles), and
`coverage_check.py <files>` (coverage-aware tier escalation). Bookkeeping:
`gatelog.py` (persistent gate ledger — diffstat flags new symbols with no
record), `badge.py` (shrink badge SVG from the trend log), DEPRECATIONS.md
(shim removal schedule — trend nags on unchecked entries). `/srk:shave`
accepts `--dry-run`: full plan with evidence, zero edits.

Context economy: load `rules/<lang>.md` once per session; the gate never loads
`safety-model.md` (that's deletion reading); score is script-only — run
diffstat, echo verbatim.

Long runs: `/srk:shave --auto` is context-durable — state lives in git +
SHRINK-PLAN.md, not the conversation, so it checkpoints per item and survives
a `/clear`. It stops at `auto_max_items` (default 8) or when context fills
(`auto_context_stop`%, default 75); resume by re-running it. Detail:
`references/context-management.md`. A PreCompact hook writes a resume
breadcrumb so even auto-compaction knows where to continue.

CI/hook integration (pre-commit scoreboard, PR comment action):
`references/ci-integration.md`.

## Settings

`.claude/shrinkage.json`, all optional:

```json
{"gate": "soft", "commit_map": false, "pr_scoreboard": false, "budget": 4000, "humor": true}
```

`gate: "hard"` = confirm with the user before new files/modules.
`commit_map: true` = team-shared map instead of auto-gitignored.

## Response style

Keep it tight, GSD-style. Every command ends with a short result line and a
**Next** block — never a wall of prose. The result is a fact or two; the
reasoning stays in the workflow files, not the reply.

**Lead the Next block with the ONE clearest thing to do now, as a plain
imperative the user can act on without decoding it — and that action is often
NOT a `/srk:` command.** When the remaining work is blocked on the user — commit
or stash in-flight work, land a branch, adjudicate a ⚖ decision, fix a flagged
bug — say it first and plainly ("Commit or stash your branch work, then
`/srk:shave 5`"). Never bury the action in a menu or a condition the user has to
resolve: "row 5 becomes executable after…" leaves them guessing. Phrase a future
step as an explicit condition → action ("When your branch lands, run
`/srk:audit`"), never a vague noun ("the natural next sweep"). If the ball is in
the user's court and no `/srk:` command is the move, say exactly that ("Nothing
to shave until your branch lands — go finish it, then `/srk:audit`") instead of
offering a command to fill the slot. Then at most 1–2 real alternatives.
Default shape:

```
<result line — the fact, e.g. "Map built: 17,682 symbols across 6 languages.">
<the script's quip verbatim, if humor is on>

Next:
• <the one concrete action, imperative — e.g. "Commit your WIP, then /srk:shave 5">
• <at most one or two real alternatives — /srk:audit, /srk:trend, …>
```

Pick actions that actually fit the situation (see each command's "Next" list) —
and when the honest next move is a human step, say it, don't pad the slot with a
`/srk:` command. Explain more only when the user asks why, or when a safety
decision (a T2 escalation, a red gate) genuinely needs it. One light joke max,
information first; `humor: false` → play it straight.

## Output discipline (anti context-rot)

Verbose output is what rots a long session — every reprinted diff and pasted
evidence chain is dead weight in the window. Keep the conversation lean:

- **Don't reprint what a tool already showed.** After running a script, report
  its one result line — never paste the diff, the file, the full map, or the
  command's raw dump back into the reply.
- **State lives on disk, references live in chat.** Gate records go to the gate
  ledger, evidence chains and findings go to SHRINK-PLAN.md, deprecations to
  DEPRECATIONS.md — say "recorded in SHRINK-PLAN.md (6 items)", don't inline
  the table. The reader opens the file if they want detail.
- **Subagents return the structured result only** — `done: <item> | <netLOC> |
  <sha>` or a findings object — not their working transcript. That's the whole
  reason per-item work is offloaded; don't let it leak back as prose.
- **`--auto` = one line per item**, then a final tally. Not a play-by-play.
- **Audit reports counts + top few**, and points at the plan file for the rest.
- **No tool-call narration** ("Now I'll run…", "Let me check…"). Just do it and
  give the result. Prefer a compact table/line over paragraphs.

Scripts follow the same rule: compact by default, detail behind `--deep`/
`--verbose`. If you're about to emit a long block, ask whether it belongs in a
file instead.

## Tone

The scripts crack one joke per run. Relay their quip verbatim — it's the
brand. Celebrate net-negative; tease growth gently, never scold.

## Languages and parser precision

Supported now: Python, JavaScript/TypeScript, PHP, Go, Rust, Java, C#, Kotlin
(+ Android: manifest/layout/nav XML, gradle scripts, and ProGuard keep rules
indexed reference-only; `rules/frameworks/android.md` for the Jetpack seams),
plus
templates — Blade/.phtml (via the PHP adapter), Twig (blocks + macros mapped,
`rules/twig.md`), Vue/Svelte/Astro (via the JS adapter). Reference-only
indexing covers Handlebars/EJS/Jinja/Smarty/Latte/ERB/Liquid templates and
framework config (Magento XML, services/routing YAML): they define no map
symbols but their usage COUNTS as references, so template-only or config-only
usage can't make a symbol look dead. Each language has a parser adapter AND a
`rules/<lang>.md`. Parsing is exact where cheap
(Python via stdlib ast; JS/TS/PHP upgrade automatically to tree-sitter when
`pip install tree-sitter tree-sitter-javascript tree-sitter-typescript
tree-sitter-php` is present) and regex-based otherwise — same map either way.
Growing further is two files, no core changes: `scripts/parsers/<lang>.py`
(brace languages reuse `parsers.scan_braced`) registered in `EXTENSIONS`,
plus `rules/<lang>.md` from `rules/_template.md` — the dynamic-reference
checklist section is mandatory; it's what makes deletion safe in that
ecosystem.

## Other runtimes

This skill follows the open Agent Skills standard (SKILL.md + bundled
scripts/references), so it loads natively in runtimes beyond Claude Code —
GitHub Copilot (cloud agent, code review, CLI, VS Code/JetBrains agent mode)
discovers it from `.claude/skills/`, `.github/skills/`, or `~/.copilot/skills/`.
`adapters/copilot/` has the install guide plus optional IDE prompt files and an
instructions-file fallback. When running OUTSIDE Claude Code, adapt like this:

- **$SKILL is this folder.** Resolve every `scripts/`, `rules/`, `references/`,
  `workflows/` path relative to the directory holding this SKILL.md.
- **No `/srk:*` commands** — follow the workflow files directly (`workflows/
  shave.md`, `workflows/audit.md`, …); they are the commands' full content.
- **No PreToolUse staging-guard hook.** The hook that blocks `git add -A`
  during a shave is Claude-Code-only — so committing through
  `scripts/safe_commit.py -m "<msg>" -- <files>` is MANDATORY discipline here,
  not belt-and-suspenders. Same for the dirty-target flow: park → precheck →
  safe_commit → unpark via `scripts/dirty_apply.py`, never hand-staged.
- **No subagents** — run the `agents/` briefs (auditor / surgeon / verifier)
  inline as your own checklist, one at a time.
- **No statusline/session hooks** — open each session with `codemap.py refresh`
  yourself; everything else (ledger, plan CLI, scoreboard, trend) is plain
  Python and works unchanged.

## File index

- `workflows/` — map, gate, shave, audit, score: full processes with success criteria
- `agents/` — auditor / surgeon / verifier subagent briefs
- `references/safety-model.md` — Zeroth Law, tiers, evidence chain, protocol
- `references/consolidation-catalog.md` — C1–C10 transforms with gotchas
- `references/map-format.md` — map spec, query syntax, parser guide
- `references/extend-vs-add.md` — worked ladder decisions
- `rules/*.md` — per-language idioms + dynamic-reference checklists
- `ARCHITECTURE.md` — system design, data flow, roadmap
