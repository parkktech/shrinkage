#!/usr/bin/env python3
"""records — change records that stop a repo taking two steps forward, one back.

Three records travel with every code change (on by default, `"change_records": false` to opt out):

- **Feature ledger** (`docs/FEATURE-LEDGER.md` or `FEATURE-LEDGER.md`) — one row per user-visible
  capability with a stable ID, its code paths and its guard test in backticks. Rows are never
  deleted; a retired feature becomes `Retired` with the owner's recorded OK.
- **Changelog** (`CHANGELOG.md`, Keep a Changelog) — a line under `## [Unreleased]`.
- **Regression log** (ledger §2) — every fix names what broke it and the guard that now catches it.

A commit touching source code must stage the ledger and changelog, or say `[ledger: none]` /
`[changelog: none]` in its message; a fix (`fix` in the subject) must stage the ledger. Each record
is enforced only once the repo has that file (`init` creates both).

    records.py init                  create CHANGELOG.md + docs/FEATURE-LEDGER.md if absent
    records.py check [--msg FILE]    gate the staged change (commit-msg hook / CI)
    records.py verify                every live ledger path still exists (nothing vanished)
    records.py protected <path>...   ledger rows that reference these paths
    records.py hook                  PreToolUse(Bash) mode: gate `git commit` before it runs
"""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
from parsers import language_of  # noqa: E402

LEDGER_NAMES = ("docs/FEATURE-LEDGER.md", "FEATURE-LEDGER.md")
CHANGELOG = "CHANGELOG.md"
NON_CODE_PARTS = {"test", "tests", "spec", "specs", "__tests__", "docs", "doc", "fixtures",
                  "vendor", "node_modules"}
ROW_ID = re.compile(r"^\|\s*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+)\s*\|")
TICKED_PATH = re.compile(r"`([\w.@/-]+/[\w.@-]+)`")
UNCHECKED_STATUSES = {"Planned", "Retired"}

CHANGELOG_TEMPLATE = """# Changelog

All notable changes, written for the people who use the software. Format:
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Every commit that changes source code adds a line under `[Unreleased]` in the right group (Added,
Changed, Deprecated, Removed, Fixed, Security), or says `[changelog: none]` in its message.
Anything Deprecated or Removed names the owner's OK from the feature ledger.

## [Unreleased]
"""

LEDGER_TEMPLATE = """# Feature ledger

**Why this exists:** work on one feature must never quietly break or delete another.

**Rules (binding):**

1. Every commit that changes source code adds or updates the rows it affects, or says
   `[ledger: none]` (refactor, tests or tooling only).
2. Each row lists its code paths and guard tests in backticks. `records.py verify` fails when a
   listed path stops existing, so a feature cannot vanish silently.
3. No feature is removed or changed in behaviour without the owner's explicit OK, recorded in the
   row's Decided column (`<Owner> OK YYYY-MM-DD: …`). Rows are never deleted or renumbered; a
   retired feature becomes `Retired`.
4. Every bug fix adds a §2 regression row naming its guard. `[ledger: none]` never excuses a fix.
5. §3 contracts change additively only; a breaking change needs a new version and the OK first.

**Status:** `Planned`, `Live`, `Flag off`, `Broken`, `Retired`.

## 1. Feature register

| ID | What people get | Status | Code | Guard | Decided |
|---|---|---|---|---|---|

## 2. Regression log

| ID | Date | What broke | Broken by | Fixed by | Guard |
|---|---|---|---|---|---|

## 3. Contracts and backwards compatibility

| ID | Contract | Consumers | Version | Code | Guard | Decided |
|---|---|---|---|---|---|---|
"""


def ledger_path(root):
    for rel in LEDGER_NAMES:
        if (Path(root) / rel).exists():
            return rel
    return None


def ledger_rows(root):
    """[(id, status_cell, [paths])] — status is the 3rd cell (feature rows); other tables
    carry no status, so their paths are always checked."""
    rel = ledger_path(root)
    if not rel:
        return []
    rows = []
    for line in (Path(root) / rel).read_text(encoding="utf-8", errors="replace").splitlines():
        m = ROW_ID.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append((m.group(1), cells[2] if len(cells) > 2 else "", TICKED_PATH.findall(line)))
    return rows


def protected(root, paths):
    """Ledger rows whose code or guard paths include (or sit under) any of `paths`."""
    hits = []
    targets = [p.rstrip("/") for p in paths]
    for rid, status, row_paths in ledger_rows(root):
        for rp in row_paths:
            if any(rp == t or rp.startswith(t + "/") or t.startswith(rp.rstrip("/") + "/")
                   for t in targets):
                hits.append((rid, status, rp))
    return hits


def protected_paths(root):
    """Every path a live ledger row names — audits treat these as settled keeps."""
    return [p for _, status, paths in ledger_rows(root)
            if status not in UNCHECKED_STATUSES for p in paths]


def verify(root):
    return [(rid, p) for rid, status, paths in ledger_rows(root)
            if status not in UNCHECKED_STATUSES
            for p in paths if not (Path(root) / p).exists()]


def is_code(rel, code_paths=None):
    if code_paths:
        return any(rel.startswith(p) for p in code_paths)
    parts = rel.split("/")
    if any(part in NON_CODE_PARTS for part in parts[:-1]):
        return False
    return language_of(parts[-1]) is not None


def gate(root, staged, message):
    """Return the list of missing-record errors for a commit (empty = allowed)."""
    cfg = settings.load(root)
    if not cfg.get("change_records", True):
        return []
    ledger, has_changelog = ledger_path(root), (Path(root) / CHANGELOG).exists()
    if not ledger and not has_changelog:
        return []
    code_paths = cfg.get("records_code_paths") or None
    if not any(is_code(p, code_paths) for p in staged if p not in (ledger, CHANGELOG)):
        return []
    subject = next((ln.strip() for ln in message.splitlines() if ln.strip()), "").lower()
    is_fix = bool(re.search(r"\bfix(es|ed)?\b", subject))
    errors = []
    if ledger and ledger not in staged:
        if is_fix:
            errors.append(f"A fix must add a regression row to {ledger} §2 naming its guard test "
                          "([ledger: none] never applies to a fix).")
        elif "[ledger: none]" not in message:
            errors.append(f"Update {ledger} rows for the features this touches, or add "
                          "[ledger: none] to the message (refactor, tests or tooling only).")
    if has_changelog and CHANGELOG not in staged and "[changelog: none]" not in message:
        errors.append(f"Add a line under [Unreleased] in {CHANGELOG}, or add [changelog: none] "
                      "to the message.")
    return errors


def git_lines(root, *args):
    try:
        out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10)
        return [ln for ln in out.stdout.splitlines() if ln]
    except (OSError, subprocess.SubprocessError):
        return []


def commit_message(cmd, root):
    """Best-effort message from a `git commit` command line: -m/--message values, a heredoc
    body, or -F/--file contents. Unparseable → whole command (markers still searchable)."""
    heredoc = re.search(r"<<-?\s*['\"]?(\w+)['\"]?\n(.*?)\n\s*\1\b", cmd, re.S)
    if heredoc:
        return heredoc.group(2)
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return cmd
    msgs, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t in ("-m", "--message") and i + 1 < len(toks):
            msgs.append(toks[i + 1]); i += 2; continue
        if t.startswith("--message="):
            msgs.append(t.split("=", 1)[1])
        elif t.startswith("-m") and len(t) > 2:
            msgs.append(t[2:])
        elif t in ("-F", "--file") and i + 1 < len(toks):
            try:
                msgs.append((Path(root) / toks[i + 1]).read_text(encoding="utf-8"))
            except OSError:
                pass
            i += 2; continue
        i += 1
    return "\n\n".join(msgs) if msgs else cmd


def staged_for(cmd, root):
    """Files the commit will include: already staged, plus what this same command stages."""
    staged = set(git_lines(root, "diff", "--cached", "--name-only"))
    for part in re.split(r"&&|;|\n", cmd):
        try:
            toks = shlex.split(part)
        except ValueError:
            continue
        if len(toks) < 2 or toks[0] != "git":
            continue
        if toks[1] == "add":
            args = [t for t in toks[2:] if not t.startswith("-")]
            if any(t in ("-A", "--all", "-u", "--update") for t in toks[2:]) or "." in args:
                staged |= set(git_lines(root, "ls-files", "-m", "-o", "--exclude-standard"))
            staged |= set(args)
        elif toks[1] == "commit" and any(t == "--all" or re.fullmatch(r"-[a-zA-Z]*a[a-zA-Z]*", t)
                                         for t in toks[2:]):
            staged |= set(git_lines(root, "ls-files", "-m"))
    return staged


def hook():
    """PreToolUse(Bash): block a `git commit` that skips the change records. Fails open."""
    try:
        data = json.load(sys.stdin)
        cmd = (data.get("tool_input") or {}).get("command", "")
    except Exception:
        return 0
    if not re.search(r"\bgit\s+(-C\s+\S+\s+)?commit\b", cmd) or "--amend" in cmd:
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        errors = gate(root, staged_for(cmd, root), commit_message(cmd, root))
    except Exception:
        return 0
    if not errors:
        return 0
    sys.stderr.write("[shrinkage] Commit blocked — change records missing:\n  - "
                     + "\n  - ".join(errors) + "\n")
    return 2


def init(root):
    made = []
    if not (Path(root) / CHANGELOG).exists():
        (Path(root) / CHANGELOG).write_text(CHANGELOG_TEMPLATE, encoding="utf-8")
        made.append(CHANGELOG)
    if not ledger_path(root):
        p = Path(root) / LEDGER_NAMES[0]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(LEDGER_TEMPLATE, encoding="utf-8")
        made.append(LEDGER_NAMES[0])
    return made


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = os.getcwd()
    cmd = argv[0] if argv else "verify"
    if cmd == "hook":
        return hook()
    if cmd == "init":
        made = init(root)
        print("created: " + ", ".join(made) if made else "change records already set up")
        return 0
    if cmd == "check":
        msg = ""
        if "--msg" in argv and argv.index("--msg") + 1 < len(argv):
            try:
                msg = Path(argv[argv.index("--msg") + 1]).read_text(encoding="utf-8")
            except OSError:
                pass
        msg = re.sub(r"(?m)^#.*$", "", msg)
        errors = gate(root, set(git_lines(root, "diff", "--cached", "--name-only")), msg)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1 if errors else 0
    if cmd == "protected":
        for rid, status, p in protected(root, argv[1:]):
            print(f"{rid} [{status or 'contract/regression'}] {p}")
        return 0
    if cmd == "verify":
        missing = verify(root)
        for rid, p in missing:
            print(f"{rid}: {p} no longer exists")
        if not missing:
            print("ledger ok" if ledger_path(root) else "no feature ledger (records.py init)")
        return 1 if missing else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
