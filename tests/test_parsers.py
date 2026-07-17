"""Parser adapters: every supported language yields the expected symbols."""
from parsers import parse_text


def names(path, text, kind=None):
    syms = parse_text(path, text)
    return {(s.kind, s.parent, s.name) for s in syms
            if kind is None or s.kind == kind}


def test_python():
    src = "class A(Base):\n    def m(self, x=1):\n        pass\n\ndef f(y):\n    return y\n"
    got = names("a.py", src)
    assert ("c", "", "A") in got and ("m", "A", "m") in got and ("f", "", "f") in got


def test_javascript_class_arrow_and_function():
    src = ("export class Cart extends Base {\n  total(items) {\n    return 1;\n  }\n}\n"
           "export function fmt(c) {\n}\n"
           "const sum = (xs) => xs.length;\n")
    got = names("a.js", src)
    assert ("c", "", "Cart") in got and ("m", "Cart", "total") in got
    assert ("f", "", "fmt") in got and ("f", "", "sum") in got


def test_php_psr12_next_line_brace_and_visibility():
    src = ("<?php\nclass Invoice extends Base implements Arrayable\n{\n"
           "    public function addLine(Item $i, int $q = 1): self\n    {\n    }\n}\n"
           "function money(float $a): string\n{\n}\n")
    got = names("a.php", src)
    assert ("c", "", "Invoice") in got and ("m", "Invoice", "addLine") in got
    assert ("f", "", "money") in got


def test_go_receiver_methods_and_brace_in_string():
    src = ('package main\n\ntype Server struct {\n\tport int\n}\n\n'
           'func (s *Server) Start(p int) error {\n\tfmt.Println("{")\n\treturn nil\n}\n\n'
           'func New(p int) *Server {\n\treturn nil\n}\n')
    got = names("a.go", src)
    assert ("c", "", "Server") in got
    assert ("m", "Server", "Start") in got, "brace inside string must not break tracking"
    assert ("f", "", "New") in got


def test_rust_impl_and_trait_methods():
    src = ("pub struct W {}\npub trait P {\n    fn pay(&self) -> bool;\n}\n"
           "impl W {\n    pub fn new() -> Self {\n        W{}\n    }\n}\n"
           "pub fn free() {}\n")
    got = names("a.rs", src)
    assert ("c", "", "W") in got and ("i", "", "P") in got
    assert ("m", "P", "pay") in got and ("m", "W", "new") in got and ("f", "", "free") in got


def test_java_and_csharp():
    java = ("public class Svc extends Base implements Aud {\n"
            "    public Order create(String s, int q) {\n        return null;\n    }\n}\n")
    cs = ("public sealed class Inv : SvcBase, IInv\n{\n"
          "    public async Task<X> CreateAsync(string id)\n    {\n        return null;\n    }\n}\n")
    j = names("A.java", java)
    c = names("B.cs", cs)
    assert ("c", "", "Svc") in j and ("m", "Svc", "create") in j
    assert ("c", "", "Inv") in c and ("m", "Inv", "CreateAsync") in c


def test_treesitter_parity_when_available():
    import importlib.util
    import os
    if importlib.util.find_spec("tree_sitter") is None or \
       importlib.util.find_spec("tree_sitter_javascript") is None:
        import pytest
        pytest.skip("tree-sitter grammars not installed")
    src = "export class C {\n  m(a) {\n    return a;\n  }\n}\nexport function f(x) {\n}\n"
    os.environ.pop("SHRINKAGE_NO_TREESITTER", None)
    try:
        import parsers.ts_engine as ts
        ts._LANGS.clear()
        exact = {(s.kind, s.parent, s.name) for s in parse_text("a.js", src)}
    finally:
        os.environ["SHRINKAGE_NO_TREESITTER"] = "1"
        ts._LANGS.clear()
    assert ("c", "", "C") in exact and ("m", "C", "m") in exact and ("f", "", "f") in exact
