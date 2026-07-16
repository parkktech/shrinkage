"""PHP adapter — regex + shared brace scanner.

Covers: class/interface/trait declarations (extends + implements), methods
(with or without visibility modifiers), and top-level functions. PSR-12
next-line braces are handled by the scanner's pending-declaration tracking.
"""
import re

from parsers import scan_braced

DECL = re.compile(
    r"^\s*(?:abstract\s+|final\s+|readonly\s+)*(?P<kw>class|interface|trait|enum)\s+"
    r"(?P<name>\w+)"
    r"(?:\s+extends\s+(?P<base>[\w\\]+))?"
    r"(?:\s+implements\s+(?P<impl>[\w\\,\s]+?))?\s*(?:$|\{)"
)
METHOD = re.compile(
    r"^\s*(?:(?:public|protected|private|static|final|abstract)\s+)*function\s+"
    r"(?P<name>\w+)\s*\((?P<params>[^)]*)\)?\s*(?::\s*(?P<ret>\??[\w\\|]+))?"
)
FUNC = re.compile(
    r"^\s*function\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)?\s*(?::\s*(?P<ret>\??[\w\\|]+))?"
)


def _sig(m):
    sig = f"{m.group('name')}({m.group('params').strip()})"
    ret = m.groupdict().get("ret")
    return sig + (f": {ret.strip()}" if ret else "")


def parse(text, ext=".php"):
    from parsers import ts_engine
    exact = ts_engine.try_parse(ext, text)
    if exact is not None:
        return exact
    return scan_braced(
        text, DECL,
        members=[("m", METHOD, _sig)],
        tops=[("f", FUNC, _sig)],
    )
