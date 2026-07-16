"""JavaScript / TypeScript adapter — regex + shared brace scanner.

Covers: class/interface declarations (with extends), class methods,
top-level function declarations, and top-level arrow-function consts.
Multi-line parameter lists are truncated to the first line (map-level detail).
"""
import re

from parsers import scan_braced

_KW_GUARD = r"(?!if\b|for\b|while\b|switch\b|catch\b|return\b|function\b|new\b|do\b|else\b)"

DECL = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?P<kw>class|interface)\s+"
    r"(?P<name>\w+)"
    r"(?:\s+extends\s+(?P<base>[\w.]+))?"
    r"(?:\s+implements\s+(?P<impl>[\w.,\s]+?))?\s*[{<]"
)
FUNC = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*"
    r"(?P<name>\w+)\s*\((?P<params>[^)]*)\)?\s*(?::\s*(?P<ret>[\w<>\[\]|. ]+?))?\s*\{?\s*$"
)
ARROW = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+(?P<name>\w+)\s*=\s*(?:async\s*)?"
    r"\((?P<params>[^)]*)\)\s*(?::\s*[\w<>\[\]|. ]+)?\s*=>"
)
METHOD = re.compile(
    r"^\s*(?:(?:public|private|protected|static|async|override|get|set)\s+)*"
    + _KW_GUARD +
    r"(?P<name>\w+)\s*\((?P<params>[^)]*)\)?\s*(?::\s*(?P<ret>[\w<>\[\]|. ]+))?\s*\{"
)


def _sig(m):
    sig = f"{m.group('name')}({m.group('params').strip()})"
    ret = m.groupdict().get("ret")
    return sig + (f": {ret.strip()}" if ret else "")


def parse(text, ext=".js"):
    from parsers import ts_engine
    exact = ts_engine.try_parse(ext, text)
    if exact is not None:
        return exact
    return scan_braced(
        text, DECL,
        members=[("m", METHOD, _sig)],
        tops=[("f", FUNC, _sig), ("f", ARROW, _sig)],
    )
