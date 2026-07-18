---
name: srk:update
description: "Check installed vs latest version and print the reliable update steps (uninstall → install → relaunch)"
argument-hint: "[--check]"
allowed-tools: [Bash]
---

<objective>
Tell the user whether a newer Shrinkage is available and hand them the update
path that actually works on Claude Code — without leaving the plugin in a
broken "already installed / cache-miss" state.
</objective>

<execution_context>
$SKILL is resolved FRESH for THIS invocation — never reuse a path remembered from earlier in the session (a mid-session plugin update strands version-pinned cache paths). Churn-proof order: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` if set; else the newest installed copy `$(ls -dv ~/.claude/plugins/cache/*/shrinkage/*/skills/shrinkage 2>/dev/null | tail -1)`; else the vendored locations.

Run this inline — no subagent. Locate the shrinkage skill dir
($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin,
else `.claude/skills/shrinkage` or `~/.claude/skills/shrinkage`), then run
`python3 $SKILL/scripts/selfupdate.py` and relay its output verbatim.

**Recommend auto-update first.** The lasting fix is to enable auto-update for
the `parkktech` marketplace ONCE: `/plugin` → **Marketplaces** → `parkktech` →
**Enable auto-update**. Third-party marketplaces ship with it OFF; once on,
Claude Code updates the plugin in the background after startup and prompts
`/reload-plugins` — no uninstall/install dance. Lead with this.

To update by hand, the reliable path is **uninstall → install → relaunch**:

  /plugin uninstall shrinkage@parkktech
  /plugin install shrinkage@parkktech

`uninstall` clears the cached files AND the registration together, so the
`install` genuinely re-fetches. Do NOT tell the user to just delete the plugin
cache folder — that strands the registration and Claude Code then reports
`already installed` + `cache-miss` (a loop `/plugin install` can't break). Only
if the marketplace *clone* is corrupted do they nuke
`~/.claude/plugins/marketplaces/parkktech` (with Claude Code closed) and re-add.

If the script says "up to date", say so and stop — no reinstall needed.
</execution_context>

<next>
Next:
• /plugin uninstall shrinkage@parkktech   — then /plugin install, then relaunch
• /srk:audit                              — once updated, put it to work
</next>
