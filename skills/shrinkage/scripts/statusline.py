#!/usr/bin/env python3
"""statusline — a Claude Code status line for Shrinkage.

Point your status line at this script (run /statusline and ask for it, or set
settings.json statusLine.command). Shows the shrink trend when active, or the
getting-started nudge when the repo hasn't scored anything yet.
"""
import json
from pathlib import Path

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
    print(f"srk {arrow}{app:+d} LOC · streak {streak}")
elif Path(".claude/codemap.txt").exists() or Path(".planning/intel/codemap.txt").exists():
    print("srk: mapped — /srk:gate before code, /srk:score --log after")
else:
    print("srk: run /srk:onboard to start shrinkage-optimized coding")
