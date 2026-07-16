"""Optional tree-sitter engine — exact parsing when grammars are installed.

    pip install tree-sitter tree-sitter-javascript tree-sitter-typescript tree-sitter-php

Adapters call `try_parse(ext, text)` first and fall back to their regex path
when this returns None (grammar not installed, parse error, or
SHRINKAGE_NO_TREESITTER=1). Same Symbol interface either way — upgrading
precision never changes the map format or anything downstream.
"""
import os

from parsers import Symbol

_LANGS = {}  # ext -> tree_sitter.Language | None (None = tried and unavailable)

_EXT_GRAMMAR = {
    ".js": ("tree_sitter_javascript", "language"),
    ".jsx": ("tree_sitter_javascript", "language"),
    ".mjs": ("tree_sitter_javascript", "language"),
    ".ts": ("tree_sitter_typescript", "language_typescript"),
    ".tsx": ("tree_sitter_typescript", "language_tsx"),
    ".php": ("tree_sitter_php", "language_php"),
}


def _language(ext):
    if ext in _LANGS:
        return _LANGS[ext]
    lang = None
    if not os.environ.get("SHRINKAGE_NO_TREESITTER"):
        try:
            import tree_sitter
            modname, fname = _EXT_GRAMMAR[ext]
            mod = __import__(modname)
            fn = getattr(mod, fname, None) or getattr(mod, "language", None)
            lang = tree_sitter.Language(fn())
        except Exception:
            lang = None
    _LANGS[ext] = lang
    return lang


def _text(node):
    return node.text.decode("utf-8", errors="replace")


def _name_of(node, *fields):
    for f in fields:
        c = node.child_by_field_name(f)
        if c is not None:
            return _text(c)
    return None


def _params(node):
    p = node.child_by_field_name("parameters") or node.child_by_field_name("formal_parameters")
    if p is None:
        return "()"
    t = " ".join(_text(p).split())
    return t if t.startswith("(") else f"({t})"


def _ret(node):
    r = node.child_by_field_name("return_type")
    return f": {' '.join(_text(r).lstrip(':').split())}" if r is not None else ""


# node types that declare a class-like scope, per grammar family
_CLASSLIKE = {
    "class_declaration": "c", "abstract_class_declaration": "c",
    "interface_declaration": "i", "trait_declaration": "i",
    "enum_declaration": "c",
}
_FUNCLIKE = {"function_declaration", "function_definition", "generator_function_declaration"}
_METHODLIKE = {"method_definition", "method_declaration"}


def _heritage(node):
    parts = []
    for child in node.children:
        if child.type in ("class_heritage", "base_clause", "class_interface_clause", "extends_clause", "implements_clause"):
            t = _text(child)
            for kw in ("extends", "implements", ":"):
                t = t.replace(kw, ",")
            parts += [x.strip() for x in t.split(",") if x.strip()]
    return ", ".join(dict.fromkeys(parts))


def _walk(node, syms, parent):
    kind = _CLASSLIKE.get(node.type)
    if kind:
        name = _name_of(node, "name")
        if name:
            syms.append(Symbol(kind, name, name, node.start_point[0] + 1, "", _heritage(node)))
            for child in node.children:
                _walk(child, syms, name)
            return
    elif node.type in _METHODLIKE and parent:
        name = _name_of(node, "name")
        if name:
            syms.append(Symbol("m", name, f"{name}{_params(node)}{_ret(node)}",
                               node.start_point[0] + 1, parent))
    elif node.type in _FUNCLIKE and not parent:
        name = _name_of(node, "name")
        if name:
            syms.append(Symbol("f", name, f"{name}{_params(node)}{_ret(node)}",
                               node.start_point[0] + 1))
    elif node.type == "variable_declarator" and not parent:
        value = node.child_by_field_name("value")
        if value is not None and value.type in ("arrow_function", "function_expression", "function"):
            name = _name_of(node, "name")
            if name:
                syms.append(Symbol("f", name, f"{name}{_params(value)}{_ret(value)}",
                                   node.start_point[0] + 1))
        return
    for child in node.children:
        _walk(child, syms, parent)


def try_parse(ext, text):
    """Exact parse via tree-sitter, or None to signal regex fallback."""
    lang = _language(ext)
    if lang is None:
        return None
    try:
        import tree_sitter
        tree = tree_sitter.Parser(lang).parse(text.encode("utf-8"))
        syms = []
        _walk(tree.root_node, syms, "")
        return syms
    except Exception:
        return None
