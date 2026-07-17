# Changelog

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
