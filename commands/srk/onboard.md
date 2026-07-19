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
6. **Reference oracle — ASK, then INSTALL. Never just print a command.** This
   is an ACTION step and it runs on EVERY onboard, including a re-run: a missing
   oracle for a language the repo actually uses is a decision to put to the
   user NOW, not a status line. Run `python3 $SKILL/scripts/lsp_refs.py
   servers`. Decide which missing oracles are worth it by the map's file counts
   — a language counts only with a real presence, so **skip anything with just
   1–2 files** (a stray script isn't worth a global install). A
   415-PHP / 151-JS / 1-Python repo → PHP + JS are candidates, Python is not.

   For the worth-it missing oracles:
   - **Default (`oracle_autoinstall` false) → ASK ONE yes/no, then RUN it on
     yes.** Plain language, e.g.: *"Your frontend has 151 JS files with no
     reference oracle — want me to install it (one-time, no license) so the
     frontend gets the same semantic dead-code checking PHP already has?"* On
     **yes**, run `lsp_refs.py install <lang1> <lang2>` yourself (all worth-it
     langs in one call) and report the result. On **no**, move on. Name any
     language you skipped and why ("skipped Python: 1 file").
   - **`oracle_autoinstall` true → skip the question, just run the install** and
     report.
   - **Unattended (any flag) → don't install** (a background `npm i -g` can hang
     on sudo/network): print the `lsp_refs.py install <lang>` line and note it.

   **THE ONE FORBIDDEN OUTCOME:** ending onboard having only *shown* an install
   command for the user to copy. In an interactive session you must either ask
   and (on yes) run it, or — with the flag — just run it. "Here's the one-liner
   if you want it" is exactly the failure this step exists to prevent; a pasted
   command is never the deliverable, the installed oracle (or a clean no) is.

   `install` processes languages independently: if one hits a **permission
   wall** (only `npm i -g` on a locked-down box can — pip --user/pipx/go/rustup
   are user-level) it prints the no-admin fix + the exact command to forward to
   a server admin and CONTINUES to the next language. Relay that admin command
   verbatim; don't retry the blocked one in a loop.
   Declining is always fine — audits work without the oracle, they just lean
   fully on the dynamic-reference checklist. `install` stays opt-in by design:
   passive detection (`servers`/`check`, the audit) NEVER installs.
7. Print the quickstart: `/srk:gate "<task>"` before coding, `/srk:score`
   after, `/srk:audit` when they want the backlog, `/srk:trend` to watch the
   ratchet move.
</process>

<success_criteria>
- [ ] Map built and location policy applied
- [ ] All five settings written as explicit choices
- [ ] Status line offered (and installed on yes) — it never appears otherwise
- [ ] Oracle: for each worth-it missing language, ASKED a yes/no and RAN the
      install on yes (or just ran it if `oracle_autoinstall` true) — 1–2-file
      languages named as skipped; NEVER ended by only printing a command for the
      user to copy; never a background install unattended
- [ ] Quickstart delivered; GSD integration noted when applicable
</success_criteria>

<next>
Next:
• /srk:gate "<task>"  — before writing code
• /srk:audit          — find safe cleanup opportunities across the repo
</next>
