#!/usr/bin/env python3
"""coverage_check — coverage-aware risk tiers for the safety model.

Usage: coverage_check.py <file> [file...]        report coverage per file
       coverage_check.py --find                  just locate the coverage report
       coverage_check.py bootstrap [--run]       detect (and optionally run) this
                                                 repo's coverage command — the
                                                 one-command upgrade from
                                                 suite-gated to coverage-aware
                                                 tiering (field gap #10)

Reads the first coverage report found (or $SHRINKAGE_COVERAGE): lcov
(lcov.info), Cobertura XML (coverage.xml — pytest-cov, PHPUnit's cobertura),
Clover XML (clover.xml — PHPUnit default), or coverage.py JSON
(coverage.json). Prints per-file line coverage and the tier consequence:
files with no/low coverage escalate deletions to T2 because test gates can't
protect them (safety-model §4).
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CANDIDATES = ["lcov.info", "coverage/lcov.info", "coverage.xml", "clover.xml",
              "coverage.json", "coverage/coverage.json", "build/logs/clover.xml",
              "coverage/cobertura-coverage.xml"]
LOW = 40.0  # percent below which we treat the file as effectively unprotected


def find_report():
    env = os.environ.get("SHRINKAGE_COVERAGE")
    if env and Path(env).exists():
        return Path(env)
    for c in CANDIDATES:
        if Path(c).exists():
            return Path(c)
    return None


def parse_lcov(path):
    cov, current = {}, None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("SF:"):
            current = line[3:].strip()
            cov[current] = [0, 0]
        elif line.startswith("DA:") and current:
            hits = int(line.split(",")[1])
            cov[current][0] += 1
            cov[current][1] += 1 if hits > 0 else 0
    return {f: (c / t * 100 if t else 0.0) for f, (t, c) in cov.items()}


def parse_xml(path):
    root = ET.parse(path).getroot()
    cov = {}
    if root.tag == "coverage" and root.find(".//project") is not None:  # clover
        for f in root.iter("file"):
            m = f.find("metrics")
            if m is not None and f.get("name"):
                stmts, covered = int(m.get("statements", 0)), int(m.get("coveredstatements", 0))
                cov[f.get("name")] = covered / stmts * 100 if stmts else 0.0
    else:  # cobertura
        for cls in root.iter("class"):
            fname = cls.get("filename")
            lines = cls.findall("./lines/line")
            if fname and lines:
                covered = sum(1 for l in lines if int(l.get("hits", 0)) > 0)
                cov[fname] = covered / len(lines) * 100
    return cov


def parse_json(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return {f: v.get("summary", {}).get("percent_covered", 0.0)
            for f, v in data.get("files", {}).items()}


def load(path):
    if path.suffix == ".info" or path.name.endswith("lcov.info"):
        return parse_lcov(path)
    if path.suffix == ".xml":
        return parse_xml(path)
    return parse_json(path)


def lookup(cov, target):
    t = str(Path(target))
    for f, pct in cov.items():
        if f.endswith(t) or t.endswith(f) or Path(f).name == Path(t).name and Path(f).parts[-2:] == Path(t).parts[-2:]:
            return pct
    return None


def detect_bootstrap(root="."):
    """(command, artifact, note) for generating this repo's first coverage
    report — the one-command upgrade from suite-gated to coverage-aware tiering.
    note carries driver caveats; (None, None, reason) when undetectable."""
    r = Path(root)
    if (r / "vendor" / "bin" / "pest").exists() or (r / "vendor" / "bin" / "phpunit").exists():
        runner = "vendor/bin/pest" if (r / "vendor" / "bin" / "pest").exists() else "vendor/bin/phpunit"
        note = ""
        try:
            import subprocess
            mods = subprocess.run(["php", "-m"], capture_output=True, text=True,
                                  timeout=20).stdout.lower()
            if "pcov" not in mods and "xdebug" not in mods:
                note = ("no coverage driver loaded — install pcov (fast: "
                        "`pecl install pcov`) or enable xdebug first, or the run "
                        "reports 0% everywhere.")
        except Exception:
            note = "couldn't verify a PHP coverage driver (php -m unavailable) — pcov or xdebug must be loaded."
        return f"{runner} --coverage-clover clover.xml", "clover.xml", note
    if (r / "pytest.ini").exists() or (r / "pyproject.toml").exists() or (r / "tests").is_dir():
        return (f"{sys.executable} -m pytest --cov --cov-report=xml",
                "coverage.xml", "needs pytest-cov (`pip install pytest-cov`).")
    pkg = r / "package.json"
    if pkg.exists():
        text = pkg.read_text(encoding="utf-8", errors="replace")
        if "vitest" in text:
            return "npx vitest run --coverage", "coverage/lcov.info", "needs @vitest/coverage-v8."
        if "jest" in text:
            return "npx jest --coverage", "coverage/lcov.info", ""
    if (r / "go.mod").exists():
        return ("go test ./... -coverprofile=coverage.out", "coverage.out",
                "Go's profile format isn't parsed directly — convert with "
                "gcov2lcov (`gcov2lcov -infile coverage.out -outfile lcov.info`).")
    if (r / "Cargo.toml").exists():
        return ("cargo tarpaulin --out Xml", "cobertura.xml",
                "needs cargo-tarpaulin (`cargo install cargo-tarpaulin`).")
    return None, None, "no recognized test ecosystem (pest/phpunit, pytest, vitest/jest, go, cargo)."


def cmd_bootstrap(run=False):
    cmd, artifact, note = detect_bootstrap(".")
    if not cmd:
        sys.exit(f"cannot bootstrap: {note}")
    print(f"coverage bootstrap for this repo:\n  command:  {cmd}\n  artifact: {artifact}"
          + (f"\n  ⚠ note:   {note}" if note else ""))
    if not run:
        print("\nDry by default — run it with:  coverage_check.py bootstrap --run\n"
              "After the artifact exists, /srk:audit upgrades every row from "
              "suite-gated to coverage-aware tiering (safety-model §4).")
        return
    import shlex
    import subprocess
    print("\nrunning (this executes your whole test suite)…")
    r = subprocess.run(shlex.split(cmd), timeout=3600)
    found = find_report()
    if found:
        print(f"\ndone — coverage artifact at {found}. Re-run /srk:audit: rows "
              "upgrade from suite-gated to coverage-aware tiering.")
    else:
        sys.exit(f"suite ran (exit {r.returncode}) but no artifact found where "
                 "coverage_check looks — check the note above, or set $SHRINKAGE_COVERAGE.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "bootstrap":
        cmd_bootstrap(run="--run" in sys.argv)
        return
    report = find_report()
    if "--find" in sys.argv:
        print(report or "no coverage report found "
              "(looked for lcov.info / coverage.xml / clover.xml / coverage.json; "
              "set $SHRINKAGE_COVERAGE to point at one)")
        return
    targets = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not targets:
        sys.exit(__doc__)
    if not report:
        print("no coverage report found — treat ALL deletion targets as T2 "
              "(test gates can't protect uncovered code; safety-model §4). "
              "Generate one (pytest --cov --cov-report=xml | PHPUnit --coverage-clover | "
              "jest --coverage) or set $SHRINKAGE_COVERAGE.")
        return
    cov = load(report)
    print(f"coverage report: {report}")
    for t in targets:
        pct = lookup(cov, t)
        if pct is None:
            print(f"  {t}: NOT IN REPORT -> tier consequence: T2 (unprotected)")
        elif pct < LOW:
            print(f"  {t}: {pct:.0f}% -> tier consequence: T2 (below {LOW:.0f}% — "
                  f"write characterization tests first)")
        else:
            print(f"  {t}: {pct:.0f}% -> test gates can protect this file (T1 eligible)")


if __name__ == "__main__":
    main()
