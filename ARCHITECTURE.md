# Shrinkage — Architecture

How the system achieves its two promises — **maximum safe code reduction** and
**minimum token cost** — and why it's built the way it is.

## 1. The thesis

Codebases grow because adding is locally cheaper than finding. For an AI agent
the imbalance is worse: discovering existing code costs context-window tokens,
so the economically "rational" move is to write new code — which is exactly
wrong for the codebase. Shrinkage inverts the economics with three mechanisms:

1. **The codemap** makes discovery nearly free (~4k tokens replaces 15–40k of
   exploration), so reuse becomes the cheap path.
2. **The doctrine** (ladder + gate + anti-speculation) makes new code carry a
   justification cost, so growth needs a reason.
3. **The scoreboard** makes the outcome measurable per change and over time,
   so the incentive sticks.

Reduction of *existing* weight is then handled by a separate, safety-governed
loop (audit → shave → verify), because removing code is a fundamentally more
dangerous act than not adding it.

## 2. System map

```
                 ┌────────────────────────────────────────────────┐
                 │                  doctrine layer                 │
                 │  SKILL.md · workflows/{map,gate,shave,audit,    │
                 │  score}.md · rules/<lang>.md · references/      │
                 └────────────┬───────────────────┬────────────────┘
                              │ instructs         │ instructs
                 ┌────────────▼─────────┐  ┌──────▼────────────────┐
                 │   main agent /       │  │  subagents            │
                 │   GSD planner/exec   │  │  auditor·surgeon·     │
                 └────────────┬─────────┘  │  verifier             │
                              │ runs       └──────┬────────────────┘
                 ┌────────────▼───────────────────▼────────────────┐
                 │                 mechanical layer                 │
                 │  codemap.py (build/refresh/query/scope/dupes/    │
                 │  langs) · diffstat.py (score/pr/log) ·           │
                 │  settings.py · parsers/ registry                 │
                 └────────────┬───────────────────┬────────────────┘
                              │ writes            │ syncs
                    .claude/codemap.txt   .planning/intel/api-map.json
                    .claude/shrinkage.json         (GSD intel)
                    .claude/shrinkage-log.jsonl
```

Scripts do everything deterministic (parsing, counting, ranking, diffing) for
zero tokens; the model spends tokens only on judgment — which candidate, which
rung, whether evidence suffices.

## 3. The codemap

**Format** (spec: `references/map-format.md`): line-based, one file-path line
per group, `c/i/m/f` symbols with `@line` and `xRefs`. Deliberately not JSON —
the same data in JSON costs ~2× the tokens, and the map's entire reason to
exist is token thrift.

**Reference counting:** one identifier-tokenization pass over all sources into
a Counter, `refs = count(name) − 1`. O(total tokens), no per-symbol scans.
It's a *ranking signal*, deliberately cheap — the safety model (§4 below)
never lets it be treated as proof.

**Budgeting:** when the map exceeds the token budget, whole low-signal files
collapse to path-only lines (rank = best symbol ref count per file), keeping
high-traffic symbols visible. `query --deep` and `scope` recover detail on
demand. This mirrors how a senior engineer holds a codebase: hot paths by
heart, cold paths by index.

**Parsers:** a registry (`parsers/__init__.py::EXTENSIONS`) maps extensions to
adapter modules exposing `parse(text) -> list[Symbol]`. Python uses stdlib
`ast` (exact); JS/TS and PHP use regexes over a shared brace scanner
(`scan_braced`) — imprecise by design, adequate for mapping, and each adapter
can upgrade to tree-sitter behind the same interface without touching core.
Adding a language = adapter + rules file; detection, ranking, dupes, diffstat,
and GSD sync inherit it.

## 4. The safety architecture

Two documents carry the entire risk story:

- `references/safety-model.md` — the Zeroth Law (backwards compatibility
  outranks reduction), risk tiers T0–T3 with autonomy limits, the five-link
  evidence chain for deletions, test gates, the deprecation cycle for
  unprovables, the one-transform-per-commit protocol, and the never-list.
- `references/consolidation-catalog.md` — C1–C10, every reduction transform
  the system is allowed to perform, each with detection signal, tier, and
  known gotchas.

The design principle: **every removal is (a) named — a catalog entry, (b)
tiered — an autonomy level, (c) evidenced — a written chain, (d) atomic — one
commit, revertible.** The gotcha lists exist because verification must be
targeted: the verifier checks the known failure modes of the specific
transform, not "looks good to me."

Roles separate cleanly: the **auditor** may only read and evidence; the
**surgeon** may only execute one named transform and must revert on red; the
**verifier** is adversarial and re-derives evidence independently. The same
separation applies when one agent plays all three roles sequentially — the
briefs define the hats, not necessarily different processes.

## 5. Token economics

| Activity | Without shrinkage | With |
|---|---|---|
| Orienting in a ~200-file repo | 15k–40k tokens (greps + file reads) | ~4k map + 1–2 targeted reads |
| Building the map | — | 0 tokens (script) |
| Finding duplicates | ad-hoc, usually skipped | 0 tokens (`dupes`) |
| Scoring a change | manual, usually skipped | 0 tokens (`diffstat`) |
| Fresh-context subagents (GSD) | full re-exploration EACH | map read each |

The multiplier case is GSD: every executor/planner/verifier subagent starts
with an empty context, so map-instead-of-exploration pays per agent, per
phase, per milestone.

## 6. GSD integration contract

- Map path: `.planning/intel/codemap.txt` when `.planning/` exists.
- Intel sync: `build`/`refresh` upsert `.planning/intel/api-map.json`
  (`entries: {Symbol: {file, kind, signature, line, refs, language}}`,
  `_meta.generator: "shrinkage/codemap.py"`) — GSD's documented loose schema,
  feeding `plan_review.source_grounding_authority: intel` and API-SURFACE.md.
- Discovery: GSD agents load project skills' `SKILL.md` + `rules/*.md` on
  their own (project-skills-discovery); SKILL.md stays lean for that reason.
- Artifacts: audits write SHRINK-PLAN.md into `.planning/`; scoreboard lines
  go into plan SUMMARY.md; verify phases consume the rules' "When verifying"
  sections.

## 7. On "reduce by 100%"

The honest version of the goal: **the ratchet only moves down.** The gate
bounds growth to justified growth; the audit/shave loop converts existing
weight into evidence-backed removals; the deprecation cycle converts
"unprovably dead" into "measured dead"; the trend log proves the direction
over time. Typical mature codebases carry 10–30% removable weight — the skill
will find and take everything the evidence chain supports, and *decline* the
rest, because the Zeroth Law and a green test suite outrank any percentage.

## 8. Roadmap

Shipped in 0.5: tree-sitter precision for JS/TS/PHP (feature-detected, regex
fallback — `ts_engine.py`); coverage-aware tiers (`coverage_check.py`, lcov/
Cobertura/Clover/coverage.py); clone detection via normalized line-shingles
(`codemap.py clones`); Go/Rust/Java/C# adapters + rules; eval fixtures with
planted traps (`evals/`); plugin packaging; Copilot adapter
(`adapters/copilot/`); scheduled-audit patterns (ci-integration.md).

Next:

- **Run the eval loop** — with-skill vs baseline on the trap fixtures,
  measuring net LOC, tokens, and correctness; iterate the doctrine on what
  fails. The fixtures and assertions are ready; this is execution.
- **Docstring capture** behind a build flag (better candidate selection,
  ~2× map size).
- **Kotlin/Swift/Ruby adapters**; tree-sitter grammars for Go/Rust/Java/C#.
- **npm installer** for multi-runtime distribution (Cursor/Codex layouts),
  GSD-style, when demand exists.
- **Coverage-gated surgeon** — surgeon refuses T1 execution without a
  coverage report, configurable.
