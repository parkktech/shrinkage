# Shrinkage for GitHub Copilot

Copilot has no skills directory, so Shrinkage installs into the repo itself —
which also means every collaborator (and the Copilot coding agent) gets it.

## Install (3 steps)

1. **Vendor the skill into the repo** so paths are stable for everyone:
   ```bash
   mkdir -p .github/shrinkage
   cp -r <shrinkage>/scripts <shrinkage>/rules <shrinkage>/references \
         <shrinkage>/workflows <shrinkage>/agents .github/shrinkage/
   ```
2. **Instructions** — append `copilot-instructions.md` from this folder to
   your `.github/copilot-instructions.md` (create it if absent). This is the
   always-on doctrine: ladder, gate, Zeroth Law, scoreboard.
3. **Prompt files** — copy `prompts/*.prompt.md` into `.github/prompts/`.
   They appear as `/srk-map`, `/srk-gate`, `/srk-score`, `/srk-shave`,
   `/srk-audit`, `/srk-trend`, `/srk-config` slash commands in Copilot Chat
   (VS Code, Visual Studio, JetBrains).

The scripts are plain Python (stdlib only; tree-sitter optional) — they run
anywhere Copilot can run a terminal command.

## Surface notes

- **Copilot Chat / agent mode (IDE):** full experience — prompt files +
  instructions + scripts.
- **Copilot coding agent (github.com):** reads
  `.github/copilot-instructions.md`, so the doctrine and script paths apply;
  prompt files are IDE-only, so put standing expectations (scoreboard in PR
  descriptions) in the instructions file.
- **Copilot CLI:** supports custom instructions; point it at the same
  vendored paths.

Prompt files are in public preview upstream — if a frontmatter field is
rejected, trim to `description` + body; the bodies are self-contained.
