#!/usr/bin/env python3
"""coverage_check — coverage-aware risk tiers for the safety model.

Usage: coverage_check.py <file> [file...]        report coverage per file
       coverage_check.py --find                  just locate the coverage report

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


def main():
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
