#!/usr/bin/env python3
"""plan — reliable edits to SHRINK-PLAN.md (open / done / restamp / carry).

The plan's conventions used to be hand-maintained by sed: striking `| ~~N~~ |`
rows, re-stamping the map fingerprint, summing est-savings, carrying rows into a
new plan. This CLI does them safely; the human-readable markdown stays the
source of truth — the CLI only edits it reliably.

  plan.py open                     list OPEN candidate rows (#id · tier · est · candidate)
  plan.py done <id> <ref> [actual] strike; resolve <ref>→sha + derive actual net
                                   LOC from git (override with [actual]); calibrate
  plan.py restamp                  refresh map-fp + recompute est-savings from open rows
  plan.py carry <old-plan>         print a new plan skeleton: open rows + a ledger pointer
"""
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PLAN_NAMES = ("SHRINK-PLAN.md", ".planning/SHRINK-PLAN.md")


def find_plan(root="."):
    for rel in PLAN_NAMES:
        p = Path(root) / rel
        if p.exists():
            return p
    sys.exit("no SHRINK-PLAN.md found (run /srk:audit first)")


def _is_row(line):
    return line.lstrip().startswith("|")


def _cells(line):
    s = line.strip().strip("|")
    return [c.strip() for c in s.split("|")]


def _colmap(lines):
    for line in lines:
        if _is_row(line):
            cells = [c.lower() for c in _cells(line)]
            if "candidate" in cells and "catalog" in cells:
                return {name: i for i, name in enumerate(cells)}
    return {}


def _rownum(cell):
    m = re.match(r"~~\s*(\d+)\s*~~$|^(\d+)$", cell.strip())
    return (m.group(1) or m.group(2)) if m else None


def _int(cell):
    m = re.search(r"-?\d+", cell.replace("−", "-"))
    return int(m.group()) if m else 0


def _iter_rows(lines):
    """Yield (idx, cells, done, in_done_section) for candidate rows only."""
    cm = _colmap(lines)
    ci = cm.get("#", 0)
    in_done = False
    for idx, line in enumerate(lines):
        h = re.match(r"^#+\s+(.+)", line)
        if h:
            in_done = h.group(1).strip().lower().startswith("done")
            continue
        if not _is_row(line):
            continue
        cells = _cells(line)
        if ci >= len(cells):
            continue
        num = _rownum(cells[ci])
        if not num:
            continue
        yield idx, cells, ("~~" in cells[ci]), in_done


def open_rows(lines):
    cm = _colmap(lines)
    out = []
    for idx, cells, done, in_done in _iter_rows(lines):
        if done or in_done:
            continue
        out.append((idx, cells, cm))
    return out


def cmd_open(root):
    plan = find_plan(root)
    lines = plan.read_text(encoding="utf-8").splitlines()
    rows = open_rows(lines)
    if not rows:
        print("no open items — plan drained (/srk:audit to rescan).")
        return
    for _, cells, cm in rows:
        g = lambda k, d="?": cells[cm[k]] if k in cm and cm[k] < len(cells) else d
        print(f"  #{_rownum(cells[cm['#']])}  {g('tier','T?'):<3}  "
              f"est {g('est. net loc', g('est', '?')):>6}  {g('candidate')}")


def _resolve_actual(ref):
    """(short_sha, net_app_LOC) for a commit-ish ref, or (None, None) if it doesn't
    resolve. Net LOC is derived exactly how diffstat scores one shave commit, so
    the calibration loop never depends on the operator passing a number by hand."""
    import subprocess
    r = subprocess.run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, None
    sha = r.stdout.strip()
    net = None
    try:
        import diffstat
        ai, ad, _t, _u = diffstat._commit_loc(sha)
        net = ai - ad
    except Exception:
        net = None
    return sha[:9], net


def cmd_done(root, ident, ref, actual=None):
    plan = find_plan(root)
    lines = plan.read_text(encoding="utf-8").splitlines()
    cm = _colmap(lines)
    ci = cm.get("#", 0)
    ev = cm.get("evidence")
    hit = None
    for idx, cells, done, _ in _iter_rows(lines):
        if _rownum(cells[ci]) == str(ident) and not done:
            hit = (idx, cells)
            break
    if not hit:
        sys.exit(f"no open item #{ident} in {plan}")
    idx, cells = hit
    # Resolve the ref to a real sha and derive the actual net LOC from git — so a
    # literal "HEAD" never freezes into the plan and calibration doesn't hinge on
    # the operator remembering the number. Deriving it now also means an amend
    # afterward can't orphan the datapoint: it's already recorded.
    sha, measured = _resolve_actual(ref)
    if sha is None:
        sha = ref
        sys.stderr.write(f"warning: '{ref}' didn't resolve to a commit — recorded as-is, "
                         "no actual derived from git.\n")
    actual_val = _int(str(actual)) if actual is not None else measured
    cells[ci] = f"~~{ident}~~"
    note = f"done {sha}" + (f", actual {actual_val:+d}" if actual_val is not None else "")
    if ev is not None and ev < len(cells):
        cells[ev] = (cells[ev] + " · " + note).strip(" ·")
    else:
        cells.append(note)
    lines[idx] = "| " + " | ".join(cells) + " |"
    plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # feed the estimate-calibration loop (P1.4) when we know the catalog + an actual
    catcell = cells[cm["catalog"]] if "catalog" in cm and cm["catalog"] < len(cells) else ""
    m = re.search(r"C\d+", catcell)
    cat = m.group() if m else None
    est = (_int(cells[cm["est. net loc"]])
           if "est. net loc" in cm and cm["est. net loc"] < len(cells) else 0)
    if cat and actual_val is not None:
        _log_calibration(root, cat, est, actual_val, sha)
    print(f"marked #{ident} done ({sha}"
          + (f", actual {actual_val:+d}" if actual_val is not None else "") + ")"
          + (" — derived from git" if actual is None and measured is not None else ""))


def _log_calibration(root, cat, est, actual, sha):
    try:
        import diffstat
        import json
        logp = diffstat.log_path(root)
        logp.parent.mkdir(parents=True, exist_ok=True)
        with logp.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "ref": sha, "net_app": int(actual), "net_test": 0, "files": 0,
                "cat": cat, "est": est}) + "\n")
    except Exception:
        pass


def _map_fp(root):
    try:
        import codemap
        mp = codemap.map_path(Path(root))
        if mp.exists():
            m = re.search(r"\| fp: (\w+)", mp.read_text(encoding="utf-8")[:2000])
            return m.group(1) if m else None
    except Exception:
        pass
    return None


def _set_comment(lines, key, value):
    pat = re.compile(rf"<!--\s*{re.escape(key)}:.*?-->")
    repl = f"<!-- {key}: {value} -->"
    for i, line in enumerate(lines):
        if pat.search(line):
            lines[i] = pat.sub(repl, line)
            return lines
    # insert after the first heading
    for i, line in enumerate(lines):
        if line.startswith("#"):
            lines.insert(i + 1, repl)
            return lines
    lines.insert(0, repl)
    return lines


def cmd_restamp(root):
    plan = find_plan(root)
    lines = plan.read_text(encoding="utf-8").splitlines()
    cm = _colmap(lines)
    total = 0
    if "est. net loc" in cm:
        for _, cells, _cm in open_rows(lines):
            total += _int(cells[cm["est. net loc"]]) if cm["est. net loc"] < len(cells) else 0
    lines = _set_comment(lines, "est-savings", total)
    fp = _map_fp(root)
    if fp:
        lines = _set_comment(lines, "map-fp", fp)
    plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"restamped: est-savings {total}"
          + (f", map-fp {fp}" if fp else " (map-fp unchanged — no map found)"))


def cmd_carry(root, old):
    src = Path(old)
    if not src.exists():
        sys.exit(f"no such plan: {old}")
    lines = src.read_text(encoding="utf-8").splitlines()
    cm = _colmap(lines)
    rows = open_rows(lines)
    print("# SHRINK-PLAN.md")
    print("<!-- map-fp: PENDING (run: plan.py restamp) -->")
    print("<!-- est-savings: PENDING -->")
    print(f"\nCarried {len(rows)} open item(s) from `{old}`. Keeps / frozen /"
          " hidden-deps live in the ledger (`references/ledger.md`), not here.\n")
    header = next((l for l in lines if _is_row(l) and "candidate" in l.lower()
                   and "catalog" in l.lower()), None)
    sep = next((l for i, l in enumerate(lines)
                if _is_row(l) and set(l.strip().strip("|")) <= set(" -:|")), None)
    if header:
        print(header)
        print(sep or "|" + "|".join(["---"] * len(_cells(header))) + "|")
    n = 0
    for _, cells, _cm in rows:
        n += 1
        cells[cm.get("#", 0)] = str(n)
        print("| " + " | ".join(cells) + " |")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd, rest = a[0], a[1:]
    root = "."
    if cmd == "open":
        cmd_open(root)
    elif cmd == "done":
        if len(rest) < 2:
            sys.exit("usage: plan.py done <id> <ref> [actual-loc]")
        cmd_done(root, rest[0], rest[1], rest[2] if len(rest) > 2 else None)
    elif cmd == "restamp":
        cmd_restamp(root)
    elif cmd == "carry":
        if not rest:
            sys.exit("usage: plan.py carry <old-plan.md>")
        cmd_carry(root, rest[0])
    else:
        sys.exit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
