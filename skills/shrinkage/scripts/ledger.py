#!/usr/bin/env python3
"""ledger — read the durable shrinkage ledger (frozen / excluded / keeps).

The ledger is institutional memory the TOOL owns, not the session: paths the
tools must never edit, trees excluded from the map, and settled keep decisions
that must not be re-flagged. Every audit and shave reads it instead of
re-receiving the same context by hand each run.

Location (first that exists): `.shrinkage/ledger.md`, `SHRINK-LEDGER.md`, or
`.planning/SHRINK-LEDGER.md`. Sections are `## frozen`, `## excluded`, `## keeps`;
each row's first whitespace token is the path/glob (the rest is a human reason).
"""
import fnmatch
from pathlib import Path

NAMES = (".shrinkage/ledger.md", "SHRINK-LEDGER.md", ".planning/SHRINK-LEDGER.md")


def path(root="."):
    root = Path(root)
    for rel in NAMES:
        p = root / rel
        if p.exists():
            return p
    return None


def section(root, name):
    """First path/glob token of each content row under `## <name>` (case-insensitive)."""
    p = path(root)
    if not p:
        return []
    out, cur = [], None
    try:
        # Lenient read: the ledger is hand-authored and optional, so a file saved
        # as cp1252/latin-1 (e.g. an em-dash in a reason line) or any read hiccup
        # must degrade to "no entries" — never crash the map/audit/commit that
        # reads it with a UnicodeDecodeError (which is a ValueError, not OSError).
        text = p.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            head = line.lstrip("#").strip().split()
            cur = head[0].lower() if head else None
            continue
        if cur != name.lower():
            continue
        s = line.strip().lstrip("-*").strip()
        if not s or s.startswith(("|", "<!--")):
            continue
        out.append(s.split()[0])
    return out


def excluded(root="."):
    return section(root, "excluded")


def frozen(root="."):
    return section(root, "frozen")


def red_baselines(root="."):
    """`## red-baselines` — suites known red/quarantined. Audits skip
    re-discovering them; shaves treat any row gated on one as repair-first."""
    return section(root, "red-baselines")


def matches(rel, globs):
    """Does POSIX relpath `rel` match any glob/dir-prefix in `globs`?"""
    for g in globs:
        gg = g.rstrip("/")
        if (fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(rel, gg)
                or rel == gg or rel.startswith(gg + "/")
                or ("**" in g and fnmatch.fnmatch(rel, g.replace("**", "*")))):
            return True
    return False
