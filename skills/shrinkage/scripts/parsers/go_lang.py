"""Go adapter — regex + shared brace scanner.

Covers: struct/interface type declarations, funcs, and methods (receiver
form `func (r *Recv) Name(...)` — the receiver type becomes the parent).
Go has no classes; structs with methods play that role in the map.
"""
import re

from parsers import Symbol, scan_braced

TYPE = re.compile(
    r"^\s*type\s+(?P<name>\w+)\s+(?P<kw>struct|interface)\s*\{?"
)
FUNC = re.compile(
    r"^\s*func\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)?\s*(?P<ret>[^{]*)"
)
METHOD = re.compile(
    r"^\s*func\s+\(\s*\w+\s+\*?(?P<recv>\w+)\s*\)\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)?\s*(?P<ret>[^{]*)"
)


def _sig(m):
    sig = f"{m.group('name')}({m.group('params').strip()})"
    ret = (m.groupdict().get("ret") or "").strip()
    return sig + (f" {ret}" if ret else "")


def parse(text):
    # Methods first (FUNC would also match them) — collect directly, then let
    # scan_braced handle types and plain funcs with methods masked out.
    syms = []
    masked = []
    for line in text.splitlines():
        m = METHOD.search(line)
        masked.append("" if m else line)
    for n, line in enumerate(text.splitlines(), 1):
        m = METHOD.search(line)
        if m:
            syms.append(Symbol("m", m.group("name"), _sig(m), n, m.group("recv")))
    syms += scan_braced("\n".join(masked), TYPE, members=[], tops=[("f", FUNC, _sig)])
    # scan_braced marks interfaces as 'i'; Go structs arrive as kw=struct → map to 'c'
    for s in syms:
        if s.kind == "i" and s.base == "":
            pass  # interface — correct as-is
    return sorted(syms, key=lambda s: s.line)
