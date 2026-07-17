---
name: srk:update
description: "Reliably update the srk plugin: check installed vs latest version and clear the stale plugin cache"
argument-hint: "[--check]"
allowed-tools: [Bash]
---

<objective>
Make updating the srk plugin reliable — clear the cached clone (which Claude
Code pins to a commit and can leave stale after a version bump or force-push)
so a fresh install picks up the latest.
</objective>

<execution_context>
Run this inline — no subagent. Locate the shrinkage skill dir
($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin,
else `.claude/skills/shrinkage` or `~/.claude/skills/shrinkage`).

- `--check` (or bare, cautious): `python3 $SKILL/scripts/selfupdate.py` —
  report installed vs latest version and the cache location; change nothing.
- Otherwise: `python3 $SKILL/scripts/selfupdate.py --clear` — report versions
  AND remove the plugin cache so the next install re-clones cleanly.

Then relay the script's output verbatim, and tell the user the two commands to
finish (the plugin can't invoke `/plugin` itself):

  /plugin marketplace add parkktech/shrinkage
  /plugin install shrinkage@parkktech

…and to **quit and relaunch** Claude Code. If the script reports "up to date",
say so and stop — no reinstall needed.
</execution_context>

<next>
Next:
• /plugin install shrinkage@parkktech   — after the cache clear (then relaunch)
• /srk-audit                       — once updated, put it to work
</next>
