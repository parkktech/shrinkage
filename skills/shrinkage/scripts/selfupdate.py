#!/usr/bin/env python3
"""selfupdate — reliable version check + cache clear for the srk plugin (v0.17).

Claude Code caches the plugin as a git clone pinned to a commit; a version
bump (or a force-push) can leave that cache stale or broken so `/plugin
update` silently no-ops. This does the part a plugin CAN do: report installed
vs latest, and blow away the cache so the next install re-clones cleanly. It
prints the exact reinstall lines to finish (those are user-typed TUI commands
the plugin can't invoke itself).

Usage:
  selfupdate.py            check only — installed vs latest, cache location
  selfupdate.py --clear    also remove the plugin cache (forces a fresh clone)
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = "https://github.com/parkktech/shrinkage.git"
MARKETPLACE = "parkktech"
PLUGIN = "srk"
# Claude Code stores plugin caches under one of these roots depending on runtime.
CACHE_ROOTS = [
    "~/.claude/plugins/cache", "~/.config/claude/plugins/cache",
    "~/.claude/plugins", os.environ.get("CLAUDE_CONFIG_DIR", "") + "/plugins/cache",
]


def semver(tag):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", tag)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def cache_dir():
    for root in CACHE_ROOTS:
        if not root:
            continue
        p = Path(os.path.expanduser(root)) / MARKETPLACE
        if p.exists():
            return p
    return None


def installed_version(cache):
    if not cache:
        return None
    # version dirs (srk/0.16.0/...) or a plugin.json somewhere under the cache
    vers = []
    srk = cache / PLUGIN
    if srk.is_dir():
        vers = [d.name for d in srk.iterdir() if re.match(r"\d+\.\d+\.\d+", d.name)]
    if vers:
        return max(vers, key=semver)
    for pj in cache.rglob(".claude-plugin/plugin.json"):
        try:
            return json.loads(pj.read_text(encoding="utf-8")).get("version")
        except (OSError, ValueError):
            pass
    return None


def latest_remote():
    try:
        out = subprocess.run(["git", "ls-remote", "--tags", REPO],
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    tags = re.findall(r"refs/tags/v?(\d+\.\d+\.\d+)", out.stdout)
    return max(tags, key=semver) if tags else None


def main():
    clear = "--clear" in sys.argv
    cache = cache_dir()
    inst = installed_version(cache)
    latest = latest_remote()

    print(f"srk plugin — installed: {inst or 'unknown'} · latest: {latest or 'unreachable'}")
    if cache:
        print(f"cache: {cache}")
    else:
        print("cache: none found (not installed via marketplace, or already clear)")

    if inst and latest and semver(inst) >= semver(latest):
        print("up to date." + ("" if clear else " (nothing to do)"))
    elif latest:
        print(f"update available: {inst or '?'} -> {latest}")

    if clear and cache:
        shutil.rmtree(cache, ignore_errors=True)
        print(f"cleared cache: {cache}")
        print("now run these in Claude Code, then relaunch:")
        print(f"  /plugin marketplace add {MARKETPLACE}/shrinkage")
        print(f"  /plugin install {PLUGIN}@{MARKETPLACE}")
    elif clear:
        print("no cache to clear — just: /plugin install "
              f"{PLUGIN}@{MARKETPLACE} (then relaunch)")
    elif latest and inst and semver(inst) < semver(latest):
        print("run `selfupdate.py --clear` (or /srk:update) to refresh cleanly.")


if __name__ == "__main__":
    main()
