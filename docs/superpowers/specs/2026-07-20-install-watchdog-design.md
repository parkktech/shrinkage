# Install Watchdog — self-diagnosing first run

**Date:** 2026-07-20
**Status:** Approved design, not yet implemented
**Branch:** `feature/install-watchdog`

## Problem

Shrinkage installed cleanly (`cache/parkktech/shrinkage/0.40.3/` complete, all 12
command files present, `enabledPlugins` set, CLI 2.1.215 — past the v2.1.193 the
`renames` migration needs). Yet `/srk` in the running session returned
**"No commands match"**. A headless `claude -p "/srk:help"` from the same
directory ran the real command and printed the full reference.

So the install was correct and the *running process* was stale. `/reload-plugins`
recovered it (`Reloaded: 7 plugins · 14 skills · 73 agents · 13 hooks`).

The defect is not the install. **The defect is that the failure was silent.** The
plugin was invisible to the user (empty `/srk`) and invisible to Claude, who had
no signal and reported the install as healthy. It took a multi-step manual
investigation to discover a one-command fix.

### Why the existing nudges can't catch this

`hooks.json` already emits advisory `[shrinkage]` text from SessionStart. That
hook never fired here, because it lives *inside* the plugin that failed to load.
**A hook inside the plugin cannot detect the plugin failing to load.** Any
detector must live outside plugin registration.

## Goal

The first run diagnoses itself. When Shrinkage is installed but not loaded, the
user is told so — in the conversation, where the confusion happens — along with
the cheapest recovery (`/reload-plugins`) before the expensive one (relaunch).

Non-goals: fixing Claude Code's pinned-cache bugs (#14061/#16866/#29074);
reworking install mechanics; changing what `/srk:onboard` configures.

## Architecture

Five components. Everything lives under `~/.claude/shrinkage/` except one
settings entry.

### 1. Heartbeat writer — plugin `hooks.json`, SessionStart

Writes `~/.claude/shrinkage/state/hb/<session_id>`. Proof-of-life that the plugin
loaded this session. Prunes entries older than a day.

### 2. Watchdog — `~/.claude/shrinkage/watchdog.py`

Registered as a `UserPromptSubmit` hook in `~/.claude/settings.json`, referenced
by **stable absolute path**.

`UserPromptSubmit` rather than `SessionStart` is load-bearing: it fires strictly
after all SessionStart hooks have completed, so "no heartbeat" unambiguously
means "the plugin hook did not run" rather than "has not run yet". Registering
the watchdog at SessionStart would race the very hook it observes.

On the first prompt of a session it emits, when warranted:

```
[shrinkage] installed but not loaded in this session.
Try /reload-plugins first. If commands are still missing, quit and
relaunch claude — without --continue or --resume.
```

### 3. Planter — plugin SessionStart

On first successful load, silently copies the watchdog to the stable path and
adds the settings entry. Idempotent; merges into existing hooks rather than
overwriting. Re-copies when the plugin version differs from the recorded
watchdog version, so upgrades do not strand an old script.

Silent by design: the watchdog is planted with zero questions, and the optional
extras (status line, oracle, preferences) remain a normal Next-menu offer. The
first session a user opens is theirs, not ours.

### 4. Statusline segment — `statusline.py`

Same detection, rendered as `⚠ srk not loaded` on the chained bar. Ambient
reinforcement only; the watchdog is the load-bearing signal because it reaches
Claude's context and a status bar does not.

### 5. Self-uninstall — inside the watchdog

If Shrinkage is no longer enabled, or its install directory is gone, the watchdog
removes its own settings entry and exits. Without this, `/plugin uninstall`
strands a hook pointing at a deleted script — the fix would manufacture a new
failure mode.

## Detection logic

The heartbeat is **consume-on-read**: SessionStart writes it, the watchdog
deletes it on read. This makes the check time-independent — no freshness window
to tune, and no false alarm when a session sits idle for hours before its first
prompt. A separate `state/checked/<session_id>` marker keeps it to one check per
session.

Decision matrix:

| enabled in settings | on disk | heartbeat | action |
|---|---|---|---|
| yes | yes | present | silent (healthy) |
| yes | yes | absent | **warn** |
| no | either | — | self-uninstall |
| yes | missing | — | self-uninstall |

`enabled in settings` must be resolved across **all** scopes (user, project,
`settings.local.json`), not just `~/.claude/settings.json`.

### Known limitation

If `--resume` reuses the original `session_id`, the `checked` marker from the
first run silences the watchdog on resume. This fails *silent* rather than
false-positive, which is the safe direction, but resumed sessions are exactly how
this bug reached the user. **Verify Claude Code's actual resume/session-id
behavior during implementation** and revisit if ids are reused.

## Failure modes — all fail-open

- **No `python3`** → hook no-ops. A diagnostic must never block a prompt.
- **Malformed `settings.json`** → planter aborts and logs; never writes.
  Corrupting user settings is worse than the bug being fixed.
- **Settings writes** are atomic (temp + rename) and merge-preserving. Another
  tool may own `statusLine` (GSD does, in the reporting environment) and must
  survive untouched.
- **Concurrent sessions** → all state is per-`session_id`; no shared mutable
  state.
- **Latency** budget <50ms: stdlib only, a handful of `stat` calls. This runs on
  every prompt.

## Testing

Detection stays a **pure function of (settings, disk, heartbeat)** so it is
testable without a live Claude Code. Add `tests/test_watchdog.py` alongside the
existing suite:

- one case per decision-matrix row, over fixture trees
- consume-on-read: second invocation in the same session stays silent
- planter idempotency: repeated runs produce one settings entry
- planter preserves unrelated keys, including a foreign `statusLine`
- malformed `settings.json`: no write, no crash
- missing `python3`: hook no-ops
- self-uninstall removes only its own entry

## Risk

The planter writing to `~/.claude/settings.json` is the one genuinely invasive
act in this design. It is mitigated by atomic merge-preserving writes, a backup
before first write, and self-uninstall on removal — but it is the piece to review
hardest.
