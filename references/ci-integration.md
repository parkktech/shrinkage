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

## Scheduled weekly audit

Keep SHRINK-PLAN.md standing and fresh instead of auditing ad hoc.

**Option A — Claude scheduled task (Cowork / Claude desktop):** create a
scheduled task with a prompt like: *"In repo <path/URL>: run the shrinkage
audit workflow (skill: shrinkage, command /srk-audit). Refresh SHRINK-PLAN.md,
compare against last week's plan, and summarize: new candidates, candidates
executed since last week, cumulative trend (`/srk-trend`)."* Weekly cadence;
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
            Run /srk-audit for this repo. Update SHRINK-PLAN.md and open a PR
            with the refreshed plan if it changed. Do not execute any
            transforms — audit only.
```

(Adjust the action's inputs to the version you use; the contract is simply
"run the audit prompt on a schedule and PR the plan.")

**Option C — cheap mechanical pre-pass, no LLM:** a cron job that runs
`codemap.py build`, `codemap.py dupes`, and `codemap.py clones` and commits
the raw output to `.claude/audit-signals/` — the next human-triggered
`/srk-audit` starts from fresh signals without spending agent time on sweeps.

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

Monthly (or per retro): `/srk-trend`. Cumulative app LOC should trend down or
flat-with-features; a sustained climb means gates are being skipped — fix the
habit, not the hook.
