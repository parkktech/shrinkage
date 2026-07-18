#!/usr/bin/env python3
"""plan — reliable edits to SHRINK-PLAN.md (open / done / restamp / carry).

The plan's conventions used to be hand-maintained by sed: striking `| ~~N~~ |`
rows, re-stamping the map fingerprint, summing est-savings, carrying rows into a
new plan. This CLI does them safely; the human-readable markdown stays the
source of truth — the CLI only edits it reliably.

  plan.py open                     list OPEN candidate rows (#id · tier · est · candidate)
  plan.py done <id> <ref> [actual] strike; resolve <ref>→sha + derive actual net
                                   LOC from git (override with [actual]); calibrate.
                                   <id> may be a deferred row: `done D-30 HEAD`
  plan.py restamp                  refresh map-fp + recompute est-savings from open rows
  plan.py carry <old-plan>         print a new plan skeleton: open rows + a ledger pointer
  plan.py verify-gates [--runner CMD]  run every open row's named gate suite in its
                                   OWN process; stamp green / RED / 0-ASSERT /
                                   SKIPPED into the row (exit 1 on RED/0-ASSERT)
  plan.py todo-check <n|text>      tick the nth (or matching) `- [ ]` item under
                                   `## TODO before shaving`
  plan.py adjudicate <D-id> "<ruling>"  record the operator's ruling on a ⚖ row
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


def _find_deferred(lines, ident):
    """Line index of a deferred-table row `| D-30 | …` (struck or not)."""
    num = re.sub(r"(?i)^d-?", "", str(ident))
    pat = re.compile(r"^\|\s*(?:~~\s*)?[Dd]-?" + re.escape(num) + r"(?:\s*~~)?\s*\|")
    for idx, line in enumerate(lines):
        if pat.match(line.strip()):
            return idx
    return None


def _done_deferred(root, ident, ref, actual=None):
    """Strike + annotate a deferred (`D-##`) row — they live in their own table
    (id | candidate | est | why), which the main-table colmap can't see."""
    plan = find_plan(root)
    lines = plan.read_text(encoding="utf-8").splitlines()
    idx = _find_deferred(lines, ident)
    if idx is None:
        sys.exit(f"no deferred row {ident} in {plan}")
    sha, measured = _resolve_actual(ref)
    if sha is None:
        sha = ref
    actual_val = _int(str(actual)) if actual is not None else measured
    cells = _cells(lines[idx])
    if "~~" in cells[0]:
        sys.exit(f"{ident} is already struck")
    cells[0] = f"~~{cells[0]}~~"
    note = f"done {sha}" + (f", actual {actual_val:+d}" if actual_val is not None else "")
    cells[-1] = (cells[-1] + " · " + note).strip(" ·")
    lines[idx] = "| " + " | ".join(cells) + " |"
    plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
    m = re.search(r"C\d+", lines[idx])
    est = _int(cells[2]) if len(cells) > 2 else 0
    if m and actual_val is not None:
        _log_calibration(root, m.group(), est, actual_val, sha)
    print(f"marked {cells[0]} done ({sha}"
          + (f", actual {actual_val:+d}" if actual_val is not None else "") + ")")


def cmd_todo_check(root, which):
    """Tick one `- [ ]` under `## TODO before shaving` (by 1-based number or
    substring match); prints how many remain — the shave's TODO gate reads this."""
    plan = find_plan(root)
    lines = plan.read_text(encoding="utf-8").splitlines()
    in_todo, boxes = False, []
    for idx, line in enumerate(lines):
        if re.match(r"^#+\s", line):
            in_todo = line.lower().lstrip("#").strip().startswith("todo before shaving")
            continue
        if in_todo and re.match(r"^\s*-\s*\[ \]", line):
            boxes.append(idx)
    if not boxes:
        sys.exit("no unchecked TODO items (gate already clear, or no TODO section)")
    hit = None
    if str(which).isdigit():
        n = int(which)
        if 1 <= n <= len(boxes):
            hit = boxes[n - 1]
    else:
        hit = next((i for i in boxes if str(which).lower() in lines[i].lower()), None)
    if hit is None:
        sys.exit(f"no unchecked TODO item matching '{which}' ({len(boxes)} open)")
    lines[hit] = re.sub(r"-\s*\[ \]", "- [x]", lines[hit], count=1)
    plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
    left = len(boxes) - 1
    print(f"checked: {lines[hit].strip()[:70]}")
    print(f"TODO gate: {left} item(s) remaining" if left else "TODO gate: CLEAR — shave unblocked")


def cmd_adjudicate(root, ident, ruling):
    """Record the operator's ruling on a deferred ⚖ row, durably, in the row."""
    plan = find_plan(root)
    lines = plan.read_text(encoding="utf-8").splitlines()
    idx = _find_deferred(lines, ident)
    if idx is None:
        sys.exit(f"no deferred row {ident} in {plan}")
    cells = _cells(lines[idx])
    day = datetime.now(timezone.utc).date().isoformat()
    cells[-1] = (cells[-1] + f" · ⚖ ruled {day}: {ruling}").strip(" ·")
    lines[idx] = "| " + " | ".join(cells) + " |"
    plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"recorded ruling on {cells[0]}: {ruling}")


_SUITE_TOKEN = re.compile(r"[\w./-]*tests?/[\w./-]+\.(?:php|py)|[\w./-]+Test\.php")


def _classify_run(rc, out):
    """Map a test-runner's output to green / RED / 0-ASSERT / SKIPPED."""
    if re.search(r"ERRORS!|FAILURES!|Errors:\s*[1-9]|Failures:\s*[1-9]|\d+ (?:failed|errors?)\b", out):
        return "RED"
    if re.search(r"Assertions:\s*0\b|\b0 assertions\b", out):
        return "0-ASSERT"
    if re.search(r"No tests executed|no tests ran|OK, but some tests were skipped", out, re.I):
        return "SKIPPED"
    if rc == 0 and re.search(r"\bOK \(|\d+ passed", out):
        return "green"
    return "RED" if rc != 0 else "SKIPPED"


def cmd_verify_gates(root, runner=None):
    """Run every OPEN row's named gate suite(s), each in its OWN process (three
    suites green individually can error together — process pollution), and stamp
    the ACTUAL color into the row. A named gate nobody ran is how a red suite
    guarding live-money code gets recorded as green (the row-9 incident)."""
    import shlex
    import subprocess
    plan = find_plan(root)
    lines = plan.read_text(encoding="utf-8").splitlines()
    cm = _colmap(lines)
    cov = cm.get("coverage")
    if cov is None:
        sys.exit("plan has no coverage column — nothing to verify")
    if not runner:
        for cand in ("vendor/bin/phpunit", "vendor/bin/pest"):
            if (Path(root) / cand).exists():
                runner = cand
                break
        else:
            runner = f"{sys.executable} -m pytest"
    day = datetime.now(timezone.utc).date().isoformat()
    worst_bad = False
    results = {}
    for idx, cells, done, in_done in _iter_rows(lines):
        if done or in_done or cov >= len(cells):
            continue
        suites = sorted(set(_SUITE_TOKEN.findall(cells[cov])))
        if not suites:
            continue
        statuses = []
        for s in suites:
            if s in results:
                statuses.append(results[s][0])
                continue
            try:
                r = subprocess.run([*shlex.split(runner), s], capture_output=True,
                                   text=True, cwd=root, timeout=600)
                status = _classify_run(r.returncode, r.stdout + r.stderr)
            except (OSError, subprocess.SubprocessError):
                status = "RED"
            results[s] = (status, s)
            statuses.append(status)
            print(f"  {s} → {status}")
        agg = ("RED" if "RED" in statuses else
               "0-ASSERT" if "0-ASSERT" in statuses else
               "SKIPPED" if "SKIPPED" in statuses else "green")
        worst_bad = worst_bad or agg in ("RED", "0-ASSERT")
        cells[cov] = re.sub(r"\s*·\s*verified:[^|]*$", "", cells[cov]).strip()
        cells[cov] += f" · verified: {agg} {day}"
        lines[idx] = "| " + " | ".join(cells) + " |"
    plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("gate verification stamped into the plan"
          + (" — ⚠ RED/0-ASSERT gates found: repair-first, do not shave those rows"
             if worst_bad else " — all named gates green"))
    sys.exit(1 if worst_bad else 0)


def cmd_done(root, ident, ref, actual=None):
    if re.fullmatch(r"(?i)d-?\d+", str(ident)):
        return _done_deferred(root, ident, ref, actual)
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
    elif cmd == "verify-gates":
        runner = rest[rest.index("--runner") + 1] if "--runner" in rest else None
        cmd_verify_gates(root, runner)
    elif cmd == "todo-check":
        if not rest:
            sys.exit("usage: plan.py todo-check <n | text-match>")
        cmd_todo_check(root, rest[0])
    elif cmd == "adjudicate":
        if len(rest) < 2:
            sys.exit('usage: plan.py adjudicate <D-id> "<ruling>"')
        cmd_adjudicate(root, rest[0], " ".join(rest[1:]))
    else:
        sys.exit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
