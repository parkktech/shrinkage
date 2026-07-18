#!/usr/bin/env python3
"""diffstat — the minimalism scoreboard for a change.

Usage:
  diffstat.py [REF]         score the working tree against REF (default HEAD)
  diffstat.py BASE..HEAD    score a COMMITTED range (e.g. a shave batch), so a
                            dirty working tree of unrelated work can't drown it
  diffstat.py BASE..HEAD --shave-only   score ONLY the shave/fix commits in a
                            range (subjects matching shrink:/fix:), and show the
                            whole-range delta so entanglement stays visible
  diffstat.py --trend       cumulative trend + shrink streak
Flags: --pr (PR markdown block) · --log (append a trend entry) ·
       --shave-only / --prefix shrink:,fix: (range: matched commits only) ·
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
from parsers import language_of, parse_text  # noqa: E402

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


def _nonpublic(name, path, *texts):
    """True when the symbol is non-public in EVERY text — its signature change
    is internal refactoring, not a compatibility concern (the `estimateFees`
    false positive). Per language family:
    - keyword languages (PHP/Java/C#/Kotlin/TS): explicit private/protected on
      the declaration, with no same-name public declaration in the file;
    - Go: unexported = lowercase (or _) initial;
    - Rust: `fn` with no `pub` on any declaration of the name.
    Conservative on purpose: public, ambiguous, or convention-only visibility
    (Python underscores) → False, the warning stays."""
    ext = Path(path).suffix.lower()
    if ext == ".go":
        return bool(name) and (name[0].islower() or name[0] == "_")
    if ext == ".rs":
        anyfn = re.compile(r"^[^\n]*\bfn\s+" + re.escape(name) + r"\s*[<(]", re.M)
        pubfn = re.compile(r"^[^\n]*\bpub\b[^\n]*\bfn\s+" + re.escape(name) + r"\s*[<(]", re.M)
        return all(t and anyfn.search(t) and not pubfn.search(t) for t in texts)
    priv = re.compile(r"\b(?:private|protected)\b[^;{}\n]*?\b" + re.escape(name) + r"\s*\(")
    pub = re.compile(r"\bpublic\b[^;{}\n]*?\b" + re.escape(name) + r"\s*\(")
    return all(t and priv.search(t) and not pub.search(t) for t in texts)


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
        old_txt = git("show", f"{base}:{path}")
        old = {s.key(): s.signature for s in parse_text(path, old_txt)}
        if head is None:
            p = Path(path)
            new_txt = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        else:
            new_txt = git("show", f"{head}:{path}")
        new = {s.key(): s.signature
               for s in (parse_text(path, new_txt) if new_txt else [])}

        def label(k):
            _, p, n = k
            return f"{p + '.' if p else ''}{n}"
        new_syms += [label(k) for k in new.keys() - old.keys()]
        removed_syms += [label(k) for k in old.keys() - new.keys()]
        # Zeroth Law watch: an existing symbol whose signature changed is a
        # potential compatibility break — surface it, UNLESS the symbol is
        # explicitly private/protected on both sides (internal, not compat).
        sig_changes += [f"{label(k)} [{old[k]} -> {new[k]}]"
                        for k in old.keys() & new.keys()
                        if old[k] != new[k] and not _nonpublic(k[2], path, old_txt, new_txt)]
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
               new_syms, removed_syms, sig_changes, root, label=None):
    net_app, net_test = app_ins - app_del, test_ins - test_del
    is_range = ".." in ref
    if label is None:
        if is_range:
            n = git("rev-list", "--count", ref).strip() or "?"
            label = f"{n} commit{'' if n == '1' else 's'} · {ref}"
        else:
            label = f"working tree (uncommitted) vs {ref}"
    arrow = col(GREEN, "▼") if net_app < 0 else col(YELLOW, "▲") if net_app > 0 else "·"

    direction = (col(GREEN, "▼ smaller") if net_app < 0
                 else col(YELLOW, "▲ larger") if net_app > 0 else col(DIM, "no change"))
    netcode = GREEN if net_app < 0 else YELLOW if net_app > 0 else DIM

    print(col(BOLD, f"Shrinkage · {label}"))
    print("  code removed        " + col(GREEN, f"{app_del:>6,} lines"))
    print("  code added          " + col(DIM, f"{app_ins:>6,} lines"))
    print("  net change          " + col(netcode, f"{net_app:>+6,} lines") + "   " + direction)
    print(f"  files changed       {len(files):>6,}")
    print("  definitions removed " + col(GREEN, f"{len(removed_syms):>6,}")
          + col(DIM, "   (functions, methods, classes)"))
    print(f"  definitions added   {len(new_syms):>6,}")
    if not is_range and len(files) > 15:
        print(col(DIM, f"  (scoring the whole working tree — {len(files)} files dirty; to score "
                       f"just one committed shave use  <base>..HEAD)"))

    tally = plan_tally(root)
    if tally:
        print("  " + col(CYAN, "cleared from your SHRINK-PLAN:"))
        for key, text in (("removed", "dead-code removals"), ("merged", "duplicate merges"),
                          ("cleaned", "cleanups")):
            if tally[key]:
                print("    " + col(GREEN, f"{tally[key]:>3}") + f" {text}")

    print("  test code           " + col(YELLOW if net_test < 0 else DIM, f"{net_test:>+6,} lines")
          + (col(YELLOW, "   ⚠ shrank — see below") if net_test < 0 else ""))

    # Plain-language things to check before shipping — only when they fire.
    warns = []
    if sig_changes:
        names = ", ".join(s.split(" [")[0] for s in sig_changes[:6])
        more = f" (+{len(sig_changes) - 6} more)" if len(sig_changes) > 6 else ""
        warns.append(f"{len(sig_changes)} public method signature(s) changed — make sure "
                     f"everything that calls them still works: {names}{more}")
    unjustified = gate_ledger_check(new_syms)
    if unjustified:
        warns.append(f"new code with no reuse-gate record: {', '.join(unjustified[:8])} — "
                     f"run the gate to confirm it couldn't extend something that already exists")
    if net_test < 0:
        warns.append(f"test code shrank {abs(net_test)} lines — confirm that was intentional "
                     f"(deleting tests can quietly drop coverage)")
    if warns:
        print(col(YELLOW, "  ⚠ check before you ship:"))
        for w in warns:
            print(col(YELLOW, "    · ") + w)

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
    print(col(BOLD, "Shrinkage — lifetime cleanup"))
    print("  net change        " + col(GREEN if net_app <= 0 else YELLOW, f"{net_app:>+8,} lines")
          + (col(GREEN, "   ▼ smaller") if net_app < 0 else ""))
    print("  code removed      " + col(GREEN, f"{t['app_del']:>8,} lines"))
    print(f"  shave commits     {t['n']:>8,}" + col(DIM, f"   since {since}"))
    print("  " + col(CYAN, "by type:"))
    for key, text in (("removed", "dead-code removals"), ("merged", "duplicate merges"),
                      ("cleaned", "cleanups")):
        print("    " + col(GREEN, f"{b[key]:>3}") + f" {text}")
    print(f"  test code         {net_test:>+8,} lines")


def _matched_shas(ref, prefixes):
    """SHAs in the range whose SUBJECT starts with one of the prefixes (e.g.
    'shrink:', 'fix:') — the shave/fix commit templates."""
    out = []
    for line in git("log", "--format=%H%x1f%s", ref).splitlines():
        if "\x1f" not in line:
            continue
        sha, subj = line.split("\x1f", 1)
        if any(subj.startswith(p) for p in prefixes):
            out.append(sha)
    return out


def collect_commits(shas):
    """Aggregate LOC + symbol deltas across a SPECIFIC set of commits (each vs its
    parent), rather than a start..end range. Lets --shave-only score only the
    matching commits even when non-shave commits are interleaved in the range.
    Returns the same 8-tuple shape as collect()."""
    app_ins = app_del = test_ins = test_del = 0
    files, new_syms, removed_syms, sig_changes = set(), [], [], []

    def label(k):
        _, p, n = k
        return f"{p + '.' if p else ''}{n}"

    for sha in shas:
        for line in git("show", "--numstat", "--no-renames", "--format=", sha).strip().splitlines():
            if "\t" not in line:
                continue
            add, rm, path = line.split("\t", 2)
            files.add(path)
            if add == "-":
                continue
            if not NON_CODE.search(path):
                a, r = int(add), int(rm)
                if TEST_PATH.search(path):
                    test_ins += a; test_del += r
                else:
                    app_ins += a; app_del += r
            if not language_of(path):
                continue
            old_txt = git("show", f"{sha}^:{path}")
            new_txt = git("show", f"{sha}:{path}")
            old = {s.key(): s.signature for s in parse_text(path, old_txt)}
            new = {s.key(): s.signature for s in parse_text(path, new_txt)}
            new_syms += [label(k) for k in new.keys() - old.keys()]
            removed_syms += [label(k) for k in old.keys() - new.keys()]
            sig_changes += [f"{label(k)} [{old[k]} -> {new[k]}]"
                            for k in old.keys() & new.keys()
                            if old[k] != new[k] and not _nonpublic(k[2], path, old_txt, new_txt)]
    return (app_ins, app_del, test_ins, test_del, sorted(files),
            sorted(new_syms), sorted(removed_syms), sorted(sig_changes))


def shave_only_board(ref, prefixes, root):
    """--shave-only / --prefix: score ONLY the commits in a range whose subject
    matches the shave/fix templates, then show the whole-range delta so any
    entanglement (non-shave work mixed into the range) stays visible, not hidden."""
    _, head = _endpoints(ref)
    if head is None:
        print("--shave-only needs a committed range (e.g. <base>..HEAD); a "
              "working-tree diff has no commits to filter.")
        return
    all_shas = git("rev-list", ref).split()
    matched = _matched_shas(ref, prefixes)
    off = [s for s in all_shas if s not in set(matched)]
    board = collect_commits(matched)
    joined = ",".join(prefixes)
    scoreboard(ref, *board, root,
               label=f"shave-only · {len(matched)} of {len(all_shas)} commits match {joined}")
    m_net = board[0] - board[1]
    if off:
        oi = od = 0
        for s in off:
            a, d, _t, _u = _commit_loc(s)
            oi += a; od += d
        off_net = oi - od
        print("  " + col(YELLOW, "entanglement check"))
        print(f"    {len(off)} of {len(all_shas)} commits are not {joined}"
              + col(YELLOW, f"   {off_net:+,} app lines") + " from other work")
        print(col(DIM, f"    whole range = shave {m_net:+,} + other {off_net:+,} "
                       f"= {m_net + off_net:+,} lines"))
    else:
        print(col(DIM, "  all commits in the range matched — no non-shave entanglement"))


def _optval(argv, name):
    return (argv[argv.index(name) + 1]
            if name in argv and argv.index(name) + 1 < len(argv) else None)


def _positionals(argv, valued):
    skip = set()
    for name in valued:
        if name in argv:
            i = argv.index(name)
            skip.update({i, i + 1})
    return [a for j, a in enumerate(argv) if not a.startswith("--") and j not in skip]


def _git_dir(root="."):
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--git-dir"],
                           capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    d = r.stdout.strip()
    return Path(d) if os.path.isabs(d) else Path(root) / d


def log_path(root="."):
    """Kept in the git common dir — NOT in the working tree, so it can't block a
    `git checkout` during recovery or get swept into a commit. Off-git: .claude/."""
    gd = _git_dir(root)
    return (gd / "info" / "shrinkage-log.jsonl") if gd else Path(root) / ".claude" / "shrinkage-log.jsonl"


def _migrate_log(root="."):
    new = log_path(root)
    old = Path(root) / ".claude" / "shrinkage-log.jsonl"
    if old.exists() and old.resolve() != new.resolve():
        new.parent.mkdir(parents=True, exist_ok=True)
        with new.open("a", encoding="utf-8") as fh:
            fh.write(old.read_text(encoding="utf-8"))
        old.unlink()


def read_log(root="."):
    _migrate_log(root)
    p = log_path(root)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def realization(entries):
    """Per-catalog est-vs-actual: {cat: (est_sum, actual_sum, factor, n)}. Only
    entries carrying a `cat` + non-zero `est` (recorded at shave time) count."""
    agg = {}
    for e in entries:
        cat, est = e.get("cat"), e.get("est")
        if not cat or not est:
            continue
        es, ac, n = agg.get(cat, (0, 0, 0))
        agg[cat] = (es + abs(est), ac + abs(e.get("net_app", 0)), n + 1)
    return {c: (es, ac, (ac / es if es else 0.0), n) for c, (es, ac, n) in agg.items()}


def show_trend():
    total = history_total()
    print_total(total)
    real = realization(read_log())
    if real:
        print("  " + col(CYAN, "estimate realization") + col(DIM, " (actual ÷ estimate):"))
        for c in sorted(real):
            es, ac, f, n = real[c]
            print(col(DIM, f"    {c}: {round(f * 100)}%  ({ac} actual / {es} est, {n} shaves)"))
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
    pos = _positionals(argv, {"--cat", "--est", "--prefix"})
    ref = pos[0] if pos else "HEAD"
    root = Path(".")
    if "--shave-only" in argv or "--prefix" in argv:
        prefixes = [p.strip() for p in (_optval(argv, "--prefix") or "shrink:,fix:").split(",")
                    if p.strip()]
        shave_only_board(ref, prefixes, root)
        return
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
        entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "ref": ref, "net_app": net_app, "net_test": net_test,
                 "files": len(files), "new": new_syms, "removed": removed_syms}
        cat, est = _optval(argv, "--cat"), _optval(argv, "--est")
        if cat:
            entry["cat"] = cat
        if est is not None:
            try:
                entry["est"] = int(est)
            except ValueError:
                pass
        _migrate_log()
        logp = log_path()
        logp.parent.mkdir(parents=True, exist_ok=True)
        with logp.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        print(f"logged to {logp}" + (f" (cat {cat}, est {est})" if cat else ""))


if __name__ == "__main__":
    main()
