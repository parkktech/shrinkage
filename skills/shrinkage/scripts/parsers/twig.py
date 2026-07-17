"""Twig adapter (Drupal, Symfony) — blocks and macros.

Templates define two reusable-unit kinds worth mapping: `{% macro name(args) %}`
(callable — prime C1/C9 consolidation targets across themes) and
`{% block name %}` (named override points — the "extend, don't copy" seam).
Everything else in a template matters as *references*, which the codemap's
identifier counter picks up automatically once .twig files are indexed.
"""
import re

from parsers import Symbol

MACRO = re.compile(r"\{%-?\s*macro\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)")
BLOCK = re.compile(r"\{%-?\s*block\s+(?P<name>\w+)")


def parse(text):
    syms = []
    for n, line in enumerate(text.splitlines(), 1):
        m = MACRO.search(line)
        if m:
            syms.append(Symbol("f", m.group("name"),
                               f"macro {m.group('name')}({m.group('params').strip()})", n))
            continue
        b = BLOCK.search(line)
        if b:
            syms.append(Symbol("f", b.group("name"), f"block {b.group('name')}", n))
    return syms
