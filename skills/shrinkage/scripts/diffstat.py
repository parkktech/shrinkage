#!/usr/bin/env python3
"""diffstat — the minimalism scoreboard for a change.

Usage:
  diffstat.py [REF]         score the working tree against REF (default HEAD)
  diffstat.py BASE..HEAD    score a COMMITTED range (e.g. a shave batch), so a
                            dirty working tree of unrelated work can't drown it
  diffstat.py --trend       cumulative trend + shrink streak
Flags: --pr (PR markdown block) · --log (append a trend entry) ·
       --color / --no-color (force / disable ANSI; auto-on for a TTY)

Prints a short, colored scoreboard: lines removed vs added and the net (app and
test counted separately — deleting tests never flatters the score), files,
symbols removed/added (counts, not a wall of names), and — when a SHRINK-PLAN.md
exists — how many finished items were removals / merges / cleanups.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import settings  # noqa: E402
from parsers import language_of, parse_file, parse_text  # noqa: E402

TEST_PATH = re.compile(r"(^|/)(tests?|specs?|__tests__)(/|$)|(^|[./_])(test|spec)s?[._]", re.I)
# Docs/config/lockfiles are not code — excluded so "app LOC" means code.
NON_CODE = re.compile(
    r"\.(md|markdown|rst|txt|json|ya?ml|toml|ini|cfg|conf|lock|env|csv|svg)$"
    r"|(^|/)\.gitignore$|(^|/)(\.planning|\.claude)/", re.I)

# SHRINK-PLAN catalog code -> plain-language bucket (see consolidation-catalog.md).
_BUCKET = {
    "C2": "removed", "C4": "removed", "C6": "removed",              # wrappers, flags, dead symbols
    "C1": "merged", "C5": "merged", "C7": "merged", "C9": "merged",  # dedup / consolidate
    "C3": "cleaned", "C8": "cleaned", "C10": "cleaned",            # inline / table-ify / de-noise
}

_ARGV = sys.argv[1:]
COLOR = (("--color" in _ARGV or sys.stdout.isatty())
         and "--no-color" not in _ARGV and not os.environ.get("NO_COLOR"))
GREEN, RED, YELLOW, CYAN, BOLD, DIM = "32", "31", "33", "36", "1", "2"


def col(code, s):
    return f"\033[{code}m{s}\033[0m" if COLOR else str(s)


def signed(n):
    return f"+{n}" if n >= 0 else str(n)


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def _endpoints(ref):
    """'A..B' / 'A...B' -> (A, B); a single ref -> (ref, None) meaning working tree."""
    m = re.match(r"^(.+?)\.\.\.?(.+)$", ref)
    return (m.group(1), m.group(2)) if m else (ref, None)


def collect(ref):
    base, head = _endpoints(ref)
    app_ins = app_del = test_ins = test_del = 0
    files, new_syms, removed_syms, sig_changes = [], [], [], []
    # --no-renames: a rename becomes a clean delete+add pair (path handling stays simple).
    for line in git("diff", "--numstat", "--no-renames", ref).strip().splitlines():
        add, rm, path = line.split("\t", 2)
        files.append(path)
        if add == "-":             # binary
            continue
        if NON_CODE.search(path):   # docs/config don't count as code LOC
            continue
        a, r = int(add), int(rm)
        if TEST_PATH.search(path):
            test_ins += a; test_del += r
        else:
            app_ins += a; app_del += r
    for path in files:
        if not language_of(path):
            continue
        old = {s.key(): s.signature for s in parse_text(path, git("show", f"{base}:{path}"))}
        if head is None:
            new_src = parse_file(Path(path)) if Path(path).exists() else []
        else:
            txt = git("show", f"{head}:{path}")
            new_src = parse_text(path, txt) if txt else []
        new = {s.key(): s.signature for s in new_src}

        def label(k):
            _, p, n = k
            return f"{p + '.' if p else ''}{n}"
        new_syms += [label(k) for k in new.keys() - old.keys()]
        removed_syms += [label(k) for k in old.keys() - new.keys()]
        # Zeroth Law watch: an existing symbol whose signature changed is a
        # potential compatibility break — surface it every time.
        sig_changes += [f"{label(k)} [{old[k]} -> {new[k]}]"
                        for k in old.keys() & new.keys() if old[k] != new[k]]
    return (app_ins, app_del, test_ins, test_del, files,
            sorted(new_syms), sorted(removed_syms), sorted(sig_changes))


def plan_tally(root):
    """Count finished SHRINK-PLAN items by bucket (removed / merged / cleaned).

    Best-effort: a done item is a struck row (`~~…~~`) or a row under a
    `## Done` heading that carries a `C<n>` catalog code. Returns the dict, or
    None when nothing is done yet (so the line is simply omitted)."""
    plan = root / ".planning" / "SHRINK-PLAN.md"
    if not plan.exists():
        plan = root / "SHRINK-PLAN.md"
    if not plan.exists():
        return None
    try:
        text = plan.read_text(encoding="utf-8")
    except OSError:
        return None
    buckets = {"removed": 0, "merged": 0, "cleaned": 0}
    in_done = False
    for line in text.splitlines():
        h = re.match(r"^#+\s*(.+)", line)
        if h:
            in_done = h.group(1).strip().lower().startswith("done")
            continue
        if not line.lstrip().startswith("|"):
            continue
        if not (in_done or "~~" in line):
            continue
        m = re.search(r"\bC(\d+)\b", line)
        if m and ("C" + m.group(1)) in _BUCKET:
            buckets[_BUCKET["C" + m.group(1)]] += 1
    return buckets if sum(buckets.values()) else None


def gate_ledger_check(new_syms):
    """Cross-check new symbols against recorded gate justifications (v0.8).

    Opt-in: only runs when .claude/shrinkage-gates.jsonl exists. Returns the
    new symbols with no gate record."""
    ledger = Path(".claude/shrinkage-gates.jsonl")
    if not ledger.exists():
        return None
    justified = set()
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            justified.update(json.loads(line).get("symbols", []))
        except (ValueError, AttributeError):
            continue
    short = {s.split(".")[-1] for s in justified} | justified
    return [s for s in new_syms if s not in short and s.split(".")[-1] not in short]


def scoreboard(ref, app_ins, app_del, test_ins, test_del, files,
               new_syms, removed_syms, sig_changes, root):
    net_app, net_test = app_ins - app_del, test_ins - test_del
    is_range = ".." in ref
    label = ref if is_range else f"working tree vs {ref}"
    arrow = col(GREEN, "▼") if net_app < 0 else col(YELLOW, "▲") if net_app > 0 else "·"

    print(col(BOLD, f"Shrinkage · {label}"))
    print(f"  {col(GREEN, 'removed')}  {col(GREEN, str(app_del))} lines"
          f"   {col(DIM, f'added {app_ins}')}")
    netcode = GREEN if net_app < 0 else YELLOW if net_app > 0 else DIM
    test_note = (col(GREEN, "test +0") + col(DIM, " (untouched)") if net_test == 0
                 else col(YELLOW, f"test {signed(net_test)}") + col(DIM, " (down — justify)")
                 if net_test < 0 else f"test {signed(net_test)}")
    print(f"  {arrow} net    {col(netcode, 'app ' + signed(net_app))}  ·  {test_note}")
    print(col(DIM, f"  files {len(files)}  ·  symbols "
                   f"{len(removed_syms)} removed, {len(new_syms)} added"))
    if not is_range and len(files) > 15:
        print(col(DIM, f"  ({len(files)} files dirty — to score only a committed "
                       f"shave, use  <base>..HEAD)"))

    tally = plan_tally(root)
    if tally:
        print("  " + col(CYAN, "plan") + "   " + " · ".join(
            col(GREEN, f"{tally[b]} {b}") for b in ("removed", "merged", "cleaned")))

    # Judgment flags — only when they fire.
    if sig_changes:
        print(col(YELLOW, f"  ⚠ compat-watch: {len(sig_changes)} signature change(s) — "
                          f"verify additive-only (Zeroth Law): ") + "; ".join(sig_changes[:5]))
    unjustified = gate_ledger_check(new_syms)
    if unjustified:
        print(col(YELLOW, "  ⚠ unjustified new symbols (no gate record): ")
              + ", ".join(unjustified[:8]) + " — run the gate or record via gatelog.py")
    if net_test < 0:
        print(col(YELLOW, "  ⚠ test LOC went DOWN") + " — confirm justified "
              "(safety-model §7: test deletions are never a shrink win).")

    kind = ("shrunk" if net_app < 0 else "grew" if net_app > 25
            else "flat" if (net_app == 0 and files) else None)
    q = settings.quip(".", kind, net=net_app) if kind else ""
    if q:
        print(col(DIM, "  " + q))


_SHAVE_GREP = ["--grep=^shrink:", "--grep=catalog:"]  # shave-commit markers (safety-model §6 template)


def _commit_loc(sha):
    """(app_ins, app_del, test_ins, test_del) for one commit vs its parent."""
    ai = ad = ti = td = 0
    for line in git("show", "--numstat", "--no-renames", "--format=", sha).strip().splitlines():
        if "\t" not in line:
            continue
        add, rm, path = line.split("\t", 2)
        if add == "-" or NON_CODE.search(path):
            continue
        a, r = int(add), int(rm)
        if TEST_PATH.search(path):
            ti += a; td += r
        else:
            ai += a; ad += r
    return ai, ad, ti, td


def history_total():
    """Sum EVERY shave commit in history (found by the shrink:/catalog: markers),
    with a removed/merged/cleaned tally from each commit's catalog tag. This is
    the real lifetime number — it does not depend on anyone having run --log.
    Returns the totals dict, or None when no shave commits exist."""
    shas = git("log", *_SHAVE_GREP, "--format=%H").split()
    if not shas:
        return None
    ai = ad = ti = td = 0
    buckets = {"removed": 0, "merged": 0, "cleaned": 0}
    for sha in shas:
        a, d, t, u = _commit_loc(sha)
        ai += a; ad += d; ti += t; td += u
        m = re.search(r"catalog:\s*C(\d+)", git("show", "-s", "--format=%B", sha))
        if m and ("C" + m.group(1)) in _BUCKET:
            buckets[_BUCKET["C" + m.group(1)]] += 1
    return {"n": len(shas), "app_ins": ai, "app_del": ad, "test_ins": ti,
            "test_del": td, "buckets": buckets, "first": shas[-1], "last": shas[0]}


def print_total(t=None):
    t = t if t is not None else history_total()
    if not t:
        print("no shave commits found in history (the shrink:/catalog: markers). "
              "Score a committed range instead: diffstat.py <base>..HEAD")
        return
    net_app = t["app_ins"] - t["app_del"]
    net_test = t["test_ins"] - t["test_del"]
    b = t["buckets"]
    since = git("show", "-s", "--format=%ad", "--date=short", t["first"]).strip()
    arrow = col(GREEN, "▼") if net_app < 0 else col(YELLOW, "▲") if net_app > 0 else "·"
    head = col(GREEN if net_app <= 0 else YELLOW, f"app {net_app:+,} LOC")
    print(col(BOLD, "Shrinkage lifetime") + col(DIM, f" · {t['n']} shave commits · since {since}"))
    print(f"  {arrow} {head}   " + col(DIM, f"{t['app_del']:,} removed / {t['app_ins']:,} added"))
    print("  " + col(CYAN, "by type") + "  "
          + " · ".join(col(GREEN, f"{b[k]} {k}") for k in ("removed", "merged", "cleaned"))
          + col(DIM, f"   · tests {net_test:+,}"))


def show_trend():
    total = history_total()
    print_total(total)
    dep = Path("DEPRECATIONS.md")
    if dep.exists():
        pending = sum(1 for l in dep.read_text(encoding="utf-8").splitlines()
                      if l.strip().startswith("- [ ]"))
        if pending:
            print(col(YELLOW, f"  deprecation shims pending removal: {pending} (DEPRECATIONS.md)"))
    if total and (total["app_ins"] - total["app_del"]) < 0:
        q = settings.quip(".", "shrunk", net=total["app_ins"] - total["app_del"])
        if q:
            print(col(DIM, "  " + q))


def main():
    argv = sys.argv[1:]
    if "--trend" in argv:
        show_trend()
        return
    if "--total" in argv:
        print_total()
        return
    pos = [a for a in argv if not a.startswith("--")]
    ref = pos[0] if pos else "HEAD"
    root = Path(".")
    (app_ins, app_del, test_ins, test_del, files,
     new_syms, removed_syms, sig_changes) = collect(ref)
    net_app, net_test = app_ins - app_del, test_ins - test_del

    scoreboard(ref, app_ins, app_del, test_ins, test_del, files,
               new_syms, removed_syms, sig_changes, root)

    if "--pr" in argv or settings.load(".")["pr_scoreboard"]:
        print("\n--- PR description block ---")
        print("### Code minimalism scoreboard\n")
        print("| removed | added | net app | net test | files | symbols removed |")
        print("|---|---|---|---|---|---|")
        print(f"| {app_del} | {app_ins} | {signed(net_app)} | {signed(net_test)} "
              f"| {len(files)} | {len(removed_syms)} |")

    if "--log" in argv:
        logp = Path(".claude/shrinkage-log.jsonl")
        logp.parent.mkdir(parents=True, exist_ok=True)
        with logp.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "ref": ref, "net_app": net_app, "net_test": net_test,
                "files": len(files), "new": new_syms, "removed": removed_syms,
            }) + "\n")
        print(f"logged to {logp}")


if __name__ == "__main__":
    main()
