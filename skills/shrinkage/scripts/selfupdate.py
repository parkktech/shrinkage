#!/usr/bin/env python3
"""selfupdate — version check + the reliable update path for the shrinkage plugin.

Claude Code caches a plugin as a git clone and *registers* the install
separately. The trap: deleting the cache folder (which an earlier version of
this script did) leaves the plugin still registered but with no files, and
Claude Code then reports `already installed` + `cache-miss` — an unbreakable
loop, because `/plugin install` no-ops on a registered plugin.

So this script does NOT touch the filesystem. It reports installed vs latest and
prints the update path that actually works on Claude Code: `/plugin uninstall`
(which clears the cached files AND the registration together) then
`/plugin install`, then relaunch.

Usage: selfupdate.py            report installed vs latest + the update steps
       selfupdate.py --check    same (kept for compatibility)
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = "https://github.com/parkktech/shrinkage.git"
MARKETPLACE = "parkktech"
PLUGIN = "shrinkage"
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
    vers = []
    pdir = cache / PLUGIN
    if pdir.is_dir():
        vers = [d.name for d in pdir.iterdir() if re.match(r"\d+\.\d+\.\d+", d.name)]
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
    cache = cache_dir()
    inst = installed_version(cache)
    latest = latest_remote()

    print(f"shrinkage plugin — installed: {inst or 'unknown'} · latest: {latest or 'unreachable'}")
    print(f"cache: {cache}" if cache
          else "cache: none found (not installed via marketplace, or already clear)")

    if inst and latest and semver(inst) >= semver(latest):
        print("up to date — nothing to do.")
        return
    if latest:
        print(f"update available: {inst or '?'} -> {latest}")

    # The path that actually works on Claude Code. uninstall clears the cached
    # FILES and the REGISTRATION together — do NOT just delete the cache folder,
    # that strands the registration and yields 'already installed' + 'cache-miss'.
    print("\nto update, run these in Claude Code, then quit and relaunch:")
    print(f"  /plugin uninstall {PLUGIN}@{MARKETPLACE}")
    print(f"  /plugin install {PLUGIN}@{MARKETPLACE}")
    print("(uninstall FIRST — a bare /plugin install no-ops on an already-registered plugin.)")
    print("\nonly if the marketplace clone is corrupted, with Claude Code CLOSED:")
    print(f"  rm -rf ~/.claude/plugins/marketplaces/{MARKETPLACE} ~/.claude/plugins/cache/{MARKETPLACE}")
    print(f"  then reopen and run: /plugin uninstall {PLUGIN}@{MARKETPLACE} ; "
          f"/plugin marketplace add {MARKETPLACE}/{PLUGIN} ; /plugin install {PLUGIN}@{MARKETPLACE}")


if __name__ == "__main__":
    main()
