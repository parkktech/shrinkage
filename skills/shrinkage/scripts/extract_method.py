#!/usr/bin/env python3
"""extract_method — scripted C1/C9 method surgery for PHP (extract → check →
remove → wire), so merges never hand-slice code by line math again.

The loop this packages is the C9 transform exactly as field-proven:

  find    <file> <method>                     locate the span (docblock+attrs+
                                              body, brace-matched) — dry look
  check   <method> <fileA> <fileB> [...]      identity verdict across hosts:
                                              identical / indent-shifted /
                                              comment-only / DIVERGENT (exit 3)
  extract <file> <method> --to DEST           copy the method byte-exactly into
          [--trait Name] [--namespace NS]     DEST (scaffolds a trait if new)
  remove  <file> <method>                     delete the span from a host
  wire    <file> --use '\\FQ\\TraitName'      insert `use TraitName;` first in
                                              the class body (idempotent)

Safety properties (the reason this exists — a hand-rolled version aborted
mid-flight on an indentation-slicing bug):
- Brace matching runs on a real tokenizer (strings, escapes, //, #, /* */), so
  a `{` inside "{$var}", a comment, or a string literal can never fool the span.
- Heredoc/nowdoc in a method → refuse loudly (exit 2) rather than guess.
- Ambiguous name (method defined twice in the file) → refuse with both lines.
- Every mutation is atomic: the new text is built whole and only written after
  a full-file brace-balance sanity check; a failed check writes NOTHING.
Exit: 0 ok/identical(-ish) · 2 refused/precondition · 3 divergent.
"""
import re
import sys
from pathlib import Path

METHOD_RE_T = r"^[ \t]*(?:(?:public|protected|private|static|final|abstract)\s+)*function\s+&?{name}\s*\("
DECL_RE = re.compile(r"^[ \t]*(?:abstract\s+|final\s+|readonly\s+)*(?:class|trait|enum)\s+\w+")


class Refuse(Exception):
    pass


def die(code, msg):
    sys.stderr.write(msg.rstrip("\n") + "\n")
    sys.exit(code)


PHP_EXTS = {".php", ".phtml"}


def _require_php(*paths):
    """PHP-ONLY, mechanically enforced. The safety guarantee comes from
    language-exact tokenization; this tokenizer is actively WRONG for other
    languages (JS: backtick templates with ${} braces, regex literals, `#`
    private fields — all would fool the span). Other languages get their own
    exact engines (Python via ast, JS/TS via tree-sitter) — until then, refuse
    loudly rather than slice wrong quietly."""
    for p in paths:
        if Path(p).suffix.lower() not in PHP_EXTS:
            raise Refuse(
                f"{p} is not a PHP file — extract_method is PHP-only (its "
                "tokenizer would mis-slice other languages). For non-PHP "
                "merges, apply the check→extract→remove→wire loop manually "
                "with the identity verification done by eye + tests.")


def _states(text):
    """Per-char state: 'code' | 'sq' | 'dq' | 'line' | 'block'. Refuses on
    heredoc/nowdoc (`<<<`) — guessing there is how surgery goes wrong."""
    out = [None] * len(text)
    i, n, st = 0, len(text), "code"
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if st == "code":
            if c == "'":
                st = "sq"; out[i] = "sq"
            elif c == '"':
                st = "dq"; out[i] = "dq"
            elif c == "/" and nxt == "/":
                st = "line"; out[i] = "line"
            elif c == "#" and nxt != "[":          # #[Attr] is code, # comment isn't
                st = "line"; out[i] = "line"
            elif c == "/" and nxt == "*":
                st = "block"; out[i] = "block"
            elif c == "<" and text[i:i + 3] == "<<<":
                raise Refuse("heredoc/nowdoc (<<<) in range — refuse to slice; "
                             "extract this method manually.")
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
        elif st == "line":
            if c == "\n":
                st = "code"; out[i] = "code"
            else:
                out[i] = "line"
        elif st == "block":
            out[i] = "block"
            if c == "*" and nxt == "/":
                out[i + 1] = "block"; i += 1; st = "code"
        i += 1
    return out


def _balance(text):
    st = _states(text)
    return sum(1 if c == "{" else -1 for i, c in enumerate(text)
               if st[i] == "code" and c in "{}")


def find_span(text, name):
    """(start_line, end_line) 0-based inclusive: attributes + docblock +
    signature + brace-matched body. Refuses ambiguity and heredocs."""
    lines = text.splitlines(keepends=True)
    pat = re.compile(METHOD_RE_T.format(name=re.escape(name)))
    hits = [i for i, l in enumerate(lines) if pat.match(l)]
    if not hits:
        raise Refuse(f"method {name}() not found")
    if len(hits) > 1:
        raise Refuse(f"method {name}() defined more than once (lines "
                     f"{', '.join(str(h + 1) for h in hits)}) — disambiguate manually.")
    sig = hits[0]
    # walk back over docblock, then attribute lines directly above the signature
    start = sig
    j = sig - 1
    while j >= 0 and lines[j].lstrip().startswith("#["):
        start = j; j -= 1
    if j >= 0 and lines[j].rstrip().endswith("*/"):
        while j >= 0:
            start = j
            if lines[j].lstrip().startswith("/**") or lines[j].lstrip().startswith("/*"):
                break
            j -= 1
        else:
            raise Refuse("unterminated docblock above the method")
    # brace-match from the signature onward, tokenizer-guided
    off = sum(len(l) for l in lines[:sig])
    st = _states(text)
    depth, opened, i = 0, False, off
    while i < len(text):
        c = text[i]
        if st[i] == "code":
            if c == ";" and not opened:
                end_off = i; break              # abstract/interface: no body
            if c == "{":
                depth += 1; opened = True
            elif c == "}":
                depth -= 1
                if opened and depth == 0:
                    end_off = i; break
        i += 1
    else:
        raise Refuse(f"unbalanced braces — {name}() never closes")
    end = text.count("\n", 0, end_off)
    return start, end


def _slice(text, name):
    lines = text.splitlines(keepends=True)
    s, e = find_span(text, name)
    return s, e, "".join(lines[s:e + 1])


def _strip_comments(text):
    st = _states(text)
    return "".join(c for i, c in enumerate(text) if st[i] not in ("line", "block"))


def _norm_comment(text):
    return re.sub(r"\s+", "", _strip_comments(text))


def _dedent(block):
    lines = [l for l in block.splitlines() if l.strip()]
    if not lines:
        return block
    pad = min(len(l) - len(l.lstrip()) for l in lines)
    return "\n".join(l[pad:] if l.strip() else l for l in block.splitlines())


def cmd_find(path, name):
    text = Path(path).read_text(encoding="utf-8")
    s, e, block = _slice(text, name)
    print(f"{path}: {name}() spans lines {s + 1}–{e + 1} ({e - s + 1} lines)")
    sys.stdout.write(block)


def cmd_check(name, paths):
    blocks = {}
    for p in paths:
        _, _, blocks[p] = _slice(Path(p).read_text(encoding="utf-8"), name)
    ref_path, ref = paths[0], blocks[paths[0]]
    worst = "identical"
    for p in paths[1:]:
        b = blocks[p]
        if b == ref:
            verdict = "identical"
        elif _dedent(b) == _dedent(ref):
            verdict = "identical (indent-shifted)"
        elif _norm_comment(b) == _norm_comment(ref):
            verdict = "comment-only differences (pick the surviving docblock deliberately)"
        else:
            import difflib
            diff = list(difflib.unified_diff(
                _strip_comments(ref).splitlines(), _strip_comments(b).splitlines(),
                ref_path, p, lineterm="", n=1))
            print(f"DIVERGENT: {name}() in {p} vs {ref_path} — two copies that "
                  "differ are two BEHAVIORS; find out which is the bug before merging.")
            print("\n".join(diff[:12]))
            sys.exit(3)
        print(f"{p}: {verdict}")
        if verdict != "identical":
            worst = verdict
    print(f"verdict: {worst} across {len(paths)} host(s) — safe to merge"
          + (" (byte-exact)" if worst == "identical" else ""))


def _write_checked(path, new_text, what):
    if _balance(new_text) != 0:
        die(2, f"refusing to write {path}: {what} would leave unbalanced braces "
               "— nothing was modified.")
    Path(path).write_text(new_text, encoding="utf-8")


def cmd_extract(path, name, dest, trait=None, namespace=None):
    src_text = Path(path).read_text(encoding="utf-8")
    s, e, block = _slice(src_text, name)
    dest_p = Path(dest)
    if dest_p.exists():
        dtext = dest_p.read_text(encoding="utf-8")
        st = _states(dtext)
        closes = [i for i, c in enumerate(dtext) if c == "}" and st[i] == "code"]
        if not closes:
            die(2, f"{dest}: no class/trait body to insert into")
        at = dtext.rfind("\n", 0, closes[-1]) + 1
        new = dtext[:at] + "\n" + block + dtext[at:]
        _write_checked(dest, new, "insert")
        print(f"extracted {name}() (lines {s + 1}–{e + 1}) into existing {dest}")
        return
    tname = trait or dest_p.stem
    if not namespace:
        m = re.search(r"^namespace\s+([\w\\]+)\s*;", src_text, re.M)
        if m and dest_p.parent.resolve() == Path(path).parent.resolve():
            namespace = m.group(1)
        else:
            die(2, "scaffolding a NEW home in a different directory needs "
                   "--namespace (PSR-4 guessing is how wrong imports happen).")
    scaffold = (
        "<?php\n\ndeclare(strict_types=1);\n\n"
        f"namespace {namespace};\n\n"
        f"/**\n * {tname} — shared home extracted (C9) from "
        f"{Path(path).name} by extract_method.py.\n */\n"
        f"trait {tname}\n{{\n" + block + "}\n")
    dest_p.parent.mkdir(parents=True, exist_ok=True)
    _write_checked(dest, scaffold, "scaffold")
    print(f"extracted {name}() (lines {s + 1}–{e + 1}) into new trait "
          f"\\{namespace}\\{tname} at {dest}")


def cmd_remove(path, name):
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    s, e = find_span(text, name)
    before, after = lines[:s], lines[e + 1:]
    # collapse the double blank a mid-class removal leaves behind
    if before and after and before[-1].strip() == "" and after and after[0].strip() == "":
        after = after[1:]
    _write_checked(path, "".join(before + after), "removal")
    print(f"removed {name}() from {path} (lines {s + 1}–{e + 1}, {e - s + 1} lines)")


def cmd_wire(path, fq_trait):
    text = Path(path).read_text(encoding="utf-8")
    short = fq_trait.strip("\\").split("\\")[-1]
    lines = text.splitlines(keepends=True)
    decl = next((i for i, l in enumerate(lines) if DECL_RE.match(l)), None)
    if decl is None:
        die(2, f"{path}: no class/trait/enum declaration found")
    body = "".join(lines[decl:])
    if re.search(r"^\s*use\s+\\?[\w\\]*" + re.escape(short) + r"\s*;", body, re.M):
        print(f"{path}: use {short}; already wired — no change")
        return
    off = sum(len(l) for l in lines[:decl])
    st = _states(text)
    try:
        brace = next(i for i in range(off, len(text))
                     if text[i] == "{" and st[i] == "code")
    except StopIteration:
        die(2, f"{path}: class body never opens")
    at = text.find("\n", brace) + 1
    new = text[:at] + f"    use \\{fq_trait.strip(chr(92))};\n\n" + text[at:]
    _write_checked(path, new, "wire")
    print(f"wired `use \\{fq_trait.strip(chr(92))};` into {path}")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd, rest = a[0], a[1:]

    def opt(name):
        return rest[rest.index(name) + 1] if name in rest else None
    try:
        if cmd == "find" and len(rest) >= 2:
            _require_php(rest[0])
            cmd_find(rest[0], rest[1])
        elif cmd == "check" and len(rest) >= 3:
            hosts = [r for r in rest[1:] if not r.startswith("--")]
            _require_php(*hosts)
            cmd_check(rest[0], hosts)
        elif cmd == "extract" and len(rest) >= 2 and opt("--to"):
            _require_php(rest[0], opt("--to"))
            cmd_extract(rest[0], rest[1], opt("--to"), opt("--trait"), opt("--namespace"))
        elif cmd == "remove" and len(rest) >= 2:
            _require_php(rest[0])
            cmd_remove(rest[0], rest[1])
        elif cmd == "wire" and len(rest) >= 1 and opt("--use"):
            _require_php(rest[0])
            cmd_wire(rest[0], opt("--use"))
        else:
            die(2, "usage:\n  extract_method.py find <file> <method>\n"
                   "  extract_method.py check <method> <fileA> <fileB> [...]\n"
                   "  extract_method.py extract <file> <method> --to DEST "
                   "[--trait Name] [--namespace NS]\n"
                   "  extract_method.py remove <file> <method>\n"
                   "  extract_method.py wire <file> --use '\\FQ\\TraitName'")
    except Refuse as r:
        die(2, f"refused: {r}")
    except OSError as o:
        die(2, str(o))


if __name__ == "__main__":
    main()
