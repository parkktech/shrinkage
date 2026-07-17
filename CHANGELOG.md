# Changelog

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
