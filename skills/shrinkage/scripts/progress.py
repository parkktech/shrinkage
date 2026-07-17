#!/usr/bin/env python3
"""progress — shrinkage run progress from SHRINK-PLAN.md (v0.15).

Prints one durable-state line: how many plan items are done vs open, and the
resume command. Used by the PreCompact hook (so an auto-compaction leaves a
resume breadcrumb) and standalone for a quick "where am I" during a long run.

Usage: progress.py [--root DIR]
"""
import re
import sys
from pathlib import Path


def find_plan(root):
    for p in (root / ".planning" / "SHRINK-PLAN.md", root / "SHRINK-PLAN.md"):
        if p.exists():
            return p
    return None


def counts(text):
    """(open, done) candidate rows. Rows are `| N | ...`; struck (~~) or rows in
    a `## Done` section count as done."""
    open_n = done_n = 0
    in_done = False
    for line in text.splitlines():
        if re.match(r"^#+\s+Done\b", line, re.I):
            in_done = True
        if re.match(r"\|\s*\d+\s*\|", line):
            if in_done or "~~" in line:
                done_n += 1
            else:
                open_n += 1
    return open_n, done_n


def main():
    root = Path(sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else ".").resolve()
    plan = find_plan(root)
    if not plan:
        print("shrinkage: no SHRINK-PLAN.md — run /srk:audit to create one")
        return
    open_n, done_n = counts(plan.read_text(encoding="utf-8"))
    total = open_n + done_n
    if open_n:
        print(f"shrinkage: {done_n}/{total} plan items done · {open_n} open · "
              f"resume /srk:shave --auto")
    else:
        print(f"shrinkage: SHRINK-PLAN.md complete ({total}/{total}) · "
              f"/srk:audit to find more")


if __name__ == "__main__":
    main()
