"""Language adapter registry.

Adding a language = one parser module exposing `parse(text) -> list[Symbol]`
plus its extension entries in EXTENSIONS, and a rules file in `rules/<lang>.md`.
Detection, mapping, ranking, diffstat, and GSD intel sync all pick the new
language up from here — no core changes.
"""
import importlib
import os
import re
from dataclasses import dataclass, field


@dataclass
class Symbol:
    kind: str            # c=class, m=method, f=function, i=interface/trait
    name: str
    signature: str       # display form, e.g. "refresh(user_id, force=False) -> Token"
    line: int
    parent: str = ""     # enclosing class name, for methods
    base: str = ""       # superclass / implemented interfaces, for classes
    refs: int = field(default=0, compare=False)  # filled in by the ranker

    def key(self):
        return (self.kind, self.parent, self.name)


# extension -> (parser module, language label; rules file is rules/<label>.md)
EXTENSIONS = {
    ".py":   ("python_lang", "python"),
    ".js":   ("javascript", "javascript"),
    ".jsx":  ("javascript", "javascript"),
    ".mjs":  ("javascript", "javascript"),
    ".ts":   ("javascript", "javascript"),
    ".tsx":  ("javascript", "javascript"),
    ".php":  ("php", "php"),      # .blade.php lands here too (splitext -> .php)
    ".phtml": ("php", "php"),     # Magento/Zend templates: PHP+HTML — few symbols,
                                  # but indexing them makes template REFS count
    ".twig": ("twig", "twig"),    # Drupal/Symfony: blocks + macros mapped
    ".go":   ("go_lang", "go"),
    ".rs":   ("rust", "rust"),
    ".java": ("java_like", "java"),
    ".cs":   ("java_like", "csharp"),
    ".kt":     ("kotlin", "kotlin"),
    ".vue":    ("javascript", "javascript"),  # SFC: script parsed, template refs counted
    ".svelte": ("javascript", "javascript"),
    ".astro":  ("javascript", "javascript"),
}

# Reference-only types: define no symbols worth mapping, but REFERENCE code —
# they feed the identifier counter so template/config usage keeps symbols
# alive in the map (the classic deletion trap).
REF_ONLY_EXTS = {".hbs", ".mustache", ".ejs", ".j2", ".jinja", ".jinja2",
                 ".tpl", ".latte", ".erb", ".liquid",
                 ".kts", ".gradle", ".pro"}  # gradle scripts + proguard keep rules
# Framework config that references classes/methods by string (Magento XML,
# Drupal/Symfony YAML, Laravel config dirs are .php and already indexed).
REF_ONLY_FILES = re.compile(
    r"(^|/)(di|events|webapi|system|crontab|widget|acl|menu|sections)\.xml$"
    r"|(^|/)view/.*/(layout|ui_component)/.*\.xml$"
    r"|\.services\.ya?ml$|(^|/)routing\.ya?ml$|\.links\.[\w.]+\.ya?ml$"
    r"|(^|/)config/schema/.*\.ya?ml$"
    r"|(^|/)AndroidManifest\.xml$|(^|/)res/(layout|navigation|xml|menu)[^/]*/.*\.xml$")


def is_ref_only(path):
    p = str(path).replace("\\", "/")
    return os.path.splitext(p)[1].lower() in REF_ONLY_EXTS or bool(REF_ONLY_FILES.search(p))


def language_of(path):
    entry = EXTENSIONS.get(os.path.splitext(path)[1].lower())
    return entry[1] if entry else None


def parser_for(path):
    entry = EXTENSIONS.get(os.path.splitext(path)[1].lower())
    if not entry:
        return None
    return importlib.import_module(f"parsers.{entry[0]}")


def parse_text(path, text):
    """Parse source text using the adapter for path's extension.

    Adapters that accept (text, ext) get the extension (enables per-dialect
    tree-sitter grammars); older single-arg adapters still work.
    """
    parser = parser_for(str(path))
    if not parser:
        return []
    ext = os.path.splitext(str(path))[1].lower()
    try:
        return parser.parse(text, ext)
    except TypeError:
        return parser.parse(text)


def parse_file(path):
    """Parse a source file into symbols; unreadable/unparseable -> []."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return parse_text(path, fh.read())
    except OSError:
        return []


_STR_RE = re.compile(r'"(?:\\.|[^"\\])*"' + r"|'(?:\\.|[^'\\])*'" + r"|`(?:\\.|[^`\\])*`")
_LINE_COMMENT_RE = re.compile(r"(//|#).*")


def _neutralize(line):
    """Blank out string literals and line comments so braces inside them don't
    skew depth tracking (e.g. Go's `fmt.Sprintf("{%s}")`). Crude but effective
    for line-based scanning; multi-line strings remain a documented limitation."""
    return _LINE_COMMENT_RE.sub(" ", _STR_RE.sub('""', line))


def scan_braced(text, decl_re, members, tops):
    """Shared line scanner for brace-delimited languages (JS, PHP, Java, Go, ...).

    decl_re : class-like declaration regex with named groups `kw`, `name`, and
              optionally `base` / `impl` (joined into Symbol.base).
    members : [(kind, regex, fmt)] matched only directly inside a class body.
    tops    : [(kind, regex, fmt)] matched only outside any class body.
    fmt(match) -> signature string.

    Line-based and string/comment-naive by design: good enough for a map, and
    a parser can swap in tree-sitter later without changing its interface.
    """
    syms = []
    depth = 0
    stack = []  # [class_name, body_depth or None until its "{" is seen]

    for n, raw in enumerate(text.splitlines(), 1):
        line = _neutralize(raw)
        dm = decl_re.search(line)
        if dm:
            g = dm.groupdict()
            kw = (g.get("kw") or "class").lower()
            base = ", ".join(x.strip() for x in (g.get("base"), g.get("impl")) if x)
            kind = "i" if kw in ("interface", "trait") else "c"
            syms.append(Symbol(kind, g["name"], g["name"], n, "", base))
            stack.append([g["name"], None])
        else:
            inside = bool(stack) and stack[-1][1] is not None and depth == stack[-1][1]
            pool = members if inside else (tops if not stack else [])
            for kind, rex, fmt in pool:
                m = rex.search(line)
                if m:
                    parent = stack[-1][0] if inside else ""
                    syms.append(Symbol(kind, m.group("name"), fmt(m), n, parent))
                    break
        for ch in line:
            if ch == "{":
                depth += 1
                if stack and stack[-1][1] is None:
                    stack[-1][1] = depth
            elif ch == "}":
                depth -= 1
                if stack and stack[-1][1] is not None and depth < stack[-1][1]:
                    stack.pop()
    return syms
