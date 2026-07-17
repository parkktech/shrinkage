#!/usr/bin/env python3
"""gatelog — persistent gate ledger (v0.8).

The reuse gate's justifications used to live only in chat scrollback; this
gives them a machine-checkable record so diffstat can flag any new symbol
that never passed a gate.

Usage:
  gatelog.py add --task "add csv export" --rung 2 --symbols "render,_render_csv" [--note "..."]
  gatelog.py list [-n 10]

Ledger: .claude/shrinkage-gates.jsonl (one JSON object per line).
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path(".claude/shrinkage-gates.jsonl")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("--task", required=True, help="one-line task description")
    add.add_argument("--rung", type=int, required=True, help="extension-ladder rung (1-8)")
    add.add_argument("--symbols", default="", help="comma-separated symbols this gate justifies")
    add.add_argument("--note", default="", help="justification (required for rungs 7-8)")
    ls = sub.add_parser("list")
    ls.add_argument("-n", type=int, default=10)
    a = ap.parse_args()

    if a.cmd == "add":
        if a.rung >= 7 and not a.note:
            raise SystemExit("rungs 7-8 (new file/module) require --note with the justification")
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "task": a.task, "rung": a.rung,
                 "symbols": [s.strip() for s in a.symbols.split(",") if s.strip()],
                 "note": a.note}
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        print(f"gate recorded: rung {a.rung}, {len(entry['symbols'])} symbol(s) — {a.task}")
    else:
        if not LEDGER.exists():
            print("no gate ledger yet")
            return
        for line in LEDGER.read_text(encoding="utf-8").splitlines()[-a.n:]:
            e = json.loads(line)
            print(f"{e['ts']}  rung {e['rung']}  {e['task']}  -> {', '.join(e['symbols']) or '-'}")


if __name__ == "__main__":
    main()
