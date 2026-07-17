"""Kotlin adapter — regex + shared brace scanner.

Covers: class/interface/object declarations (with supertypes, primary-
constructor parens tolerated), member functions, top-level functions, and
extension functions (`fun Recv.name()` — receiver recorded as the parent,
Go-style). Companion-object members are a known v1 gap (nested one level
deeper than the scanner's direct-member rule).
"""
import re

from parsers import Symbol, scan_braced

DECL = re.compile(
    r"^\s*(?:(?:public|private|internal|protected|abstract|final|open|sealed|data|inner|annotation|enum|value)\s+)*"
    r"(?P<kw>class|interface|object)\s+(?P<name>\w+)(?:<[^>]*>)?"
    r"\s*(?:\([^)]*\)?)?\s*(?::\s*(?P<base>[^{]+?))?\s*(?:\{|$)"
)
FUN = re.compile(
    r"^\s*(?:(?:public|private|internal|protected|open|override|suspend|inline|operator|infix|tailrec|external|actual|expect)\s+)*"
    r"fun\s+(?:<[^>]*>\s+)?(?:(?P<recv>[\w.<>?]+)\.)?(?P<name>\w+)"
    r"\s*\((?P<params>[^)]*)\)?\s*(?::\s*(?P<ret>[^{=]+?))?\s*(?:\{|=|$)"
)


def _sig(m):
    recv = m.groupdict().get("recv")
    sig = f"{recv + '.' if recv else ''}{m.group('name')}({m.group('params').strip()})"
    ret = (m.groupdict().get("ret") or "").strip()
    return sig + (f": {ret}" if ret else "")


def parse(text):
    syms = scan_braced(text, DECL, members=[("m", FUN, _sig)], tops=[("f", FUN, _sig)])
    # top-level extension functions: record the receiver as parent so
    # `String.truncate` groups under String in the map
    for s in syms:
        if s.kind == "f" and "." in s.signature.split("(")[0]:
            s.parent = s.signature.split("(")[0].rsplit(".", 1)[0]
            s.kind = "m"
    return syms
