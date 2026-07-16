# Codemap Format Specification (v1)

The map is deliberately NOT JSON: braces, quotes, and repeated keys roughly
double the token cost of the same information. This line format carries full
symbol data at ~40–60% of the equivalent JSON tokens.

## Layout

```
# codemap v1 | root: acme-api | generated: 2026-07-16T09:12Z | files: 214 | symbols: 1893 | ~3900 tokens
src/auth/session.py
  c SessionManager : BaseManager  @38 x12
    m refresh(self, user_id, force=False) -> Token  @41 x12
    m invalidate(self, user_id) -> None  @67 x4
  f hash_token(raw: str) -> str  @102 x9
src/billing/Invoice.php
  c InvoiceBuilder : AbstractBuilder, Arrayable  @14 x21
    m addLine(Item $item, int $qty = 1): self  @28 x21
src/web/cart.ts
  f applyDiscount(cart: Cart, code: string): Cart  @55 x7
src/legacy/old_report.py  (+9 symbols, collapsed)
```

## Grammar

| Element | Meaning |
|---------|---------|
| unindented line | file path, relative to root, stated once per group |
| `c Name : Base` | class (with superclass / implemented interfaces after `:`) |
| `i Name` | interface or trait |
| `m sig` | method — indented under its class |
| `f sig` | top-level function |
| `@N` | definition line number |
| `xN` | reference count across the repo (omitted when 0) — the ranking signal |
| `(+N symbols, collapsed)` | file trimmed to fit the token budget; use `query --deep` or `scope` to expand |

## Query syntax

- `codemap.py query <term>` — case-insensitive match over symbol lines; prints
  each hit under its file header.
- `--deep` — re-parses the matching files and prints their full symbol lists
  (use for collapsed files or when you need every method of a class).
- `codemap.py scope <dir>` — builds a standalone deeper map for one subtree.

## Writing a new parser

`parse(text) -> list[Symbol]` where `Symbol(kind, name, signature, line,
parent="", base="")`. For brace-delimited languages, use
`parsers.scan_braced(text, decl_re, members, tops)` and supply only regexes —
see `javascript.py` (52 lines) or `php.py` (40 lines) as the reference
implementations. Register extensions in `parsers/__init__.py::EXTENSIONS`.
Precision expectations: the map locates and ranks symbols; it does not need to
be a compiler. String-literal braces and multi-line signatures may cause minor
imprecision — acceptable at map level, and a parser can upgrade to tree-sitter
later without changing its interface.
