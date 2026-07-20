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

Registered in `~/.claude/settings.json` by **stable absolute path**, on two
events:

- **`SessionStart`** — clears this session's `checked` marker, recording a new
  boot. Required because `--continue` reuses `session_id` (see Resume
  behavior); without it, a continued session would be silenced by the marker its
  own earlier run wrote. Living in user settings means it fires even when the
  plugin does not load.
- **`UserPromptSubmit`** — performs the check.

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

### Harness behavior — measured, not assumed

Every harness assumption this design rests on was verified by experiment on
Claude Code 2.1.215, each with a control:

| assumption | result | what it decided |
|---|---|---|
| `--continue` reuses `session_id` | **yes** — identical id across runs | forced the boot-clearing hook |
| `SessionStart` fires on `--continue` | **yes** — boot counter incremented | made the fix possible |
| user-scope `settings.local.json` loads hooks | **no** — control in `settings.json` fired, treatment did not | ruled out the gentler write target |
| an installed-but-unregistered plugin's hooks fire | **no** — enabled 1×, not-enabled 0×, disabled 0× | validates the heartbeat mechanism |
| `UserPromptSubmit` stdout reaches the model's context | **yes** — token reproduced verbatim | validates the warning channel |

Two of these overturned a working assumption, which is why they are recorded
here rather than left as inference:

- The `session_id` result would have silenced the watchdog on continued
  sessions — the likeliest path by which this bug reaches a user.
- `~/.claude/settings.local.json` is *listed in the docs as a settings file*,
  and would have been the less invasive target, but hooks do not load from it.
  `~/.claude/settings.json` is the only user-wide registration point that
  works. There is no hook auto-discovery directory.

Note on method: the `UserPromptSubmit` test returned a false negative on its
first run (stray stdin, and no independent record of whether the hook had
executed). Adding a hook-side log to separate "did not fire" from "fired but
undelivered" is what made the result trustworthy. Any future probe here should
carry the same corroboration.

Detail on the two resume findings:

| behavior | result |
|---|---|
| `--continue` reuses `session_id` | **yes** — identical id across runs |
| `SessionStart` fires on `--continue` | **yes** — boot counter incremented |

The first result would have broken a `session_id`-keyed `checked` marker: a
continued session is silenced by the marker its own earlier run wrote. Since
continued sessions are the likely path by which this bug reached the user, that
is the primary case failing open, not an edge case.

The second result supplies the fix. The watchdog registers its own
`SessionStart` hook in user settings, which clears the `checked` marker on every
boot. Both watchdog hooks sit outside plugin registration, so both fire whether
or not the plugin loads.

No ordering constraint between the two SessionStart hooks: the plugin's writes
`hb/<session_id>`, the watchdog's clears `checked/<session_id>`. Different files,
and `UserPromptSubmit` runs after both.

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
- boot clearing: a cleared `checked` marker re-arms the check for the same
  `session_id`, covering the `--continue` case
- planter idempotency: repeated runs produce one settings entry per event
- planter preserves unrelated keys, including a foreign `statusLine`
- malformed `settings.json`: no write, no crash
- missing `python3`: hook no-ops
- self-uninstall removes only its own entry

## Risk

The planter writing to `~/.claude/settings.json` is the one genuinely invasive
act in this design. It is mitigated by atomic merge-preserving writes, a backup
before first write, and self-uninstall on removal — but it is the piece to review
hardest.

It is also unavoidable, not merely convenient. The alternatives were considered
and eliminated: hook auto-discovery does not exist; user-scope
`settings.local.json` does not load hooks (measured); project-scope settings
protect only the repo they sit in, leaving a fresh repo — the exact first-install
case — uncovered; a separate watchdog plugin dies in the same stale registry;
and `~/.claude/CLAUDE.md` is passive and taxes every session's context.

Shrinkage already writes this file: `onboard.md` installs the `statusLine` key
there. The watchdog adds a `hooks` key beside it, which is a difference of
degree rather than kind.
