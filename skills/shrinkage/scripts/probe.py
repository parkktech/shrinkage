#!/usr/bin/env python3
"""probe — runtime deprecation telemetry (safety-model §5, mechanized).

Turns "we THINK nothing calls this" into "production says nothing called this
for N days" — the strongest evidence there is for a T2/T3 removal.

  add    <file> <symbol> [--window 30] [--logs GLOB ...]
         insert a one-line entry counter into the symbol's body, register it
         in .shrinkage/probes.json (committed), and add a DEPRECATIONS.md row
  status scan the log globs for each probe's marker and report:
         ALIVE (called -> keep the symbol) / window open / BLIND (no logs
         matched) / CLOSED-ZERO (window elapsed, 0 hits -> chain closed)
  remove <id>
         delete the marker line, drop the registry entry, tick the row

v1 languages: PHP (error_log) and Python (logging) — the stacks with an
always-on log channel. Other languages refuse with guidance. The marker only
fires in RUNNING code: deploy the probe commit, wait out the window, THEN read
status. Insertion reuses the surgery engines (extract_method) for exact
placement and is balance/parse-checked before a byte is written.
Exit: 0 ok · 2 refused/precondition.
"""
import glob as globmod
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import extract_method as em  # noqa: E402

REG = Path(".shrinkage/probes.json")
DEP = Path("DEPRECATIONS.md")
DEFAULT_LOGS = {
    "php": ["storage/logs/*.log", "var/log/*.log", "var/log/**/*.log"],
    "python": ["logs/*.log", "log/*.log", "*.log"],
}

MARKERS = {
    "php": "error_log('srk-probe:{pid}');  "
           "// srk deprecation probe — managed by probe.py, do not hand-edit",
    "python": '__import__("logging").getLogger("srk.probe")'
              '.warning("srk-probe:{pid}")'
              "  # srk deprecation probe — managed by probe.py",
}


def die(code, msg):
    sys.stderr.write(msg.rstrip("\n") + "\n")
    sys.exit(code)


def load_reg():
    if REG.exists():
        try:
            return json.loads(REG.read_text(encoding="utf-8"))
        except ValueError:
            die(2, f"{REG} is corrupt JSON — fix or delete it first.")
    return {"probes": []}


def save_reg(reg):
    REG.parent.mkdir(parents=True, exist_ok=True)
    REG.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")


def probe_lang(path):
    try:
        eng = em.engine_for(path)
    except em.Refuse as e:
        die(2, str(e))
    if eng not in MARKERS:
        die(2, f"{path}: runtime probes v1 cover PHP + Python (stacks with an "
               f"always-on log channel). For {eng}: verify with "
               "`lsp_refs.py check` + the dynamic-reference checklist instead.")
    return eng


def _php_insert_at(text, name):
    """(line0-to-insert-before, indent) for a PHP method/function body entry."""
    cfg = em.BRACE_CFGS["php"]
    start, end = em.brace_find_span(text, name, cfg)   # may raise Refuse
    lines = text.splitlines(keepends=True)
    pat = re.compile(cfg["method_re"].format(name=re.escape(name)))
    sig = next(i for i in range(start, end + 1) if pat.match(lines[i]))
    off = sum(len(l) for l in lines[:sig])
    st = em._states(text, cfg)
    i = off
    while i < len(text):
        if st[i] == "code":
            if text[i] == "{":
                break
            if text[i] == ";":
                raise em.Refuse(f"{name}() has no body (abstract/interface "
                                "declaration) — nothing to instrument.")
        i += 1
    else:
        raise em.Refuse(f"{name}() body opener not found")
    brace_line = text.count("\n", 0, i)
    if brace_line == end:
        raise em.Refuse(f"{name}() is a single-line body — put the body on "
                        "its own lines first, then re-add the probe.")
    rest = text[i + 1:].split("\n", 1)[0].strip()
    if rest and not rest.startswith(("//", "#", "/*")):
        raise em.Refuse(f"{name}() has code on the brace line ({rest[:40]!r}) "
                        "— give the body its own lines first.")
    indent = re.match(r"[ \t]*", lines[sig]).group(0) + "    "
    return brace_line + 1, indent


def _py_insert_at(text, name):
    """(line0-to-insert-before, indent) for a Python def body entry —
    after the docstring if there is one."""
    import ast
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        raise em.Refuse(f"file does not parse ({e.msg}, line {e.lineno})")
    defs = em._py_defs(tree, name)
    if not defs:
        raise em.Refuse(f"def {name}() not found")
    if len(defs) > 1:
        raise em.Refuse(f"def {name}() defined more than once — "
                        "disambiguate manually.")
    d = defs[0]
    body = d.body
    is_doc = (isinstance(body[0], ast.Expr)
              and isinstance(getattr(body[0], "value", None), ast.Constant)
              and isinstance(body[0].value.value, str))
    anchor = body[1] if is_doc and len(body) > 1 else body[0]
    if anchor.lineno == d.lineno:
        raise em.Refuse(f"def {name}() is a one-liner — expand the body to "
                        "its own lines first, then re-add the probe.")
    if is_doc and len(body) == 1:
        return body[0].end_lineno, " " * body[0].col_offset
    if is_doc:
        return anchor.lineno - 1, " " * anchor.col_offset
    return anchor.lineno - 1, " " * anchor.col_offset


def cmd_add(path, symbol, window, logs):
    p = Path(path)
    if not p.exists():
        die(2, f"{path}: no such file")
    lang = probe_lang(path)
    text = p.read_text(encoding="utf-8")
    pid = hashlib.sha1(f"{path}:{symbol}".encode()).hexdigest()[:8]
    marker = f"srk-probe:{pid}"
    reg = load_reg()
    if any(pr["id"] == pid for pr in reg["probes"]):
        die(2, f"probe {pid} already armed for {symbol} ({path}) — "
               "probe.py status to read it.")
    if marker in text:
        die(2, f"{path} already contains {marker} — remove the stray line "
               "or run probe.py remove.")
    try:
        line0, indent = (_php_insert_at if lang == "php"
                         else _py_insert_at)(text, symbol)
    except em.Refuse as e:
        die(2, str(e))
    lines = text.splitlines(keepends=True)
    probe_line = indent + MARKERS[lang].format(pid=pid) + "\n"
    new = "".join(lines[:line0]) + probe_line + "".join(lines[line0:])
    em._write_checked(path, new, "probe insertion")

    today = date.today().isoformat()
    logs = logs or DEFAULT_LOGS[lang]
    reg["probes"].append({"id": pid, "file": str(path), "symbol": symbol,
                          "lang": lang, "added": today,
                          "window_days": window, "logs": logs,
                          "marker": marker})
    save_reg(reg)
    row = (f"- [ ] probe {pid}: {symbol} ({path}) — window {window}d "
           f"from {today}")
    if DEP.exists():
        DEP.write_text(DEP.read_text(encoding="utf-8").rstrip("\n")
                       + "\n" + row + "\n", encoding="utf-8")
    else:
        DEP.write_text("# Deprecations\n\nRuntime probes armed by probe.py — "
                       "each row closes empirically (CLOSED-ZERO) or the "
                       "symbol stays.\n\n" + row + "\n", encoding="utf-8")
    print(f"armed probe {pid}: {symbol} ({path}), window {window}d, "
          f"watching {', '.join(logs)}")
    print("The counter only fires in RUNNING code — commit and DEPLOY this "
          "change, then `probe.py status` after the window.")
    print(f"Annotate the plan row: `probe: {pid} since {today}`.")


def _scan(probe):
    files = []
    for g in probe["logs"]:
        files.extend(globmod.glob(g, recursive=True))
    files = sorted(set(f for f in files if Path(f).is_file()))
    hits = 0
    for f in files:
        try:
            hits += Path(f).read_text(encoding="utf-8",
                                      errors="replace").count(probe["marker"])
        except OSError:
            pass
    return len(files), hits


def cmd_status():
    reg = load_reg()
    if not reg["probes"]:
        print("no probes armed — probe.py add <file> <symbol> to start one.")
        return
    for pr in reg["probes"]:
        elapsed = (date.today() - date.fromisoformat(pr["added"])).days
        window = pr["window_days"]
        nfiles, hits = _scan(pr)
        print(f"probe {pr['id']} — {pr['symbol']} ({pr['file']}), "
              f"armed {pr['added']}, window {window}d")
        if hits:
            print(f"  ALIVE — {hits} hit(s) in {nfiles} log file(s): still "
                  f"called at runtime → KEEP {pr['symbol']}; "
                  f"probe.py remove {pr['id']}")
        elif nfiles == 0:
            print("  BLIND — 0 log files matched "
                  f"{', '.join(pr['logs'])}; telemetry is off. Point the "
                  "probe at the real channel (edit logs in "
                  f"{REG}) or check the deploy.")
        elif elapsed < window:
            print(f"  window open — {elapsed}d elapsed, "
                  f"{window - elapsed}d remaining · 0 hits · "
                  f"{nfiles} log file(s) watched")
        else:
            print(f"  CLOSED-ZERO — 0 hits in {elapsed}d ≥ window {window}d. "
                  f"Empirical chain closed: remove {pr['symbol']} citing "
                  f"probe {pr['id']}, then probe.py remove {pr['id']}")


def cmd_remove(pid):
    reg = load_reg()
    hit = next((pr for pr in reg["probes"] if pr["id"] == pid), None)
    if hit is None:
        die(2, f"no probe {pid} in {REG} — probe.py status lists them.")
    p = Path(hit["file"])
    if p.exists():
        text = p.read_text(encoding="utf-8")
        kept = [l for l in text.splitlines(keepends=True)
                if hit["marker"] not in l]
        if len(kept) == len(text.splitlines(keepends=True)):
            print(f"note: {hit['marker']} not found in {p} (already gone) — "
                  "dropping the registry entry.")
        else:
            em._write_checked(str(p), "".join(kept), "probe removal")
    else:
        print(f"note: {p} no longer exists (symbol removed?) — "
              "dropping the registry entry.")
    reg["probes"] = [pr for pr in reg["probes"] if pr["id"] != pid]
    save_reg(reg)
    if DEP.exists():
        today = date.today().isoformat()
        out = []
        for l in DEP.read_text(encoding="utf-8").splitlines(keepends=True):
            if f"probe {pid}:" in l and l.lstrip().startswith("- [ ]"):
                l = l.replace("- [ ]", "- [x]", 1).rstrip("\n") \
                    + f" (probe removed {today})\n"
            out.append(l)
        DEP.write_text("".join(out), encoding="utf-8")
    print(f"probe {pid} removed.")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        die(0, __doc__)
    if args[0] == "add":
        rest, window, logs = args[1:], 30, []
        if "--window" in rest:
            i = rest.index("--window")
            window = int(rest[i + 1])
            del rest[i:i + 2]
        while "--logs" in rest:
            i = rest.index("--logs")
            logs.append(rest[i + 1])
            del rest[i:i + 2]
        if len(rest) != 2:
            die(2, "usage: probe.py add <file> <symbol> [--window N] "
                   "[--logs GLOB ...]")
        cmd_add(rest[0], rest[1], window, logs)
        return
    if args[0] == "status":
        cmd_status()
        return
    if args[0] == "remove":
        if len(args) != 2:
            die(2, "usage: probe.py remove <id>")
        cmd_remove(args[1])
        return
    die(2, f"unknown subcommand {args[0]!r} — try: add, status, remove")


if __name__ == "__main__":
    main()
