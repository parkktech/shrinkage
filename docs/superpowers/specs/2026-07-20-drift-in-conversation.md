# Version drift in-conversation — the update hint gets a voice

**Date:** 2026-07-20
**Status:** Implemented (option 2); unreleased
**Branch:** `feature/drift-in-conversation`
**Follows:** `2026-07-20-install-watchdog-design.md` (v0.41.0)

## Problem

v0.41.0 shipped. On the release machine — which had Shrinkage installed, loaded,
and healthy — **nothing anywhere reported that 0.40.3 was now stale.** No status
line hint, no conversational note, no signal to Claude, who went on describing
the install as current.

Detection is not the missing piece. `statusline.py` already carries the whole
mechanism: `installed_version()`, `origin_url()`, `latest_from_tags()`,
`check_update()`, a TTL cache at `~/.claude/shrinkage-update.json`, and the
rendered `⬆ /srk:update to vX.Y.Z`. `origin_url()` even resolves the marketplace
*origin* rather than the local clone, specifically so a stale clone still sees
new tags.

**The defect is delivery, not detection.** Two independent failures, both
measured on the release machine.

### Failure 1 — the only channel is a status line the user may not own

The drift hint renders in exactly one place: the srk status line segment. On the
release machine:

```
statusLine.command → "…/hooks/gsd-statusline.js"      srk segment: absent
```

GSD owns the status line. Shrinkage's own docs tell it not to fight for it —
`statusline.py` opens by saying another tool's bar must **never** be replaced,
only chained onto. That is correct and should stay. But it means the sole
delivery channel for version drift is *optional*, *foreign-owned*, and here
simply **off**. Anyone running GSD — or any other status line — is silently
outside update notification entirely.

This is the install-watchdog defect one channel over. That spec's finding was:

> The plugin was invisible to the user (empty `/srk`) and invisible to Claude,
> who had no signal and reported the install as healthy.

Version drift is, today, invisible to the user and invisible to Claude.

### Failure 2 — negative results are cached as long as positive ones

`check_update()` always writes `checked_at`, including on failure, so a broken
remote cannot cause a respawn storm. That reasoning is sound. But the failure is
then cached under the **same 6-hour TTL as a success**:

```
{"checked_at": <13:24>, "latest": null}     age 1.2h · TTL 6h · stale: false
```

Measured: the 13:24 check ran while the machine's SSH auth was misconfigured, so
`git ls-remote` exited non-zero and `latest` was recorded as `null`. Re-running
the identical call after auth was fixed returned `0.41.0`. The null was not a
verdict — it was a transient error frozen for six hours.

Any transient condition — auth not yet configured, laptop offline, network blip,
GitHub hiccup — therefore suppresses the update hint for a full TTL after it has
stopped applying. First-install is the worst case: a fresh machine is exactly
where auth is least likely to be ready, and where the hint matters most.

## Goal

When the running copy is behind the latest released tag, say so **in the
conversation**, where the watchdog already speaks — so the signal reaches both
the user and Claude regardless of who owns the status line. And let a failed
check retry promptly instead of masquerading as a six-hour-old answer.

**Non-goals.** No new version-detection logic: it exists and works, and this
design adds none. No second network call — the existing cache is the only
source. No change to the status line segment, which stays exactly as it is for
users who do have it. Still not fixing the pinned-cache bugs
(#14061/#16866/#29074); this reports drift, it does not repair it.

## Architecture

Two changes. Neither introduces a new component.

### 1. Split the cache TTL by outcome — `statusline.py`

One constant becomes two:

```python
TTL = 6 * 3600          # a successful answer stays fresh for 6h
TTL_FAILED = 15 * 60    # a failed check is retried in 15m
```

Staleness is chosen by whether `latest` resolved:

```python
ttl = TTL if data.get("latest") else TTL_FAILED
stale = (time.time() - data.get("checked_at", 0)) > ttl
```

This preserves the anti-respawn-storm property in full — a persistently broken
remote still backs off, just at 15 minutes rather than 6 hours — while ensuring
a transient failure self-heals on the order of the next few prompts. The
distinction is ordinary negative-vs-positive caching; the current code simply
has one TTL where it needs two.

### 2. The watchdog reads the cache and speaks — `watchdog.py`

The watchdog already runs on `UserPromptSubmit`, outside plugin registration,
once per session, with a proven in-conversation channel. It gains one more
observation: read `~/.claude/shrinkage-update.json` (honoring
`$SRK_UPDATE_CACHE`) and compare `latest` against `installed_version()`.

**Cache-read only.** The watchdog never calls the network, never spawns the
worker, never writes the cache. It reports what the status line machinery has
already discovered. This keeps the <50ms per-prompt budget — a single small
JSON read — and keeps exactly one component owning the remote call.

Emitted on the first prompt of a session when warranted:

```
[shrinkage] running v0.40.3 · v0.41.0 released. /srk:update for the steps.
```

The verdict set becomes `healthy | warn | drift | uninstall`. `warn`
(installed-but-not-loaded) **outranks** `drift`: a plugin that did not load is
the more urgent problem, and reporting both in one prompt is noise. Drift is
reported only from an otherwise-healthy state.

Version comparison reuses `semver()` from `statusline.py`, re-derived rather
than imported — the same rationale the watchdog already documents for
`NOT_LOADED_FLAG`: the two files ship and update independently, so an import
would couple them.

## Detection logic

Evaluated only when the load-state verdict is `healthy`:

| installed | cache `latest` | comparison | verdict |
|---|---|---|---|
| known | absent / null | — | `healthy` (silent — nothing known) |
| known | equal | `==` | `healthy` |
| known | lower | `<` installed | `healthy` (local build ahead of tags) |
| known | higher | `>` installed | **`drift`** |
| unknown (vendored) | any | — | `healthy` (silent) |
| any | unparseable semver | — | `healthy` (silent) |

Silence is the default everywhere the answer is not confidently "behind."
A vendored install with no `plugin.json` and no `/x.y.z/` path segment yields no
version and must never be nagged — `installed_version()` already returns `None`
for exactly this case.

Consume-on-read matches the existing watchdog behavior: once per session, keyed
on the same per-boot `checked` marker, so `--continue` re-arms it.

## Failure modes — all fail-open

- **Cache absent** (first ever run, before the worker has finished) → silent.
  The status-line-less case that would otherwise make this permanent is closed
  by the SessionStart spawn below; the remaining window is one session at most.
- **Cache malformed** → silent, no crash, no rewrite. A diagnostic must never
  corrupt state it does not own.
- **Clock skew** making `checked_at` future-dated → treated as fresh, silent.
  Never nag on nonsense.
- **Latency** unchanged in the common case: one `stat` plus a small JSON read,
  no subprocess, no network.
- The status line segment's behavior is **byte-identical** for existing users
  apart from failed checks refreshing sooner.

## Resolved — who spawns the worker when there is no status line

**Decision: option 2.** The plugin's SessionStart hook calls
`statusline.py --refresh-if-stale`, which spawns the detached worker when the
cache is stale and prints nothing. The watchdog stays a pure reader; the
network call stays off `UserPromptSubmit`.

Verified end-to-end against the exact failure this spec documents — a
`{"latest": null}` cache aged 1.2h, the state measured on the release machine:

```
cache before: {"checked_at": …, "latest": null}
--refresh-if-stale
cache after:  {"checked_at": …, "latest": "0.41.0"}
```

and the watchdog then reporting it, ranking correctly, and consuming on read:

```
loaded, behind      → [shrinkage] running v0.40.3 · v0.41.0 released. …
same session again  → (silent)
not loaded, behind  → installed-but-not-loaded only; drift suppressed
```

### The two candidates as weighed

1. **The watchdog spawns it** when the cache is missing or stale — detached,
   fire-and-forget. Closes the gap completely; costs the watchdog its
   cache-read-only purity and puts a network call behind a prompt hook.
2. **The plugin's SessionStart hook spawns it** — already runs when the plugin
   loads (it writes the heartbeat), already off the prompt path. Cheaper and
   better placed, but does nothing for a not-loaded session — which is fine,
   since `warn` outranks `drift` in that state anyway.

The split TTL fixes *staleness*, but on a machine with no srk status line
segment the worker may never run at all, leaving the cache permanently absent
and the watchdog permanently silent. Two candidates:

1. **The watchdog spawns it** when the cache is missing or stale — detached,
   fire-and-forget, same pattern the status line already uses. Closes the gap
   completely; costs the watchdog its cache-read-only purity and puts a network
   call behind a prompt hook.
2. **The plugin's SessionStart hook spawns it** — already runs when the plugin
   loads (it writes the heartbeat), already off the prompt path. Cheaper and
   better placed, but does nothing for a not-loaded session — which is fine,
   since `warn` outranks `drift` in that state anyway.

Option 2 keeps the network call off `UserPromptSubmit`, preserves the watchdog
as a pure reader, and its blind spot is a state where drift would be suppressed
regardless.

## Testing

Detection stays a pure function of (cache contents, installed version), testable
without a live Claude Code or network. Extend `tests/test_watchdog.py`:

- one case per decision-matrix row
- `drift` is suppressed when the load verdict is `warn`
- consume-on-read: second prompt in the same session is silent
- boot clearing re-arms drift for the same `session_id` (`--continue`)
- absent / malformed / future-dated cache → silent, no write, no crash
- vendored install (no version) → silent

Extend `tests/test_statusline.py`:

- a `latest: null` entry older than `TTL_FAILED` is stale; younger is fresh
- a successful entry stays fresh to the full `TTL`
- **regression for Failure 2**: a null entry at 1.2h — the exact measured
  case — is treated as stale and re-checked

## Risk

Low. No new network calls, no settings writes, no new files, no change to the
install or removal path. The one behavior change for existing users is failed
update checks retrying at 15 minutes instead of 6 hours, which strictly
increases `git ls-remote` frequency only on machines already failing to reach
the remote — bounded, and still heavily backed off.

The real risk is **nag fatigue**. The watchdog's credibility rests on speaking
rarely and only when actionable. Drift is a weaker signal than not-loaded: the
user may be pinned deliberately. Mitigations: once per session, only from an
otherwise-healthy state, outranked by `warn`, and silent under every uncertainty
in the matrix above. If it still proves noisy, the next lever is a
`drift_notify` config key alongside the existing settings rather than more
in-message conditions.
