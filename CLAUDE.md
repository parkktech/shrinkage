# Working on the Shrinkage repo (instructions for AI agents)

This repo IS the `srk` plugin (Shrinkage). It's installed via its own
self-hosted marketplace, so **shipping a change means bumping the version,
tagging it, and pushing both** — not just committing.

## Before you commit
- Run the tests: `python3 -m pytest tests/ -q` — must be green. Every script
  change needs matching test coverage under `tests/`.
- Shrinkage practices its own doctrine: extend existing scripts/rules over
  adding new files; keep diffs minimal; a net-negative diff is a good diff.

## Every release — do ALL of these (see RELEASING.md for detail)
1. Bump `"version"` in `.claude-plugin/plugin.json` (semver).
2. Add a top entry to `CHANGELOG.md`.
3. Commit with message starting `vX.Y.Z: <summary>`.
4. `git tag vX.Y.Z`
5. `git push origin main --tags`  ← the `--tags` is REQUIRED; a tagless push
   makes the repo look stale even though code landed.

Then verify: `git ls-remote --tags origin` shows the new tag and
`git ls-remote origin HEAD` matches the release commit.

## Layout
- `.claude-plugin/` — `plugin.json` (the plugin) + `marketplace.json` (the
  self-hosted marketplace; plugin source is `./`).
- `commands/*.md` — the `/srk:*` slash commands (thin; defer to workflows).
- `skills/shrinkage/` — the skill: `SKILL.md`, `scripts/`, `rules/`,
  `references/`, `workflows/`, `agents/`, `adapters/`.
- `agents/` (repo root) — the tiered Claude Code subagents (surgeon on Haiku).
- `hooks/hooks.json` — SessionStart auto-map hook.
- `tests/` — pytest suite. `ci/tests.yml` — CI (kept out of `.github/` because
  the release PAT lacks the Workflows scope; copy it there via the GitHub UI to
  activate).

## Gotchas already learned (don't rediscover them)
- SessionStart hook stdout goes to Claude's context, NOT the user's terminal —
  don't design user-visible features around it; use the status line for that.
- The hook must be fast on large repos (60k+ files): read the cached map
  header, never fingerprint-walk the tree at session start.
- Scripts invoke via `python3` with a `python` fallback in the hook — some
  servers lack `python3`.
- Don't name a script `platform.py` (shadows stdlib) — it's `platformmap.py`.
