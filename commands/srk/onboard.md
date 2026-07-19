---
name: srk:onboard
description: "▶ START HERE — one-shot setup: status line, codemap, every preference (gate, map policy, PR scoreboard, comedy), quickstart"
argument-hint: ""
allowed-tools: [Bash, Read, Write]
---

<objective>
Set up Shrinkage in this repo in one pass — map built, all settings captured
as conscious choices, user ready to work.
</objective>

<process>
1. Locate the shrinkage skill dir ($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else `.claude/skills/shrinkage` or `~/.claude/skills/shrinkage`). Run
   `python3 $SKILL/scripts/codemap.py build` and show the summary (files,
   symbols, ~tokens, languages, any unsupported languages worth an adapter).
2. **Offer the status line FIRST — before any other preference** (the
   always-visible layer: trend + streak at the bottom of Claude Code, plus an
   `⬆ /srk:update` nudge when a newer plugin release exists). This NEVER
   appears unless configured — Claude Code only renders a status line when
   settings define one, and a plugin cannot set it for you, so this question is
   the only reliable install point. **Check the existing settings first**
   (`.claude/settings.json`, `.claude/settings.local.json`,
   `~/.claude/settings.json`) — there is only ONE statusLine slot:

   - **No status line configured** → install the full bar. Standalone mode
     also renders the session basics (model │ dir │ ctx %) from stdin, so
     nothing is missing versus a general-purpose bar. Merge into
     `.claude/settings.json` (create if absent, preserve other keys):

     ```json
     {"statusLine": {"type": "command", "command":
       "python3 $(ls -dv ~/.claude/plugins/cache/parkktech/shrinkage/*/ | tail -1)skills/shrinkage/scripts/statusline.py"}}
     ```

   - **A status line already exists (GSD's, a custom one) → NEVER replace it.**
     CHAIN instead: keep their command verbatim and add the srk segment on its
     own line beneath (multi-line status lines are supported). Rewrite the slot
     to a wrapper that tees stdin to both:

     ```json
     {"statusLine": {"type": "command", "command":
       "sh -c 'IN=$(cat); printf \"%s\" \"$IN\" | { <their existing command, verbatim>; }; printf \"%s\" \"$IN\" | python3 $(ls -dv ~/.claude/plugins/cache/parkktech/shrinkage/*/ | tail -1)skills/shrinkage/scripts/statusline.py --segment'"}}
     ```

     Show the user the before/after command and confirm before writing —
     you are rewrapping a setting another tool installed.

   The `ls -dv | tail -1` picks the newest installed plugin copy, so the
   setting survives updates. Vendored (non-plugin) installs point at
   `.claude/skills/shrinkage/scripts/statusline.py` instead. Takes effect on
   the next session start.
3. Walk the user through every setting, one question with a recommended
   default (interactive sessions — unattended runs take defaults silently):
   - **commit_map** — commit the map (team-shared) or keep it gitignored
     (default; always fresh)?
   - **gate** — soft (justifications suffice, default) or hard (confirm
     before any new file/module)?
   - **pr_scoreboard** — put the scoreboard block in PR descriptions? (great
     for teams; default off)
   - **budget** — map token budget; default 4000, raise for big repos, or
     plan to use `scope` in monorepos.
   - **humor** — the comedy setting. Quips on (default) or straight-faced?
     Ask with a straight face.
4. Write the answers to `.claude/shrinkage.json`; re-run
   `codemap.py refresh` so map location/gitignore reflect the choices.
5. GSD project detected → point out the auto-integration (map + api-map.json
   in `.planning/intel/`, SHRINK-PLAN.md target, SUMMARY.md scoreboard lines).
6. **Reference oracle — check, then OFFER TO INSTALL.** Run `python3
   $SKILL/scripts/lsp_refs.py servers` and show the output. Cross-reference the
   ✗ rows against the languages THIS repo actually uses (from the map you just
   built — don't offer a Rust oracle to a PHP-only repo). For each missing
   oracle whose language is present:
   - **Interactive session → ask before installing.** One question per language
     (or a single grouped one): "Install the PHP oracle? It's `intelephense`
     via npm — a global package-manager install on this machine, one-time,
     no license needed. It upgrades every audit's dead-code check from lexical
     to semantic." On **yes**, run `python3 $SKILL/scripts/lsp_refs.py install
     <lang>` and show the result — it runs the right package manager, then
     re-checks the binary is actually on PATH (a package that lands off-PATH is
     reported as a warning, never a false success). On **no**, move on.
   - **Unattended session → never auto-install** (a background `npm i -g` could
     hang on sudo/network). Just print the exact `lsp_refs.py install <lang>`
     line for the user to run when they're back, and note it in the close.
   Either way, declining is fine — audits work without the oracle, they just
   lean fully on the dynamic-reference checklist. `install` is opt-in by
   design: passive detection (`servers`/`check`, the audit) NEVER installs.
7. Print the quickstart: `/srk:gate "<task>"` before coding, `/srk:score`
   after, `/srk:audit` when they want the backlog, `/srk:trend` to watch the
   ratchet move.
</process>

<success_criteria>
- [ ] Map built and location policy applied
- [ ] All five settings written as explicit choices
- [ ] Status line offered (and installed on yes) — it never appears otherwise
- [ ] Oracle availability shown (`lsp_refs.py servers`); install OFFERED and
      (on yes, interactive) RUN for missing languages the repo uses — never
      auto-installed unattended
- [ ] Quickstart delivered; GSD integration noted when applicable
</success_criteria>

<next>
Next:
• /srk:gate "<task>"  — before writing code
• /srk:audit          — find safe cleanup opportunities across the repo
</next>
