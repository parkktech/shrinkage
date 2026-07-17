#!/usr/bin/env python3
"""diffstat — the minimalism scoreboard for the current change.

Usage: diffstat.py [REF] [--pr] [--log]     compare worktree against REF (default HEAD)
       diffstat.py --trend                  summarize the trend log (cumulative + streak)

Prints: net app LOC and net test LOC (separately — deleting tests never
flatters the score), files touched, new/removed symbols (via the same parser
registry as codemap.py, so every supported language is scored).

--pr   also emit a markdown block for the PR description
       (or set pr_scoreboard=true in .claude/shrinkage.json)
--log  append a JSON line to .claude/shrinkage-log.jsonl — the repo's weight
       trend over time
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import settings  # noqa: E402
from parsers import language_of, parse_file, parse_text  # noqa: E402

TEST_PATH = re.compile(r"(^|/)(tests?|specs?|__tests__)(/|$)|(^|[./_])(test|spec)s?[._]", re.I)
# Docs/config/lockfiles are not code — excluded from LOC so "app LOC" means code.
NON_CODE = re.compile(
    r"\.(md|markdown|rst|txt|json|ya?ml|toml|ini|cfg|conf|lock|env|csv|svg)$"
    r"|(^|/)\.gitignore$|(^|/)(\.planning|\.claude)/", re.I)


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def collect(ref):
    net_app = net_test = 0
    files, new_syms, removed_syms = [], [], []
    for line in git("diff", "--numstat", ref).strip().splitlines():
        add, rm, path = line.split("\t", 2)
        files.append(path)
        if add == "-":  # binary
            continue
        if NON_CODE.search(path):  # docs/config don't count as code LOC
            continue
        delta = int(add) - int(rm)
        if TEST_PATH.search(path):
            net_test += delta
        else:
            net_app += delta
    for path in files:
        if not language_of(path):
            continue
        old = {s.key() for s in parse_text(path, git("show", f"{ref}:{path}"))}
        new = {s.key() for s in (parse_file(Path(path)) if Path(path).exists() else [])}
        new_syms += [f"{p + '.' if p else ''}{n}" for _, p, n in new - old]
        removed_syms += [f"{p + '.' if p else ''}{n}" for _, p, n in old - new]
    return net_app, net_test, files, sorted(new_syms), sorted(removed_syms)


def signed(n):
    return f"+{n}" if n >= 0 else str(n)


def names(syms):
    return f" ({', '.join(syms[:8])})" if syms else ""


def show_trend():
    logp = Path(".claude/shrinkage-log.jsonl")
    if not logp.exists():
        print("no trend log yet — run diffstat.py --log after changes to start one")
        return
    entries = [json.loads(l) for l in logp.read_text(encoding="utf-8").splitlines() if l.strip()]
    app = sum(e["net_app"] for e in entries)
    test = sum(e["net_test"] for e in entries)
    streak = 0
    for e in reversed(entries):
        if e["net_app"] >= 0:
            break
        streak += 1
    print(f"trend: {len(entries)} scored changes | cumulative app LOC {signed(app)} | "
          f"cumulative test LOC {signed(test)} | shrink streak: {streak}")
    for e in entries[-10:]:
        print(f"  {e['ts']}  app {signed(e['net_app']):>6}  test {signed(e['net_test']):>6}  "
              f"files {e['files']}")
    if app < 0:
        q = settings.quip(".", "shrunk", net=app)
        if q:
            print(q)


def main():
    argv = sys.argv[1:]
    if "--trend" in argv:
        show_trend()
        return
    pos = [a for a in argv if not a.startswith("--")]
    ref = pos[0] if pos else "HEAD"
    net_app, net_test, files, new_syms, removed_syms = collect(ref)
    net = net_app + net_test

    print(f"net LOC: {signed(net)} (app {signed(net_app)}, test {signed(net_test)}) | "
          f"files touched: {len(files)} | "
          f"new symbols: {len(new_syms)}{names(new_syms)} | "
          f"removed symbols: {len(removed_syms)}{names(removed_syms)}")

    kind = ("shrunk" if net_app < 0 else
            "grew" if net_app > 25 else
            "flat" if (net_app == 0 and files) else None)
    q = settings.quip(".", kind, net=net_app) if kind else ""
    if q:
        print(q)
    elif net_app < 0:
        print("net-negative app diff — the feature landed and the codebase got smaller. Call it out.")
    if net_test < 0:
        print("note: test LOC went DOWN — confirm this was justified (safety-model §7: "
              "test deletions are never a shrink win).")

    if "--pr" in argv or settings.load(".")["pr_scoreboard"]:
        print("\n--- PR description block ---")
        print("### Code minimalism scoreboard\n")
        print("| net app LOC | net test LOC | files touched | new symbols | removed symbols |")
        print("|---|---|---|---|---|")
        print(f"| {signed(net_app)} | {signed(net_test)} | {len(files)} "
              f"| {len(new_syms)}{names(new_syms)} | {len(removed_syms)}{names(removed_syms)} |")

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
