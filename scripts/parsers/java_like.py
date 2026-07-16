"""Java and C# adapter — regex + shared brace scanner (one module, two
ecosystems: the declaration grammars are close enough that a single adapter
with a permissive modifier set covers both; rules files stay separate).

Covers: class/interface/enum/record/struct declarations (extends/implements
and C# `: Base, IFace` forms), methods, and constructors.
"""
import re

from parsers import Symbol, scan_braced

_KW_GUARD = r"(?!if\b|for\b|while\b|switch\b|catch\b|return\b|new\b|else\b|do\b|using\b|lock\b|foreach\b)"

DECL = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|static|final|sealed|abstract|partial)\s+)*"
    r"(?P<kw>class|interface|enum|record|struct)\s+(?P<name>\w+)(?:<[^>]*>)?"
    r"(?:\s+extends\s+(?P<base>[\w.<>]+))?"
    r"(?:\s+implements\s+(?P<impl>[\w.,<>\s]+?))?"
    r"(?:\s*:\s*(?P<cs_base>[\w.,<>\s]+?))?\s*(?:\{|$)"
)
METHOD = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|static|final|abstract|virtual|override|sealed|async|synchronized)\s+)+"
    r"(?:[\w.<>\[\],?]+\s+)?" + _KW_GUARD +
    r"(?P<name>\w+)\s*\((?P<params>[^)]*)\)?\s*(?:\{|;|=>|throws|$)"
)


def _sig(m):
    return f"{m.group('name')}({m.group('params').strip()})"


def parse(text):
    syms = scan_braced(text, DECL, members=[("m", METHOD, _sig)], tops=[])
    # C# base clause arrives in cs_base; merge into Symbol.base after the fact
    for n, line in enumerate(text.splitlines(), 1):
        dm = DECL.search(line)
        if dm and dm.group("cs_base"):
            for s in syms:
                if s.line == n and s.kind in ("c", "i") and not s.base:
                    s.base = dm.group("cs_base").strip()
    return syms
