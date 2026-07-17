#!/usr/bin/env python3
"""badge — generate a shrink badge SVG from the trend log (v0.8).

Usage: badge.py [--out .claude/shrinkage-badge.svg]

Reads .claude/shrinkage-log.jsonl and renders a shields-style badge with the
cumulative app-LOC delta. Green when the ratchet points down, gray otherwise.
Commit the SVG and embed it in your README to make the metric visible.
"""
import json
import sys
from pathlib import Path

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" aria-label="shrinkage: {value}">
<rect rx="3" width="{w}" height="20" fill="#555"/>
<rect rx="3" x="66" width="{vw}" height="20" fill="{color}"/>
<rect x="66" width="4" height="20" fill="{color}"/>
<g fill="#fff" text-anchor="middle" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">
<text x="33" y="14">shrinkage</text>
<text x="{vx}" y="14">{value}</text>
</g></svg>"""


def main():
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv \
        else Path(".claude/shrinkage-badge.svg")
    log = Path(".claude/shrinkage-log.jsonl")
    if not log.exists():
        raise SystemExit("no trend log — score with --log first")
    app = sum(json.loads(l)["net_app"] for l in log.read_text(encoding="utf-8").splitlines() if l.strip())
    value = f"{'+' if app >= 0 else ''}{app} LOC"
    color = "#009E73" if app < 0 else "#7F7F7F"
    vw = 6 * len(value) + 14
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(SVG.format(w=66 + vw, vw=vw, vx=66 + vw // 2, value=value, color=color),
                   encoding="utf-8")
    print(f"badge written: {out} ({value})")


if __name__ == "__main__":
    main()
