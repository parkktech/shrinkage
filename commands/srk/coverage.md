---
name: srk:coverage
description: "Upgrade tiering: generate the repo's first coverage artifact (suite-gated → coverage-aware)"
argument-hint: "[--run]"
allowed-tools: [Bash]
---

<execution_context>
$SKILL is resolved FRESH for THIS invocation — never reuse a path remembered from earlier in the session (a mid-session plugin update strands version-pinned cache paths). Churn-proof order: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` if set; else the newest installed copy `$(ls -dv ~/.claude/plugins/cache/*/shrinkage/*/skills/shrinkage 2>/dev/null | tail -1)`; else the vendored locations.

Run `python3 $SKILL/scripts/coverage_check.py bootstrap` — it detects this
repo's test ecosystem (pest/phpunit incl. the pcov/xdebug driver check, pytest,
vitest/jest, go, cargo) and prints the exact coverage command + where the
artifact lands. Show the user that plan and CONFIRM before `--run` (it executes
the entire test suite — minutes, and for live-API suites, money). After the
artifact exists, say the payoff plainly: the next `/srk:audit` upgrades every
row from suite-gated (named observing suites) to real coverage-aware tiering
(safety-model §4) — deletion targets earn T1 by measured coverage instead of
by hand-named gates.
</execution_context>

<success_criteria>
- [ ] Detected command shown with driver caveats before anything runs
- [ ] --run only with user confirmation; artifact verified found afterward
- [ ] Next step stated: /srk:audit re-tiers on real coverage
</success_criteria>

<next>
Next:
• artifact generated → /srk:audit (rows upgrade to coverage-aware tiering)
• driver missing → install it (pcov / pytest-cov / @vitest/coverage-v8), rerun
</next>
