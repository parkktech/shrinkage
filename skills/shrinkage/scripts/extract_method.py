#!/usr/bin/env python3
"""extract_method — scripted C1/C9 method surgery (extract → check → remove →
wire) across the plugin's language matrix, so merges never hand-slice code.

  find    <file> <method>                     locate the span (docs+attrs+body)
  check   <method> <fileA> <fileB> [...]      identity verdict across hosts:
                                              identical / indent-shifted /
                                              comment-only / DIVERGENT (exit 3)
  extract <file> <method> --to DEST           copy byte-exactly into DEST
          [--trait Name] [--namespace NS]     (PHP trait scaffold)
          [--package NAME]                    (Go scaffold)
  remove  <file> <method>                     delete the span from a host
  wire    <file> --use '\\FQ\\Trait'          PHP: class-body `use Trait;`
          --import '<verbatim line>'          Py/JS/TS/Java/C#/Kotlin/Go/Rust:
                                              insert after the last import
          --mixin 'pkg.mod.ClassName'         Python: import + first class bases

Engines — exactness is the contract, per language:
- PHP/.phtml, Java, C#, Kotlin, Go, Rust: brace-family tokenizers with
  per-language string/comment rules (C# @"..."/$"..." and text blocks refused;
  Rust lifetimes disambiguated from char literals, nested /* */ handled, raw
  strings refused; Go backtick raw strings handled; heredocs refused).
- Python: stdlib `ast` — exact spans (decorators + leading comments included);
  the comment-only verdict is AST-identity with docstrings stripped.
- JS/TS: tree-sitter (the plugin's optional exact engine). Absent → loud
  refusal with the install hint, never a guess. Class methods are refused for
  extract (`this`-binding is behavior, not mechanics).
- Templates (Twig/Blade markup/Vue/...): not method surgery — dedupe there is
  partial/component extraction; refused with that guidance.
Every mutation is built whole and sanity-checked (balance / re-parse) before a
single byte is written; a failed check writes NOTHING.
Exit: 0 ok/identical(-ish) · 2 refused/precondition · 3 divergent.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class Refuse(Exception):
    pass


def die(code, msg):
    sys.stderr.write(msg.rstrip("\n") + "\n")
    sys.exit(code)


# ---------------------------------------------------------------- brace family

BRACE_CFGS = {
    "php": dict(
        method_re=r"^[ \t]*(?:(?:public|protected|private|static|final|abstract)\s+)*function\s+&?{name}\s*\(",
        attr_res=[r"^[ \t]*#\["], doc_block=True, doc_line_prefixes=[],
        line_seqs=[("//", None), ("#", "[")], sq="string", bq=False, nested_block=False,
        refuse=[("<<<", "heredoc/nowdoc")],
        import_re=r"^use\s+[\w\\]+", insert="brace",
    ),
    "java": dict(
        method_re=r"^[ \t]*(?:(?:public|protected|private|static|final|abstract|synchronized|native|default|strictfp)\s+)*(?:<[^>\n]+>\s+)?[\w<>\[\],.?]+\s+{name}\s*\(",
        attr_res=[r"^[ \t]*@\w"], doc_block=True, doc_line_prefixes=["//"],
        line_seqs=[("//", None)], sq="string", bq=False, nested_block=False,
        refuse=[('"""', "text block")],
        import_re=r"^import\s+", insert="brace",
    ),
    "csharp": dict(
        method_re=r"^[ \t]*(?:(?:public|protected|private|internal|static|sealed|abstract|virtual|override|async|partial|extern|new|readonly)\s+)*[\w<>\[\],.?]+\s+{name}\s*[<(]",
        attr_res=[r"^[ \t]*\["], doc_block=True, doc_line_prefixes=["///"],
        line_seqs=[("//", None)], sq="string", bq=False, nested_block=False,
        refuse=[('@"', "verbatim string"), ('$"', "interpolated string"), ('"""', "raw string")],
        import_re=r"^using\s+", insert="brace",
    ),
    "kotlin": dict(
        method_re=r"^[ \t]*(?:(?:public|private|protected|internal|open|override|suspend|inline|tailrec|operator|infix|external|actual|expect|final|abstract)\s+)*fun\s+(?:<[^>\n]+>\s+)?(?:[\w?<>.]+\.)?{name}\s*\(",
        attr_res=[r"^[ \t]*@\w"], doc_block=True, doc_line_prefixes=["//"],
        line_seqs=[("//", None)], sq="string", bq=False, nested_block=False,
        refuse=[('"""', "raw string")],
        import_re=r"^import\s+", insert="brace",
    ),
    "go": dict(
        method_re=r"^func\s+(?:\([^)]*\)\s+)?{name}\s*\(",
        attr_res=[], doc_block=False, doc_line_prefixes=["//"],
        line_seqs=[("//", None)], sq="string", bq=True, nested_block=False,
        refuse=[],
        import_re=r"^import\s|^\t\"|^    \"", insert="eof",
    ),
    "rust": dict(
        method_re=r"^[ \t]*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+|const\s+|unsafe\s+|extern\s+\"[^\"]*\"\s+)*fn\s+{name}\s*[<(]",
        attr_res=[r"^[ \t]*#\["], doc_block=False, doc_line_prefixes=["///", "//"],
        line_seqs=[("//", None)], sq="lifetime", bq=False, nested_block=True,
        refuse=[('r#"', "raw string"), ('r"', "raw string")],
        import_re=r"^use\s+", insert="eof",
    ),
}

EXT_ENGINE = {
    ".php": "php", ".phtml": "php", ".java": "java", ".cs": "csharp",
    ".kt": "kotlin", ".kts": "kotlin", ".go": "go", ".rs": "rust",
    ".py": "python",
    ".js": "js", ".jsx": "js", ".mjs": "js", ".ts": "js", ".tsx": "js",
}

TEMPLATE_EXTS = {".twig", ".vue", ".svelte", ".astro", ".hbs", ".mustache",
                 ".ejs", ".j2", ".jinja", ".jinja2", ".tpl", ".latte", ".erb",
                 ".liquid", ".blade"}


def engine_for(path):
    ext = Path(path).suffix.lower()
    if str(path).endswith(".blade.php"):
        raise Refuse(f"{path} is a Blade template — template dedupe is partial/"
                     "component extraction (manual, gated by view:cache), not "
                     "method surgery.")
    if ext in TEMPLATE_EXTS:
        raise Refuse(f"{path} is a template — dedupe there is partial/component/"
                     "include extraction (manual, gated by the framework's "
                     "template compile), not method surgery.")
    eng = EXT_ENGINE.get(ext)
    if eng is None:
        raise Refuse(f"{path}: unsupported extension for scripted surgery — run "
                     "the check→extract→remove→wire loop manually (verify "
                     "identity across hosts BEFORE deleting any copy).")
    return eng


def _is_char_lit(text, i):
    """Rust: is the ' at i a char literal ('a', '\\n') rather than a lifetime?"""
    if i + 2 < len(text) and text[i + 1] == "\\":
        j = text.find("'", i + 2)
        return j != -1 and j <= i + 4
    return i + 2 < len(text) and text[i + 2] == "'"


def _states(text, cfg):
    """Per-char state: code | sq | dq | bq | line | block. Refuses on the
    language's un-sliceable literals (heredoc, C# interpolation, Rust raw)."""
    out = [None] * len(text)
    i, n, st, depth = 0, len(text), "code", 0
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if st == "code":
            for tok, why in cfg["refuse"]:
                if text.startswith(tok, i):
                    raise Refuse(f"{why} ({tok!r}) in range — refuse to slice; "
                                 "handle this method manually.")
            line_hit = False
            for seq, notf in cfg["line_seqs"]:
                if text.startswith(seq, i) and (notf is None or not text.startswith(notf, i + len(seq))):
                    st = "line"; out[i] = "line"; line_hit = True
                    break
            if line_hit:
                pass
            elif c == "'" and cfg["sq"] != "none":
                if cfg["sq"] == "lifetime" and not _is_char_lit(text, i):
                    out[i] = "code"                      # a lifetime, not a char
                else:
                    st = "sq"; out[i] = "sq"
            elif c == '"':
                st = "dq"; out[i] = "dq"
            elif c == "`" and cfg["bq"]:
                st = "bq"; out[i] = "bq"
            elif c == "/" and nxt == "*":
                st = "block"; depth = 1; out[i] = "block"
            else:
                out[i] = "code"
        elif st == "sq":
            out[i] = "sq"
            if c == "\\" and i + 1 < n:
                out[i + 1] = "sq"; i += 1
            elif c == "'":
                st = "code"
        elif st == "dq":
            out[i] = "dq"
            if c == "\\" and i + 1 < n:
                out[i + 1] = "dq"; i += 1
            elif c == '"':
                st = "code"
        elif st == "bq":
            out[i] = "bq"
            if c == "`":
                st = "code"
        elif st == "line":
            if c == "\n":
                st = "code"; out[i] = "code"
            else:
                out[i] = "line"
        elif st == "block":
            out[i] = "block"
            if cfg["nested_block"] and c == "/" and nxt == "*":
                depth += 1; out[i + 1] = "block"; i += 1
            elif c == "*" and nxt == "/":
                depth -= 1; out[i + 1] = "block"; i += 1
                if depth == 0:
                    st = "code"
        i += 1
    return out


def _balance(text, cfg):
    st = _states(text, cfg)
    return sum(1 if c == "{" else -1 for i, c in enumerate(text)
               if st[i] == "code" and c in "{}")


def brace_find_span(text, name, cfg):
    lines = text.splitlines(keepends=True)
    pat = re.compile(cfg["method_re"].format(name=re.escape(name)))
    hits = [i for i, l in enumerate(lines) if pat.match(l)]
    if not hits:
        raise Refuse(f"method {name}() not found")
    if len(hits) > 1:
        raise Refuse(f"method {name}() defined more than once (lines "
                     f"{', '.join(str(h + 1) for h in hits)}) — disambiguate manually.")
    sig = hits[0]
    start, j = sig, sig - 1
    while j >= 0 and any(re.match(a, lines[j]) for a in cfg["attr_res"]):
        start = j; j -= 1
    if cfg["doc_block"] and j >= 0 and lines[j].rstrip().endswith("*/"):
        while j >= 0:
            start = j
            if lines[j].lstrip().startswith(("/**", "/*")):
                break
            j -= 1
        else:
            raise Refuse("unterminated doc block above the method")
    elif cfg["doc_line_prefixes"]:
        while j >= 0 and any(lines[j].lstrip().startswith(p) for p in cfg["doc_line_prefixes"]) \
                and lines[j].strip():
            start = j; j -= 1
    off = sum(len(l) for l in lines[:sig])
    st = _states(text, cfg)
    depth, opened, i = 0, False, off
    while i < len(text):
        c = text[i]
        if st[i] == "code":
            if c == ";" and not opened:
                end_off = i; break
            if c == "{":
                depth += 1; opened = True
            elif c == "}":
                depth -= 1
                if opened and depth == 0:
                    end_off = i; break
        i += 1
    else:
        raise Refuse(f"unbalanced braces — {name}() never closes")
    return start, text.count("\n", 0, end_off)


def brace_strip_comments(text, cfg):
    st = _states(text, cfg)
    return "".join(c for i, c in enumerate(text) if st[i] not in ("line", "block"))


# -------------------------------------------------------------- python engine

def _py_defs(tree, name):
    import ast
    out = []

    def walk(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                out.append(child)
            walk(child)
    walk(tree)
    return out


def py_find_span(text, name):
    import ast
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        raise Refuse(f"file does not parse ({e.msg}, line {e.lineno}) — fix it first")
    defs = _py_defs(tree, name)
    if not defs:
        raise Refuse(f"def {name}() not found")
    if len(defs) > 1:
        raise Refuse(f"def {name}() defined more than once (lines "
                     f"{', '.join(str(d.lineno) for d in defs)}) — disambiguate manually.")
    d = defs[0]
    start = min([dec.lineno for dec in d.decorator_list] + [d.lineno]) - 1
    lines = text.splitlines(keepends=True)
    j = start - 1
    while j >= 0 and lines[j].lstrip().startswith("#") and lines[j].strip():
        start = j; j -= 1
    return start, d.end_lineno - 1


def py_norm(block):
    """AST identity with docstrings stripped — comments/formatting/docstrings
    normalize away; any semantic difference survives."""
    import ast
    import textwrap
    try:
        tree = ast.parse(textwrap.dedent(block))
    except SyntaxError:
        return None

    def strip_docs(node):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(getattr(body[0], "value", None), ast.Constant) \
                and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
        for child in ast.iter_child_nodes(node):
            strip_docs(child)
    strip_docs(tree)
    return ast.dump(tree)


def py_sane(text):
    import ast
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


# ---------------------------------------------------------------- js/ts engine

def _js_lang(ext):
    from parsers import ts_engine
    lang = ts_engine._language(".ts" if ext in (".ts", ".tsx") else ".js")
    if lang is None:
        raise Refuse(
            "JS/TS surgery needs the exact engine: pip install tree-sitter "
            "tree-sitter-javascript tree-sitter-typescript (and unset "
            "SHRINKAGE_NO_TREESITTER). Refusing to guess — template literals "
            "and regex literals defeat approximate slicing.")
    return lang


def _js_tree(text, ext):
    import tree_sitter
    lang = _js_lang(ext)
    tree = tree_sitter.Parser(lang).parse(text.encode("utf-8"))
    return tree


def _js_matches(root, name):
    out = []

    def walk(node):
        if node.type in ("function_declaration", "generator_function_declaration",
                         "method_definition"):
            n = node.child_by_field_name("name")
            if n is not None and n.text.decode() == name:
                out.append(node)
        elif node.type == "variable_declarator":
            n = node.child_by_field_name("name")
            v = node.child_by_field_name("value")
            if n is not None and n.text.decode() == name and v is not None \
                    and v.type in ("arrow_function", "function_expression", "function"):
                p = node.parent
                out.append(p if p is not None and p.type == "lexical_declaration" else node)
        for c in node.children:
            walk(c)
    walk(root)
    return out


def js_find_span(text, name, ext):
    tree = _js_tree(text, ext)
    if tree.root_node.has_error:
        raise Refuse("file has parse errors — fix them first")
    hits = _js_matches(tree.root_node, name)
    if not hits:
        raise Refuse(f"function {name}() not found")
    if len(hits) > 1:
        raise Refuse(f"{name}() defined more than once (lines "
                     f"{', '.join(str(h.start_point[0] + 1) for h in hits)}) — disambiguate manually.")
    node = hits[0]
    start = node.start_point[0]
    prev = node.prev_named_sibling
    if prev is not None and prev.type == "comment" and prev.end_point[0] >= start - 1:
        start = prev.start_point[0]
    # include `export` keyword line if the declaration is wrapped
    if node.parent is not None and node.parent.type == "export_statement":
        start = min(start, node.parent.start_point[0])
        node = node.parent
    return start, node.end_point[0], hits[0].type


def js_strip_comments(text, ext):
    tree = _js_tree(text, ext)
    drops = []

    def walk(node):
        if node.type == "comment":
            drops.append((node.start_byte, node.end_byte))
        for c in node.children:
            walk(c)
    walk(tree.root_node)
    b = text.encode("utf-8")
    for s, e in sorted(drops, reverse=True):
        b = b[:s] + b[e:]
    return b.decode("utf-8")


def js_sane(text, ext):
    return not _js_tree(text, ext).root_node.has_error


# ------------------------------------------------------------- shared helpers

def _norm_ws(s):
    return re.sub(r"\s+", "", s)


def _dedent(block):
    lines = [l for l in block.splitlines() if l.strip()]
    if not lines:
        return block
    pad = min(len(l) - len(l.lstrip()) for l in lines)
    return "\n".join(l[pad:] if l.strip() else l for l in block.splitlines())


def find_span(text, name, path):
    eng = engine_for(path)
    ext = Path(path).suffix.lower()
    if eng == "python":
        return py_find_span(text, name)
    if eng == "js":
        s, e, _ = js_find_span(text, name, ext)
        return s, e
    return brace_find_span(text, name, BRACE_CFGS[eng])


def _slice(text, name, path):
    lines = text.splitlines(keepends=True)
    s, e = find_span(text, name, path)
    return s, e, "".join(lines[s:e + 1])


def norm_comment(block, path):
    eng = engine_for(path)
    if eng == "python":
        return py_norm(block)
    if eng == "js":
        return _norm_ws(js_strip_comments(block, Path(path).suffix.lower())
                        if not _js_tree(block, Path(path).suffix.lower()).root_node.has_error
                        else block)
    return _norm_ws(brace_strip_comments(block, BRACE_CFGS[eng]))


def sane(text, path):
    eng = engine_for(path)
    if eng == "python":
        return py_sane(text)
    if eng == "js":
        return js_sane(text, Path(path).suffix.lower())
    return _balance(text, BRACE_CFGS[eng]) == 0


def _write_checked(path, new_text, what):
    if not sane(new_text, path):
        die(2, f"refusing to write {path}: {what} would leave the file "
               "unbalanced/unparseable — nothing was modified.")
    Path(path).write_text(new_text, encoding="utf-8")


# ------------------------------------------------------------------- commands

def cmd_find(path, name):
    text = Path(path).read_text(encoding="utf-8")
    s, e, block = _slice(text, name, path)
    print(f"{path}: {name}() spans lines {s + 1}–{e + 1} ({e - s + 1} lines)")
    sys.stdout.write(block)


def cmd_check(name, paths):
    engines = {engine_for(p) for p in paths}
    if len(engines) > 1:
        die(2, f"hosts span languages ({', '.join(sorted(engines))}) — a merge "
               "across languages is not a merge.")
    blocks = {p: _slice(Path(p).read_text(encoding="utf-8"), name, p)[2] for p in paths}
    ref_path, ref = paths[0], blocks[paths[0]]
    worst = "identical"
    for p in paths[1:]:
        b = blocks[p]
        if b == ref:
            verdict = "identical"
        elif _dedent(b) == _dedent(ref):
            verdict = "identical (indent-shifted)"
        else:
            na, nb = norm_comment(ref, ref_path), norm_comment(b, p)
            if na is not None and na == nb:
                verdict = ("comment/format-only differences "
                           "(pick the surviving docs deliberately)")
            else:
                import difflib
                diff = list(difflib.unified_diff(
                    _dedent(ref).splitlines(), _dedent(b).splitlines(),
                    ref_path, p, lineterm="", n=1))
                print(f"DIVERGENT: {name}() in {p} vs {ref_path} — two copies "
                      "that differ are two BEHAVIORS; find out which is the "
                      "bug before merging.")
                print("\n".join(diff[:12]))
                sys.exit(3)
        print(f"{p}: {verdict}")
        if verdict != "identical":
            worst = verdict
    print(f"verdict: {worst} across {len(paths)} host(s) — safe to merge"
          + (" (byte-exact)" if worst == "identical" else ""))


def _insert_before_last_brace(dtext, block, cfg):
    st = _states(dtext, cfg)
    closes = [i for i, c in enumerate(dtext) if c == "}" and st[i] == "code"]
    if not closes:
        raise Refuse("no class/trait body to insert into")
    at = dtext.rfind("\n", 0, closes[-1]) + 1
    return dtext[:at] + "\n" + block + dtext[at:]


def cmd_extract(path, name, dest, trait=None, namespace=None, package=None):
    eng = engine_for(path)
    if engine_for(dest) != eng:
        raise Refuse(f"destination {dest} is a different language than {path}")
    src_text = Path(path).read_text(encoding="utf-8")
    if eng == "js":
        _, _, kind = js_find_span(src_text, name, Path(path).suffix.lower())
        if kind == "method_definition":
            raise Refuse("JS class methods are not extractable mechanically — "
                         "`this`-binding makes the move a behavior change, not "
                         "mechanics. Restructure by hand with tests.")
    s, e, block = _slice(src_text, name, path)
    dest_p = Path(dest)
    if dest_p.exists():
        dtext = dest_p.read_text(encoding="utf-8")
        if eng in BRACE_CFGS and BRACE_CFGS[eng]["insert"] == "brace":
            new = _insert_before_last_brace(dtext, block, BRACE_CFGS[eng])
        elif eng == "python" and re.match(r"[ \t]", block):
            import ast
            tree = ast.parse(dtext)
            last = tree.body[-1] if tree.body else None
            if not isinstance(last, ast.ClassDef):
                raise Refuse("indented (method) block needs the home file to "
                             "END with a class to insert into — or extract a "
                             "module-level function instead.")
            lines = dtext.splitlines(keepends=True)
            new = "".join(lines[:last.end_lineno]) + "\n" + block + "".join(lines[last.end_lineno:])
        else:
            new = dtext.rstrip("\n") + "\n\n\n" + block
            if eng == "js" and not re.search(rf"\bexport\b.*\b{re.escape(name)}\b", new):
                new = new.rstrip("\n") + f"\n\nexport {{ {name} }};\n"
        _write_checked(dest, new, "insert")
        print(f"extracted {name}() (lines {s + 1}–{e + 1}) into existing {dest}")
        return
    # scaffold a NEW home, per language
    if eng == "php":
        tname = trait or dest_p.stem
        if not namespace:
            m = re.search(r"^namespace\s+([\w\\]+)\s*;", src_text, re.M)
            if m and dest_p.parent.resolve() == Path(path).parent.resolve():
                namespace = m.group(1)
            else:
                die(2, "scaffolding a NEW home in a different directory needs "
                       "--namespace (PSR-4 guessing is how wrong imports happen).")
        scaffold = ("<?php\n\ndeclare(strict_types=1);\n\n"
                    f"namespace {namespace};\n\n"
                    f"/**\n * {tname} — shared home extracted (C9) from "
                    f"{Path(path).name} by extract_method.py.\n */\n"
                    f"trait {tname}\n{{\n" + block + "}\n")
    elif eng == "python":
        if re.match(r"[ \t]", block):
            cname = trait or dest_p.stem.title().replace("_", "")
            scaffold = (f'"""{cname} — shared home extracted (C9) from '
                        f'{Path(path).name} by extract_method.py."""\n\n\n'
                        f"class {cname}:\n" + block)
        else:
            scaffold = (f'"""Shared home extracted (C9) from {Path(path).name} '
                        'by extract_method.py."""\n\n' + block)
    elif eng == "go":
        if not package:
            die(2, "a NEW Go home needs --package <name>.")
        scaffold = f"package {package}\n\n" + block
    elif eng in ("kotlin", "rust"):
        scaffold = block if not re.match(r"[ \t]", block) else None
        if scaffold is None:
            die(2, f"indented (member) block — {eng} member extraction needs an "
                   "EXISTING home type; create the shell, then extract into it.")
    elif eng == "js":
        scaffold = ("// shared home extracted (C9) by extract_method.py\n" + block
                    + ("" if block.lstrip().startswith("export")
                       else f"\nexport {{ {name} }};\n"))
    else:
        die(2, f"{eng}: no trait/mixin concept to scaffold — create the home "
               "shell (utility class / interface) yourself, then extract into it.")
    dest_p.parent.mkdir(parents=True, exist_ok=True)
    _write_checked(dest, scaffold, "scaffold")
    print(f"extracted {name}() (lines {s + 1}–{e + 1}) into new {dest}")


def cmd_remove(path, name):
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    s, e = find_span(text, name, path)
    before, after = lines[:s], lines[e + 1:]
    if before and after and before[-1].strip() == "" and after[0].strip() == "":
        after = after[1:]
    _write_checked(path, "".join(before + after), "removal")
    print(f"removed {name}() from {path} (lines {s + 1}–{e + 1}, {e - s + 1} lines)")


PHP_DECL = re.compile(r"^[ \t]*(?:abstract\s+|final\s+|readonly\s+)*(?:class|trait|enum)\s+\w+")


def cmd_wire_php(path, fq_trait):
    text = Path(path).read_text(encoding="utf-8")
    short = fq_trait.strip("\\").split("\\")[-1]
    lines = text.splitlines(keepends=True)
    decl = next((i for i, l in enumerate(lines) if PHP_DECL.match(l)), None)
    if decl is None:
        die(2, f"{path}: no class/trait/enum declaration found")
    body = "".join(lines[decl:])
    if re.search(r"^\s*use\s+\\?[\w\\]*" + re.escape(short) + r"\s*;", body, re.M):
        print(f"{path}: use {short}; already wired — no change")
        return
    off = sum(len(l) for l in lines[:decl])
    st = _states(text, BRACE_CFGS["php"])
    try:
        brace = next(i for i in range(off, len(text)) if text[i] == "{" and st[i] == "code")
    except StopIteration:
        die(2, f"{path}: class body never opens")
    at = text.find("\n", brace) + 1
    new = text[:at] + f"    use \\{fq_trait.strip(chr(92))};\n\n" + text[at:]
    _write_checked(path, new, "wire")
    print(f"wired `use \\{fq_trait.strip(chr(92))};` into {path}")


def cmd_wire_import(path, line):
    """Insert a verbatim import line after the file's last import (Python /
    JS-TS / Java / C# / Kotlin / Go / Rust). Idempotent by exact-line match."""
    eng = engine_for(path)
    text = Path(path).read_text(encoding="utf-8")
    if line.strip() in (l.strip() for l in text.splitlines()):
        print(f"{path}: import already present — no change")
        return
    if eng == "python":
        imp = re.compile(r"^(?:import\s+\w|from\s+[\w.]+\s+import\b)")
    elif eng in BRACE_CFGS:
        imp = re.compile(BRACE_CFGS[eng]["import_re"])
    else:  # js
        imp = re.compile(r"^import\b|^const\s+\w+\s*=\s*require\(")
    lines = text.splitlines(keepends=True)
    last = max((i for i, l in enumerate(lines) if imp.match(l)), default=None)
    if last is None:
        anchor = next((i for i, l in enumerate(lines)
                       if l.strip() and not l.lstrip().startswith(("<?php", "#", "//", "/*", "*", '"""'))
                       and not re.match(r"^(?:package|namespace)\b", l)), 0)
        at = anchor
    else:
        at = last + 1
    lines.insert(at, line.rstrip("\n") + "\n")
    _write_checked(path, "".join(lines), "wire")
    print(f"wired `{line.strip()}` into {path}")


def cmd_wire_mixin(path, dotted):
    """Python: import the mixin and add it FIRST in the first class's bases."""
    if engine_for(path) != "python":
        die(2, "--mixin is Python-only (use --use for PHP traits, --import elsewhere).")
    mod, _, cls = dotted.rpartition(".")
    if not mod:
        die(2, "--mixin needs a dotted path: pkg.module.ClassName")
    import ast
    text = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(text)
    cdef = next((n for n in tree.body if isinstance(n, ast.ClassDef)), None)
    if cdef is None:
        die(2, f"{path}: no top-level class to mix into")
    lines = text.splitlines(keepends=True)
    header = lines[cdef.lineno - 1]
    if not header.rstrip().endswith(":"):
        die(2, f"{path}: class signature spans multiple lines — wire the mixin by hand.")
    if re.search(rf"\b{re.escape(cls)}\b", header):
        print(f"{path}: {cls} already in bases — no change")
        return
    m = re.match(rf"^([ \t]*class\s+{cdef.name}\s*)(\(([^)]*)\))?\s*:\s*$", header)
    if not m:
        die(2, f"{path}: could not parse the class header — wire the mixin by hand.")
    bases = m.group(3)
    new_header = (f"{m.group(1)}({cls}, {bases}):\n" if bases and bases.strip()
                  else f"{m.group(1)}({cls}):\n")
    lines[cdef.lineno - 1] = new_header
    Path(path).write_text("".join(lines), encoding="utf-8")
    cmd_wire_import(path, f"from {mod} import {cls}")
    print(f"mixed {cls} into class {cdef.name} in {path}")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd, rest = a[0], a[1:]

    def opt(name):
        return rest[rest.index(name) + 1] if name in rest else None
    try:
        if cmd == "find" and len(rest) >= 2:
            engine_for(rest[0])
            cmd_find(rest[0], rest[1])
        elif cmd == "check" and len(rest) >= 3:
            hosts = [r for r in rest[1:] if not r.startswith("--")]
            cmd_check(rest[0], hosts)
        elif cmd == "extract" and len(rest) >= 2 and opt("--to"):
            cmd_extract(rest[0], rest[1], opt("--to"), opt("--trait"),
                        opt("--namespace"), opt("--package"))
        elif cmd == "remove" and len(rest) >= 2:
            engine_for(rest[0])
            cmd_remove(rest[0], rest[1])
        elif cmd == "wire" and len(rest) >= 1 and (opt("--use") or opt("--import") or opt("--mixin")):
            if opt("--use"):
                if engine_for(rest[0]) != "php":
                    die(2, "--use wires PHP traits; use --import (verbatim line) "
                           "or --mixin (Python) for other languages.")
                cmd_wire_php(rest[0], opt("--use"))
            elif opt("--mixin"):
                cmd_wire_mixin(rest[0], opt("--mixin"))
            else:
                cmd_wire_import(rest[0], opt("--import"))
        else:
            die(2, "usage:\n  extract_method.py find <file> <method>\n"
                   "  extract_method.py check <method> <fileA> <fileB> [...]\n"
                   "  extract_method.py extract <file> <method> --to DEST "
                   "[--trait Name] [--namespace NS] [--package NAME]\n"
                   "  extract_method.py remove <file> <method>\n"
                   "  extract_method.py wire <file> --use '\\FQ\\Trait' | "
                   "--import '<line>' | --mixin 'pkg.mod.Class'")
    except Refuse as r:
        die(2, f"refused: {r}")
    except OSError as o:
        die(2, str(o))


if __name__ == "__main__":
    main()
