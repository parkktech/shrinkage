# Shrinkage for GitHub Copilot

Copilot supports the open **Agent Skills** standard — the same `SKILL.md` +
bundled-scripts format Shrinkage is built on — across the Copilot cloud agent,
Copilot code review, Copilot CLI, and agent mode in VS Code/JetBrains. So the
primary install is no longer a hand-rolled instructions file: **vendor the
skill itself and every Copilot surface (and Claude Code) loads it natively.**

## Install — skills-native (recommended)

One copy, discovered by both runtimes:

```bash
mkdir -p .claude/skills
cp -r <shrinkage>/skills/shrinkage .claude/skills/shrinkage
```

That's it. Copilot discovers project skills in `.claude/skills`, `.github/skills`,
and `.agents/skills`; Claude Code reads `.claude/skills` — so `.claude/skills/
shrinkage` serves everyone with a single vendored copy. Prefer a GitHub-native
layout? Use `.github/skills/shrinkage` instead (Copilot-only). For a personal,
cross-repo install: `~/.copilot/skills/shrinkage`.

Notes:

- **Do NOT pre-approve `shell`/`bash` via `allowed-tools` frontmatter.** This is
  a tool that deletes code; Copilot's per-command confirmation prompt is a
  feature here, not friction. Shrinkage ships without `allowed-tools` on purpose.
- In an active Copilot CLI session, `/skills reload` picks up a fresh vendor.
- The skill's `SKILL.md` has an **Other runtimes** section covering the Copilot
  degradations — most importantly: with no Claude-side staging-guard hook,
  committing through `scripts/safe_commit.py` (and `dirty_apply.py park →
  precheck → unpark` for dirty targets) is mandatory discipline, not optional.

## Optional extras

1. **Prompt files** (IDE slash commands) — copy `prompts/*.prompt.md` into
   `.github/prompts/`. They appear as `/srk-map`, `/srk-gate`, `/srk-score`,
   `/srk-shave`, `/srk-audit`, `/srk-trend`, `/srk-query`, `/srk-config` in
   Copilot Chat. They assume the skill is vendored at
   `.claude/skills/shrinkage/` — adjust paths if you vendored elsewhere.
2. **Always-on doctrine** — append `copilot-instructions.md` from this folder
   to `.github/copilot-instructions.md`. Skills load contextually; the
   instructions file is read on every request, so the core rules (ladder, gate,
   Zeroth Law, path-limited commits) stay active even when the skill doesn't
   trigger. Also the fallback for Copilot versions predating agent skills.

## Surface notes

- **Copilot CLI / agent mode (VS Code, JetBrains):** full experience — the
  skill loads with its scripts; prompt files add the slash commands in IDEs.
- **Copilot cloud agent & code review (github.com):** read repo skills and
  `.github/copilot-instructions.md`; put standing expectations (scoreboard in
  PR descriptions, never `git add -A`) in the instructions file since prompt
  files are IDE-only.
- **Anything else with a shell:** the scripts are stdlib-only Python
  (tree-sitter optional) — any agent that can run a command can use the map,
  scoreboard, ledger, and plan CLI.
