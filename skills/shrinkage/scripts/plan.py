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
  plan.py todo-check <n|text> [...]|--all   tick TODO-gate items (one, several,
                                   or all) under `## TODO before shaving`
  plan.py adjudicate <D-id> "<ruling>"  record the operator's ruling on a ⚖ row
  plan.py bug-done <B-id> <ref>    strike a `## Bugs found` table row (fix landed)
  plan.py failset record|compare -- <suite cmd…>   identical-failure-set gate for
                                   permanently-red corners: record the exact
                                   failing names, later require the same set
"""
import json
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
    _text0 = plan.read_text(encoding="utf-8")
    _ext_check(root, plan, _text0)
    lines = _text0.splitlines()
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


def _find_labeled(lines, ident):
    """Line index of a labeled table row (`| D-30 |`, `| B-2 |`…), struck or not."""
    m = re.fullmatch(r"(?i)([a-z])-?(\d+)", str(ident))
    if not m:
        return None
    letter, num = m.group(1), m.group(2)
    pat = re.compile(r"^\|\s*(?:~~\s*)?[" + letter.upper() + letter.lower() +
                     r"]-?" + num + r"(?:\s*~~)?\s*\|")
    for idx, line in enumerate(lines):
        if pat.match(line.strip()):
            return idx
    return None


_find_deferred = _find_labeled  # deferred rows are the original labeled case


def _done_deferred(root, ident, ref, actual=None):
    """Strike + annotate a deferred (`D-##`) row — they live in their own table
    (id | candidate | est | why), which the main-table colmap can't see."""
    plan = find_plan(root)
    _text0 = plan.read_text(encoding="utf-8")
    _ext_check(root, plan, _text0)
    lines = _text0.splitlines()
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
    _new = "\n".join(lines) + "\n"
    plan.write_text(_new, encoding="utf-8")
    _stamp(root, _new)
    m = re.search(r"C\d+", lines[idx])
    est = _int(cells[2]) if len(cells) > 2 else 0
    if m and actual_val is not None:
        _log_calibration(root, m.group(), est, actual_val, sha)
    print(f"marked {cells[0]} done ({sha}"
          + (f", actual {actual_val:+d}" if actual_val is not None else "") + ")")


def cmd_todo_check(root, whiches):
    """Tick `- [ ]` items under `## TODO before shaving` — by 1-based number,
    substring match, several at once, or `--all`. Prints how many remain (the
    shave's TODO gate reads this). Numbers refer to the ORIGINAL unchecked
    order, so `todo-check 1 3` means the 1st and 3rd open items."""
    plan = find_plan(root)
    _text0 = plan.read_text(encoding="utf-8")
    _ext_check(root, plan, _text0)
    lines = _text0.splitlines()
    in_todo, boxes = False, []
    for idx, line in enumerate(lines):
        if re.match(r"^#+\s", line):
            in_todo = line.lower().lstrip("#").strip().startswith("todo before shaving")
            continue
        if in_todo and re.match(r"^\s*-\s*\[ \]", line):
            boxes.append(idx)
    if not boxes:
        sys.exit("no unchecked TODO items (gate already clear, or no TODO section)")
    if "--all" in whiches:
        hits = list(boxes)
    else:
        hits = []
        for which in whiches:
            if str(which).isdigit() and 1 <= int(which) <= len(boxes):
                hits.append(boxes[int(which) - 1])
            else:
                m = next((i for i in boxes if str(which).lower() in lines[i].lower()), None)
                if m is None:
                    sys.exit(f"no unchecked TODO item matching '{which}' "
                             f"({len(boxes)} open — nothing was checked)")
                hits.append(m)
    for hit in dict.fromkeys(hits):
        lines[hit] = re.sub(r"-\s*\[ \]", "- [x]", lines[hit], count=1)
        print(f"checked: {lines[hit].strip()[:70]}")
    _new = "\n".join(lines) + "\n"
    plan.write_text(_new, encoding="utf-8")
    _stamp(root, _new)
    left = len(boxes) - len(dict.fromkeys(hits))
    print(f"TODO gate: {left} item(s) remaining" if left else "TODO gate: CLEAR — shave unblocked")


def cmd_adjudicate(root, ident, ruling):
    """Record the operator's ruling on a deferred ⚖ row, durably, in the row."""
    plan = find_plan(root)
    _text0 = plan.read_text(encoding="utf-8")
    _ext_check(root, plan, _text0)
    lines = _text0.splitlines()
    idx = _find_deferred(lines, ident)
    if idx is None:
        sys.exit(f"no deferred row {ident} in {plan}")
    cells = _cells(lines[idx])
    day = datetime.now(timezone.utc).date().isoformat()
    cells[-1] = (cells[-1] + f" · ⚖ ruled {day}: {ruling}").strip(" ·")
    lines[idx] = "| " + " | ".join(cells) + " |"
    _new = "\n".join(lines) + "\n"
    plan.write_text(_new, encoding="utf-8")
    _stamp(root, _new)
    print(f"recorded ruling on {cells[0]}: {ruling}")


_SUITE_TOKEN = re.compile(
    r"[\w./-]*tests?/[\w./-]+\.(?:php|py)"          # tests/**.php|py
    r"|[\w./-]+Tests?\.(?:php|java|kt|cs)"          # FooTest.java / FooTests.cs …
    r"|[\w./-]+_test\.go"                           # foo_test.go
    r"|[\w./-]+\.(?:test|spec)\.[cm]?[jt]sx?"       # foo.test.ts / foo.spec.js
)


def _detect_runner(root):
    """One runner per repo, by build-system marker — --runner overrides."""
    r = Path(root)
    for cand in ("vendor/bin/phpunit", "vendor/bin/pest"):
        if (r / cand).exists():
            return cand
    if (r / "gradlew").exists():
        return "./gradlew test --tests"
    if (r / "go.mod").exists():
        return "go test"
    if (r / "Cargo.toml").exists():
        return "cargo test"
    if list(r.glob("*.sln")) or list(r.glob("*.csproj")):
        return "dotnet test --filter"
    if (r / "package.json").exists():
        return "npm test --"
    return f"{sys.executable} -m pytest"


def _suite_arg(runner, token):
    """Adapt a suite token to the runner's addressing scheme."""
    if "gradlew" in runner or "--filter" in runner:
        return Path(token).stem                     # class name / filter term
    if runner.startswith("go test"):
        d = str(Path(token).parent)
        return "./" + d if d not in (".", "") else "./..."
    if runner.startswith("cargo test"):
        return Path(token).stem
    return token


def _classify_run(rc, out):
    """Map a test-runner's output to green / RED / 0-ASSERT / SKIPPED —
    phpunit/pest, pytest, jest/vitest, go test, cargo, gradle, dotnet."""
    if re.search(r"ERRORS!|FAILURES!|Errors:\s*[1-9]|Failures:\s*[1-9]"
                 r"|[1-9]\d* (?:failed|errors?)\b|--- FAIL|^FAIL\b|BUILD FAILED"
                 r"|test result: FAILED|Failed!", out, re.M):
        return "RED"
    if re.search(r"Assertions:\s*0\b|\b0 assertions\b", out):
        return "0-ASSERT"
    if re.search(r"No tests executed|no tests ran|no test files|no tests found"
                 r"|OK, but some tests were skipped", out, re.I):
        return "SKIPPED"
    if rc == 0 and re.search(r"\bOK \(|\d+ passed|\d+ passing|^ok\b"
                             r"|test result: ok|BUILD SUCCESSFUL|Passed!", out, re.M):
        return "green"
    return "RED" if rc != 0 else "SKIPPED"


_FAIL_RES = [
    re.compile(r"^\d+\)\s+([\w\\]+::\w+)", re.M),       # phpunit/pest: "1) Class::test"
    re.compile(r"^FAILED\s+(\S+)", re.M),                # pytest: "FAILED tests/x.py::t"
    re.compile(r"--- FAIL:\s+(\S+)", re.M),              # go test
]


def cmd_failset(root, mode, cmdline):
    """Identical-failure-set gate for PERMANENTLY-RED corners (safety-model §4):
    `record` captures the exact failing-test names of a known-red suite;
    `compare` re-runs and requires the EXACT same set — new failures mean your
    transform broke something even though the suite was already red."""
    import hashlib
    import shlex
    import subprocess
    if not cmdline:
        sys.exit("usage: plan.py failset record|compare -- <suite command…>")
    if isinstance(cmdline, str):
        cmdline = shlex.split(cmdline)
    try:
        r = subprocess.run(cmdline, capture_output=True, text=True, cwd=root, timeout=1800)
    except (OSError, subprocess.SubprocessError) as e:
        sys.exit(f"suite command failed to run: {e}")
    out = r.stdout + r.stderr
    names = sorted({m for rx in _FAIL_RES for m in rx.findall(out)})
    key = hashlib.sha1(" ".join(cmdline).encode()).hexdigest()[:12]
    fp = _plan_stamp_path(root).parent / "srk-failset.json"
    data = {}
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if mode == "record":
        data[key] = {"cmd": " ".join(cmdline), "failing": names}
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        print(f"recorded failure set: {len(names)} known-red test(s) for `{' '.join(cmdline)}`")
        for n in names:
            print(f"  ✗ {n}")
        return
    base = data.get(key)
    if base is None:
        sys.exit("no recorded baseline for this exact command — `failset record` first.")
    old, new = set(base["failing"]), set(names)
    added, gone = sorted(new - old), sorted(old - new)
    if not added and not gone:
        print(f"IDENTICAL failure set ({len(new)} known-red) — the permanently-red "
              "corner is unchanged; your transform introduced nothing new.")
        return
    if added:
        print("NEW failures (your transform likely broke these):")
        for n in added:
            print(f"  + {n}")
    if gone:
        print("VANISHED failures (fixed — or no longer running; verify WHICH):")
        for n in gone:
            print(f"  - {n}")
    sys.exit(1)


def cmd_verify_gates(root, runner=None):
    """Run every OPEN row's named gate suite(s), each in its OWN process (three
    suites green individually can error together — process pollution), and stamp
    the ACTUAL color into the row. A named gate nobody ran is how a red suite
    guarding live-money code gets recorded as green (the row-9 incident)."""
    import shlex
    import subprocess
    plan = find_plan(root)
    _text0 = plan.read_text(encoding="utf-8")
    _ext_check(root, plan, _text0)
    lines = _text0.splitlines()
    cm = _colmap(lines)
    cov = cm.get("coverage")
    if cov is None:
        sys.exit("plan has no coverage column — nothing to verify")
    if not runner:
        runner = _detect_runner(root)
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
                r = subprocess.run([*shlex.split(runner), _suite_arg(runner, s)],
                                   capture_output=True, text=True, cwd=root, timeout=600)
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
    _new = "\n".join(lines) + "\n"
    plan.write_text(_new, encoding="utf-8")
    _stamp(root, _new)
    print("gate verification stamped into the plan"
          + (" — ⚠ RED/0-ASSERT gates found: repair-first, do not shave those rows"
             if worst_bad else " — all named gates green"))
    sys.exit(1 if worst_bad else 0)


def _plan_stamp_path(root):
    import subprocess
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--git-dir"],
                       capture_output=True, text=True)
    gd = Path(r.stdout.strip()) if r.returncode == 0 else Path(root) / ".claude"
    if not gd.is_absolute():
        gd = Path(root) / gd
    return gd / "info" / "srk-plan-stamp"


def _ext_check(root, plan, text):
    """Warn (never block) when the plan changed outside plan.py since our last
    write — the co-installed-tooling collision class (a GSD hook once silently
    reverted a plan's progress mid-run)."""
    import hashlib
    sp = _plan_stamp_path(root)
    try:
        stamp = sp.read_text(encoding="utf-8").strip()
    except OSError:
        return
    if stamp and stamp != hashlib.sha1(text.encode()).hexdigest():
        print(f"⚠ {plan.name} was modified OUTSIDE plan.py since the last srk "
              "write (co-installed tooling? an editor?). If progress looks "
              "reverted, diff the plan before trusting it.")


def _stamp(root, new_text):
    import hashlib
    sp = _plan_stamp_path(root)
    try:
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(hashlib.sha1(new_text.encode()).hexdigest(), encoding="utf-8")
    except OSError:
        pass


def cmd_done(root, ident, ref, actual=None):
    if re.fullmatch(r"(?i)[a-z]-?\d+", str(ident)):
        return _done_deferred(root, ident, ref, actual)
    plan = find_plan(root)
    _text0 = plan.read_text(encoding="utf-8")
    _ext_check(root, plan, _text0)
    lines = _text0.splitlines()
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
    _new = "\n".join(lines) + "\n"
    plan.write_text(_new, encoding="utf-8")
    _stamp(root, _new)
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
    _text0 = plan.read_text(encoding="utf-8")
    _ext_check(root, plan, _text0)
    lines = _text0.splitlines()
    cm = _colmap(lines)
    total = 0
    if "est. net loc" in cm:
        for _, cells, _cm in open_rows(lines):
            total += _int(cells[cm["est. net loc"]]) if cm["est. net loc"] < len(cells) else 0
    lines = _set_comment(lines, "est-savings", total)
    fp = _map_fp(root)
    if fp:
        lines = _set_comment(lines, "map-fp", fp)
    _new = "\n".join(lines) + "\n"
    plan.write_text(_new, encoding="utf-8")
    _stamp(root, _new)
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
            sys.exit("usage: plan.py todo-check <n | text-match> [more…] | --all")
        cmd_todo_check(root, rest)
    elif cmd == "adjudicate":
        if len(rest) < 2:
            sys.exit('usage: plan.py adjudicate <D-id> "<ruling>"')
        cmd_adjudicate(root, rest[0], " ".join(rest[1:]))
    elif cmd == "bug-done":
        if len(rest) < 2 or not re.fullmatch(r"(?i)b-?\d+", rest[0]):
            sys.exit("usage: plan.py bug-done <B-id> <ref> [actual-loc]")
        cmd_done(root, rest[0], rest[1], rest[2] if len(rest) > 2 else None)
    elif cmd == "failset":
        if len(rest) < 3 or rest[0] not in ("record", "compare") or "--" not in rest:
            sys.exit("usage: plan.py failset record|compare -- <suite command…>")
        cmd_failset(root, rest[0], rest[rest.index("--") + 1:])
    else:
        sys.exit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
