#!/usr/bin/env python3
"""guard_staging — PreToolUse hook: block broad git staging DURING a shave.

Scoped to shave sessions only (a marker file the shave workflow writes), so
normal development is never touched. Rejects `git add -A|.|--all|-u` and
`git commit -a|--all|-am` — the broad-staging commands that once swept a user's
179 dirty files into a shave commit (safety-model §6). Points at safe_commit.py.

Fails OPEN: any error, no active shave marker, or an unparseable command → allow
(exit 0). Only a confirmed forbidden command during an active shave blocks
(exit 2, plus a deny decision for hosts that read structured output).
"""
import json
import os
import re
import shlex
import sys
import time

MARKERS = (".claude/srk-shave-active", ".planning/.srk-shave-active")
_MAX_AGE = 2 * 3600  # a stale marker (crashed shave) stops guarding after 2h


def shave_active():
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    for rel in MARKERS:
        p = os.path.join(root, rel)
        try:
            if os.path.exists(p):
                if (time.time() - os.path.getmtime(p)) < _MAX_AGE:
                    return True
                # Stale marker = a crashed shave. Self-clean so it can't linger
                # as cruft (or re-arm if anything ever touches its mtime).
                try:
                    os.remove(p)
                except OSError:
                    pass
        except OSError:
            pass
    return bool(os.environ.get("SRK_SHAVE_ACTIVE"))


def forbidden(cmd):
    """Return a short label for the first broad-staging git subcommand, else None."""
    for part in re.split(r"[;&|\n]+", cmd):
        try:
            toks = shlex.split(part)
        except ValueError:
            continue
        if len(toks) < 2 or toks[0] != "git":
            continue
        sub, rest = toks[1], toks[2:]
        if sub == "add":
            for t in rest:
                if t in ("-A", "--all", ".", "-u", "--update") or \
                        re.fullmatch(r"-[A-Za-z]*A[A-Za-z]*", t):
                    return f"git add {t}"
        elif sub == "commit":
            for t in rest:
                if t == "--all" or re.fullmatch(r"-[a-z]*a[a-z]*", t):
                    return f"git commit {t}"
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("tool_name") != "Bash":
        sys.exit(0)
    cmd = (data.get("tool_input") or {}).get("command", "")
    if not cmd or not shave_active():
        sys.exit(0)
    hit = forbidden(cmd)
    if not hit:
        sys.exit(0)
    reason = (
        f"[shrinkage] Blocked `{hit}` during an active shave. Broad staging can "
        "sweep the user's in-flight work into a shave commit (safety-model §6). "
        "Commit only your transform's files:\n"
        "  python3 $SKILL/scripts/safe_commit.py -m \"<msg>\" -- <file> [<file>...]\n"
        "or explicit paths:  git add -- <file> ; git commit -- <file> -m \"<msg>\"")
    try:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": reason}}))
    except Exception:
        pass
    sys.stderr.write(reason + "\n")
    sys.exit(2)


if __name__ == "__main__":
    main()
