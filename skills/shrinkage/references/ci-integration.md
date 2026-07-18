# CI / Hooks Integration

Make the scoreboard part of the team's routine, not just the agent's. Copy
what fits; every snippet assumes the skill lives at `.claude/skills/shrinkage`.

## Git pre-commit hook — see the score before every commit

`.git/hooks/pre-commit` (or a pre-commit-framework local hook):

```bash
#!/bin/sh
# Shrinkage scoreboard — informational, never blocks.
python .claude/skills/shrinkage/scripts/diffstat.py --log || true
```

Logs every commit into the trend (`.claude/shrinkage-log.jsonl`) and prints
the line where the committer sees it. Deliberately non-blocking: the
scoreboard is a compass, not a quota (safety-model §7) — blocking commits on
LOC invites gaming the metric.

## GitHub Action — scoreboard comment on every PR

`.github/workflows/shrinkage.yml`:

```yaml
name: srk-score
on: [pull_request]
permissions:
  pull-requests: write
jobs:
  score:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Score the PR
        run: |
          python .claude/skills/shrinkage/scripts/diffstat.py \
            origin/${{ github.base_ref }} --pr | tee score.txt
      - name: Comment scoreboard
        uses: marocchino/sticky-pull-request-comment@v2
        with:
          header: shrinkage
          path: score.txt
```

One sticky comment per PR, updated on each push: net app/test LOC, files,
new/removed symbols. Reviewers see growth claims next to the diff that makes
them.

## Optional: budget alarm (still not a blocker)

A soft alarm step after scoring, for teams that want a nudge threshold:

```bash
NET=$(python .claude/skills/shrinkage/scripts/diffstat.py origin/main | grep -oP 'app \+?\K-?\d+')
[ "$NET" -gt 300 ] && echo "::warning::+${NET} app LOC — was every line gate-justified?"
```

Keep it a warning. The moment the number becomes a gate, people optimize the
number instead of the codebase — splitting PRs, deleting tests, gaming
whitespace. The gate for growth is the reuse gate, enforced in review by the
justifications the scoreboard makes visible.

## T0 auto-PR bot (the safest automation)

Tier-0 removals — commented-out code blocks, dead imports, stale TODOs, noise
(catalog C10) — are mechanical enough to automate end-to-end. A weekly action
that audits and opens a PR containing ONLY T0 items gives recurring cleanup
with human review as the gate:

```yaml
name: srk-t0-bot
on:
  schedule:
    - cron: "0 7 * * 1"
  workflow_dispatch: {}
jobs:
  t0:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Run the shrinkage audit (skill: shrinkage). Then execute ONLY
            tier-T0, catalog-C10 removals (commented-out code, dead imports,
            stale TODOs) — nothing T1 or above, no symbol deletions. One
            commit per file group, tests green after each. Open a PR titled
            "shrink: T0 noise sweep" with the diffstat scoreboard in the body.
            If nothing qualifies, exit without a PR.
```

The PR review is the human gate; the tier restriction is what makes unattended
execution safe.

## Shrink badge

Make the metric visible in the README:

```bash
python3 <skill>/scripts/badge.py --out .claude/shrinkage-badge.svg
```

reads the trend log and writes a badge with the cumulative app-LOC delta
(green when negative). Commit it and embed:
`![shrinkage](.claude/shrinkage-badge.svg)`. Regenerate in the same hook/CI
step that runs `diffstat.py --log`.

## Scheduled weekly audit

Keep SHRINK-PLAN.md standing and fresh instead of auditing ad hoc.

**Option A — Claude scheduled task (Cowork / Claude desktop):** create a
scheduled task with a prompt like: *"In repo <path/URL>: run the shrinkage
audit workflow (skill: shrinkage, command /srk:audit). Refresh SHRINK-PLAN.md,
compare against last week's plan, and summarize: new candidates, candidates
executed since last week, cumulative trend (`/srk:trend`)."* Weekly cadence;
the summary lands wherever your scheduled tasks report.

**Option B — GitHub Action cron + Claude Code:**

```yaml
name: srk-weekly-audit
on:
  schedule:
    - cron: "0 6 * * 1"   # Mondays 06:00 UTC
  workflow_dispatch: {}
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Run /srk:audit for this repo. Update SHRINK-PLAN.md and open a PR
            with the refreshed plan if it changed. Do not execute any
            transforms — audit only.
```

(Adjust the action's inputs to the version you use; the contract is simply
"run the audit prompt on a schedule and PR the plan.")

**Option C — cheap mechanical pre-pass, no LLM:** a cron job that runs
`codemap.py build`, `codemap.py dupes`, and `codemap.py clones` and commits
the raw output to `.claude/audit-signals/` — the next human-triggered
`/srk:audit` starts from fresh signals without spending agent time on sweeps.

## Keeping the map continuously fresh (editor hook)

The map self-heals at every task start (`refresh` rebuilds when any source is
newer) and after implementation (core-loop step 6). For continuous freshness —
every new method, class, or parameter folded in the moment it's written — add
a Claude Code PostToolUse hook in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/skills/shrinkage/scripts/codemap.py refresh --quiet >/dev/null 2>&1 || true"
          }
        ]
      }
    ]
  }
}
```

Notes: `refresh` is a no-op when the map is current, and a rebuild is a fast
parse-only pass — fine for small/medium repos. On very large repos prefer the
default task-start/task-end refresh cadence, or scope the hook to the subtree
you work in (`--root <dir>`). GSD projects get the same effect for free at
phase boundaries: executors re-run the core loop, so the map and api-map.json
are refreshed around every plan.

## Trend review ritual

Monthly (or per retro): `/srk:trend`. Cumulative app LOC should trend down or
flat-with-features; a sustained climb means gates are being skipped — fix the
habit, not the hook.

## Status line

Show shrinkage state under the input box: point Claude Code's status line at
`scripts/statusline.py` (run `/statusline` and ask for it, or set
`statusLine.command` in settings). It shows `srk: run /srk:onboard ...` before
first use, the mapped-tip once the codemap exists, and `srk ▼-123 LOC ·
streak N` once you're scoring with `--log`.

## The growth gate (pre-push / CI) — dead code caught the week it's born

The audit catches accumulated weight; the growth gate stops NEW weight at the
seam where it actually arrives — the push. `diffstat.py <range> --ci-gate`
runs the diff-sized checks: net app growth, public signature changes
(compat-watch), unjustified new symbols (gatelog cross-check), and dupe-shaped
new symbols (a name that already lives elsewhere in the map — C1/C9 being
born). Warn-only by default; `--strict` exits 1 on warnings for blocking CI.

Pre-push hook (`.git/hooks/pre-push`, chmod +x):

```sh
#!/bin/sh
SKILL=$(ls -dv ~/.claude/plugins/cache/*/shrinkage/*/skills/shrinkage 2>/dev/null | tail -1)
[ -n "$SKILL" ] || exit 0
python3 "$SKILL/scripts/diffstat.py" "origin/$(git rev-parse --abbrev-ref HEAD)..HEAD" --ci-gate
# add --strict to block the push on warnings
```

GitHub Actions: copy `ci/growth-gate.yml` into `.github/workflows/`.
