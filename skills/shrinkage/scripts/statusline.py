#!/usr/bin/env python3
"""statusline — a Claude Code status line for Shrinkage.

Point your status line at this script (run /statusline and ask for it, or set
settings.json statusLine.command). Shows the shrink trend when active, or the
getting-started nudge when the repo hasn't scored anything yet — plus an
update hint (`⬆ /srk:update to vX.Y.Z`) when the marketplace has a newer
release than the installed plugin (the GSD-style bottom-bar nudge).

The update check NEVER blocks a render: every display reads a small cache
(~/.claude/shrinkage-update.json, override with $SRK_UPDATE_CACHE); when the
cache is older than 6h, a detached background `--check-update` process
refreshes it with `git ls-remote --tags` against the marketplace's origin.
A version-agnostic settings.json command (survives plugin updates):

  "statusLine": {"type": "command", "command":
    "python3 $(ls -dv ~/.claude/plugins/cache/parkktech/shrinkage/*/ | tail -1)skills/shrinkage/scripts/statusline.py"}
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

TTL = 6 * 3600  # re-check the remote at most every 6 hours


def cache_path():
    p = os.environ.get("SRK_UPDATE_CACHE")
    return Path(p) if p else Path.home() / ".claude" / "shrinkage-update.json"


def installed_version():
    """Version of the running copy: nearest .claude-plugin/plugin.json above this
    file (the plugin cache is a full repo copy), else a /x.y.z/ path segment.
    None (→ no hint) for vendored installs that carry neither."""
    here = Path(__file__).resolve()
    for d in here.parents:
        pj = d / ".claude-plugin" / "plugin.json"
        if pj.exists():
            try:
                return json.loads(pj.read_text(encoding="utf-8")).get("version")
            except (OSError, ValueError):
                break
    m = re.search(r"/(\d+\.\d+\.\d+)/", str(here))
    return m.group(1) if m else None


def origin_url():
    """The marketplace clone's origin remote, found from this file's cache path:
    <plugins>/cache/<mp>/<plugin>/<ver>/… → <plugins>/marketplaces/<mp>. Checking
    the ORIGIN (not the local clone) sees new tags even when the clone is stale."""
    if os.environ.get("SRK_REPO_URL"):
        return os.environ["SRK_REPO_URL"]
    parts = Path(__file__).resolve().parts
    if "cache" in parts:
        i = parts.index("cache")
        if i + 1 < len(parts):
            mp = Path(*parts[:i]) / "marketplaces" / parts[i + 1]
            try:
                r = subprocess.run(["git", "-C", str(mp), "remote", "get-url", "origin"],
                                   capture_output=True, text=True)
            except (OSError, subprocess.SubprocessError):
                return None
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
    return None


def semver(s):
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)$", (s or "").strip())
    return tuple(int(g) for g in m.groups()) if m else None


def latest_from_tags(text):
    """Highest semver among `git ls-remote --tags` lines (peeled ^{} lines and
    non-semver tags are ignored)."""
    best = None
    for line in text.splitlines():
        m = re.search(r"refs/tags/v?(\d+\.\d+\.\d+)$", line.strip())
        if m and (best is None or semver(m.group(1)) > semver(best)):
            best = m.group(1)
    return best


def check_update():
    """Background worker: ask the remote for its tags, write the cache. Always
    writes checked_at (even on failure) so a broken remote can't cause a
    respawn storm — we just try again after the TTL."""
    url = origin_url()
    latest = None
    if url:
        try:
            r = subprocess.run(["git", "ls-remote", "--tags", url],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                latest = latest_from_tags(r.stdout)
        except (OSError, subprocess.SubprocessError):
            pass
    cp = cache_path()
    try:
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(json.dumps({"checked_at": int(time.time()), "latest": latest}),
                      encoding="utf-8")
    except OSError:
        pass


def update_hint():
    """The ` · ⬆ /srk:update to vX.Y.Z` segment, or ''. Cache-read only —
    a stale cache kicks off a DETACHED background refresh and returns the old
    answer; a render is never blocked on the network."""
    inst = semver(installed_version())
    if not inst:
        return ""
    cp = cache_path()
    data = {}
    try:
        data = json.loads(cp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if int(time.time()) - int(data.get("checked_at", 0)) > TTL:
        try:
            cp.parent.mkdir(parents=True, exist_ok=True)
            cp.write_text(json.dumps({"checked_at": int(time.time()),
                                      "latest": data.get("latest")}), encoding="utf-8")
            subprocess.Popen([sys.executable, __file__, "--check-update"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        except OSError:
            pass
    latest = semver(data.get("latest"))
    if latest and latest > inst:
        return f" · ⬆ /srk:update to v{data['latest']}"
    return ""


def main():
    if "--check-update" in sys.argv:
        check_update()
        return
    log = Path(".git/info/shrinkage-log.jsonl")
    if not log.exists():
        log = Path(".claude/shrinkage-log.jsonl")
    if log.exists():
        entries = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
        app = sum(e.get("net_app", 0) for e in entries)
        streak = 0
        for e in reversed(entries):
            if e.get("net_app", 0) >= 0:
                break
            streak += 1
        arrow = "▼" if app < 0 else "▲"
        line = f"srk {arrow}{app:+d} LOC · streak {streak}"
    elif Path(".claude/codemap.txt").exists() or Path(".planning/intel/codemap.txt").exists():
        line = "srk: mapped — /srk:gate before code, /srk:score --log after"
    else:
        line = "srk: run /srk:onboard to start shrinkage-optimized coding"
    print(line + update_hint())


if __name__ == "__main__":
    main()
