"""Rust adapter — regex + shared brace scanner.

Covers: struct/enum/trait declarations, free fns, and fns inside `impl`
blocks (the impl target becomes the parent; `impl Trait for Type` records
the trait as base context on the method's parent name `Type`).
"""
import re

from parsers import Symbol, scan_braced

DECL = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?P<kw>struct|enum|trait|union)\s+(?P<name>\w+)"
)
IMPL = re.compile(
    r"^\s*impl(?:<[^>]*>)?\s+(?:(?P<trait>[\w:]+)\s+for\s+)?(?P<target>\w+)"
)
FN = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?(?:const\s+)?fn\s+"
    r"(?P<name>\w+)\s*(?:<[^>]*>)?\s*\((?P<params>[^)]*)\)?\s*(?:->\s*(?P<ret>[^{]+))?"
)


def _sig(m):
    sig = f"{m.group('name')}({m.group('params').strip()})"
    ret = (m.groupdict().get("ret") or "").strip().rstrip(";{").strip()
    return sig + (f" -> {ret}" if ret else "")


def parse(text):
    syms = []
    depth = 0
    impl_stack = []  # (target, trait, depth_at_open)
    for n, line in enumerate(text.splitlines(), 1):
        dm = DECL.search(line)
        im = IMPL.search(line) if not dm else None
        fm = FN.search(line) if not (dm or im) else None
        if dm:
            kind = "i" if dm.group("kw") == "trait" else "c"
            syms.append(Symbol(kind, dm.group("name"), dm.group("name"), n))
            if kind == "i":  # trait body fns are methods of the trait
                impl_stack.append([dm.group("name"), "", None])
        elif im:
            impl_stack.append([im.group("target"), im.group("trait") or "", None])
        elif fm:
            parent = impl_stack[-1][0] if impl_stack and impl_stack[-1][2] is not None else ""
            syms.append(Symbol("m" if parent else "f", fm.group("name"), _sig(fm), n, parent))
        for ch in line:
            if ch == "{":
                depth += 1
                if impl_stack and impl_stack[-1][2] is None:
                    impl_stack[-1][2] = depth
            elif ch == "}":
                depth -= 1
                if impl_stack and impl_stack[-1][2] is not None and depth < impl_stack[-1][2]:
                    impl_stack.pop()
    return syms
