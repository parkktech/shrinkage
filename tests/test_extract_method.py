"""extract_method.py — tokenizer-guided C1/C9 method surgery (find/check/extract/remove/wire)."""
from conftest import run

import extract_method


def _balanced(text):
    return extract_method._balance(text, extract_method.BRACE_CFGS["php"]) == 0

# A host shaped like the real case: docblock, braces inside strings and
# comments, "{$var}" interpolation — everything that breaks naive line-slicing.
HOST = """<?php

declare(strict_types=1);

namespace App\\Domain\\Trading\\Services;

class {CLS}
{{
    private array $guards = [];

    /**
     * Aggregate results from all fired guards into a single result.
     *
     * @param array $rows guard rows (unbalanced brace in doc: {{ )
     */
    private function aggregateGuardResults(array $rows, string $direction): array
    {{
        $out = ['dir' => $direction, 'brace' => '}}'];   // a } in a string
        foreach ($rows as $r) {{
            // note: closing } in this comment
            $msg = "guard {{$r['name']}} fired";        /* interpolated {{$x}} */
            $out['msgs'][] = $msg;
        }}
        return $out;
    }}

    public function evaluate(array $rows): array
    {{
        return $this->aggregateGuardResults($rows, 'long');
    }}
}}
"""


def _host(repo, cls, fname=None, body_tweak=None, comment_tweak=None):
    text = HOST.replace("{CLS}", cls).replace("{{", "{").replace("}}", "}")
    if body_tweak:
        text = text.replace("'long'", "'short'").replace(
            "$out['msgs'][] = $msg;", "$out['msgs'][] = strtoupper($msg);")
    if comment_tweak:
        text = text.replace("a } in a string", "a } in a string (edited note)")
    p = repo / (fname or f"{cls}.php")
    p.write_text(text)
    return p


def test_find_brace_matches_through_strings_and_comments(repo):
    p = _host(repo, "RiskGuardService")
    code, out = run("extract_method.py", "find", str(p), "aggregateGuardResults", cwd=repo)
    assert code == 0, out
    assert "spans lines 11–25" in out, out            # docblock through closing brace
    assert 'return $out;' in out and "evaluate" not in out, out


def test_check_identical_and_comment_only_and_divergent(repo):
    a = _host(repo, "RiskGuardService")
    b = _host(repo, "BacktestRiskGuardEvaluator")
    code, out = run("extract_method.py", "check", "aggregateGuardResults", str(a), str(b), cwd=repo)
    assert code == 0 and "identical" in out, out
    c = _host(repo, "CommentTwin", comment_tweak=True)
    code, out = run("extract_method.py", "check", "aggregateGuardResults", str(a), str(c), cwd=repo)
    assert code == 0 and "comment/format-only" in out, out
    d = _host(repo, "DivergentTwin", body_tweak=True)
    code, out = run("extract_method.py", "check", "aggregateGuardResults", str(a), str(d), cwd=repo)
    assert code == 3, out
    assert "DIVERGENT" in out and "two BEHAVIORS" in out, out


def test_extract_scaffolds_trait_then_remove_then_wire_round_trip(repo):
    a = _host(repo, "RiskGuardService")
    b = _host(repo, "BacktestRiskGuardEvaluator")
    (repo / "Concerns").mkdir()
    dest = repo / "Concerns" / "AggregatesGuardResults.php"
    code, out = run("extract_method.py", "extract", str(a), "aggregateGuardResults",
                    "--to", str(dest), "--namespace",
                    "App\\Domain\\Trading\\Services\\Concerns", cwd=repo)
    assert code == 0, out
    t = dest.read_text()
    assert "trait AggregatesGuardResults" in t and "private function aggregateGuardResults" in t
    assert _balanced(t), "scaffold must be balanced (tokenized)"

    for host in (a, b):
        code, out = run("extract_method.py", "remove", str(host), "aggregateGuardResults", cwd=repo)
        assert code == 0, out
        code, out = run("extract_method.py", "wire", str(host), "--use",
                        "App\\Domain\\Trading\\Services\\Concerns\\AggregatesGuardResults", cwd=repo)
        assert code == 0, out
        text = host.read_text()
        assert "function aggregateGuardResults" not in text
        assert "use \\App\\Domain\\Trading\\Services\\Concerns\\AggregatesGuardResults;" in text
        assert _balanced(text), "host must stay balanced after remove+wire"
    # wire is idempotent
    code, out = run("extract_method.py", "wire", str(a), "--use",
                    "App\\Domain\\Trading\\Services\\Concerns\\AggregatesGuardResults", cwd=repo)
    assert code == 0 and "already wired" in out, out


def test_extract_into_existing_home_appends_before_closing_brace(repo):
    a = _host(repo, "RiskGuardService")
    dest = repo / "Existing.php"
    dest.write_text("<?php\n\nnamespace App\\Support;\n\ntrait Existing\n{\n"
                    "    private function money(float $v): string\n    {\n"
                    "        return (string) $v;\n    }\n}\n")
    code, out = run("extract_method.py", "extract", str(a), "aggregateGuardResults",
                    "--to", str(dest), cwd=repo)
    assert code == 0, out
    t = dest.read_text()
    assert t.index("money") < t.index("aggregateGuardResults"), "appended after existing members"
    assert t.rstrip().endswith("}"), t
    assert _balanced(t), "existing home must stay balanced after insert"


def test_refusals_leave_files_untouched(repo):
    a = _host(repo, "RiskGuardService")
    before = a.read_text()
    code, out = run("extract_method.py", "remove", str(a), "noSuchMethod", cwd=repo)
    assert code == 2 and "not found" in out, out
    assert a.read_text() == before
    # heredoc in range → refuse, no write
    h = repo / "Heredoc.php"
    h.write_text("<?php\nclass H\n{\n    private function tricky(): string\n    {\n"
                 "        return <<<EOT\nbody {ok}\nEOT;\n    }\n}\n")
    code, out = run("extract_method.py", "remove", str(h), "tricky", cwd=repo)
    assert code == 2 and "heredoc" in out.lower(), out
    # duplicate definition → refuse with both lines
    dup = repo / "Dup.php"
    dup.write_text("<?php\nclass A\n{\n    private function x(): int { return 1; }\n}\n"
                   "class B\n{\n    private function x(): int { return 2; }\n}\n")
    code, out = run("extract_method.py", "remove", str(dup), "x", cwd=repo)
    assert code == 2 and "more than once" in out, out


def test_boundaries_refuse_loudly(repo):
    # JS without tree-sitter (conftest forces SHRINKAGE_NO_TREESITTER=1 in run())
    # → install hint, never a guess; templates → partial-extraction guidance;
    # unknown languages → manual-loop guidance; cross-language extract → refuse.
    js = repo / "utils.js"
    js.write_text("function helper(a) {\n  return `x ${a} y`;\n}\n")
    before = js.read_text()
    code, out = run("extract_method.py", "remove", str(js), "helper", cwd=repo)
    assert code == 2 and "tree-sitter" in out, out
    assert js.read_text() == before
    twig = repo / "card.twig"
    twig.write_text("{% block card %}x{% endblock %}\n")
    code, out = run("extract_method.py", "find", str(twig), "card", cwd=repo)
    assert code == 2 and "partial/component" in out, out
    rb = repo / "thing.rb"
    rb.write_text("def helper\nend\n")
    code, out = run("extract_method.py", "find", str(rb), "helper", cwd=repo)
    assert code == 2 and "manually" in out, out
    php = _host(repo, "GuardHost")
    code, out = run("extract_method.py", "extract", str(php), "aggregateGuardResults",
                    "--to", str(repo / "home.go"), cwd=repo)
    assert code == 2 and "different language" in out, out


JAVA = """package com.acme;

public class {CLS} {{
    /**
     * Format money — a }} in the doc.
     */
    @Deprecated
    private static String money(double v) {{
        String brace = "}}";           // a }} in a comment
        char c = '{{';
        return "$" + v + brace + c;
    }}

    public String total(double v) {{ return money(v); }}
}}
"""


def test_java_round_trip(repo):
    a = repo / "A.java"
    b = repo / "B.java"
    for p, cls in ((a, "A"), (b, "B")):
        p.write_text(JAVA.replace("{CLS}", cls).replace("{{", "{").replace("}}", "}"))
    code, out = run("extract_method.py", "find", str(a), "money", cwd=repo)
    assert code == 0 and "@Deprecated" in out and "money" in out, out
    code, out = run("extract_method.py", "check", "money", str(a), str(b), cwd=repo)
    assert code == 0 and "identical" in out, out
    code, out = run("extract_method.py", "remove", str(a), "money", cwd=repo)
    assert code == 0, out
    t = a.read_text()
    assert "money(double" not in t and "total" in t, t
    code, out = run("extract_method.py", "wire", str(a), "--import",
                    "import com.acme.util.Money;", cwd=repo)
    assert code == 0, out
    lines = a.read_text().splitlines()
    assert "import com.acme.util.Money;" in [l.strip() for l in lines[:4]], lines[:4]
    assert lines.index("import com.acme.util.Money;") < \
        next(i for i, l in enumerate(lines) if "class A" in l), "import before the class"


def test_csharp_refuses_interpolated_strings_but_handles_plain(repo):
    bad = repo / "Bad.cs"
    bad.write_text('public class Bad {\n    private string M(int v) {\n'
                   '        return $"x {v}";\n    }\n}\n')
    code, out = run("extract_method.py", "find", str(bad), "M", cwd=repo)
    assert code == 2 and "interpolated" in out, out
    ok = repo / "Ok.cs"
    ok.write_text('public class Ok {\n    /// <summary>doc</summary>\n'
                  '    private string Money(double v) {\n'
                  '        string b = "}";  // }\n        return "$" + v + b;\n    }\n}\n')
    code, out = run("extract_method.py", "remove", str(ok), "Money", cwd=repo)
    assert code == 0, out
    assert "Money" not in ok.read_text()


def test_kotlin_interpolation_and_go_raw_strings_and_rust_lifetimes(repo):
    kt = repo / "Fmt.kt"
    kt.write_text('class Fmt {\n    // helper\n'
                  '    private fun money(v: Double): String {\n'
                  '        val s = "got ${v.toString()} }"\n        return s\n    }\n}\n')
    code, out = run("extract_method.py", "find", str(kt), "money", cwd=repo)
    assert code == 0 and "spans lines 2–6" in out, out

    go = repo / "fmt.go"
    go.write_text('package fmtx\n\n// money renders a value.\n'
                  'func (s *Svc) money(v float64) string {\n'
                  '\traw := `brace } here`\n\treturn raw\n}\n\n'
                  'func Total(v float64) string { return "" }\n')
    code, out = run("extract_method.py", "remove", str(go), "money", cwd=repo)
    assert code == 0, out
    assert "money" not in go.read_text() and "Total" in go.read_text()

    rs = repo / "fmt.rs"
    rs.write_text("/// doc line\npub fn area<'a>(s: &'a str) -> usize {\n"
                  "    let c = '}';\n    // }\n    s.len()\n}\n\n"
                  "pub fn keep() {}\n")
    code, out = run("extract_method.py", "remove", str(rs), "area", cwd=repo)
    assert code == 0, out
    assert "area" not in rs.read_text() and "keep" in rs.read_text()


PY = '''"""Module doc."""
import os


class {CLS}:
    # leading comment on the helper
    @staticmethod
    def money(v):
        """Render money."""
        # inline note
        return "$" + str(v)

    def total(self, v):
        return self.money(v)
'''


def test_python_find_check_extract_wire(repo):
    a = repo / "a_svc.py"
    b = repo / "b_svc.py"
    a.write_text(PY.replace("{CLS}", "ASvc"))
    b.write_text(PY.replace("{CLS}", "BSvc").replace("# inline note", "# other note")
                 .replace('"""Render money."""', '"""Render money (docstring differs)."""'))
    code, out = run("extract_method.py", "find", str(a), "money", cwd=repo)
    assert code == 0 and "leading comment" in out and "@staticmethod" in out, out
    # comments + docstring differ, AST identical → comment/format-only
    code, out = run("extract_method.py", "check", "money", str(a), str(b), cwd=repo)
    assert code == 0 and "comment/format-only" in out, out
    c = repo / "c_svc.py"
    c.write_text(PY.replace("{CLS}", "CSvc").replace('return "$" + str(v)',
                                                     'return "$" + repr(v)'))
    code, out = run("extract_method.py", "check", "money", str(a), str(c), cwd=repo)
    assert code == 3 and "DIVERGENT" in out, out
    # extract → new mixin scaffold; remove; wire import + mixin
    dest = repo / "money_mixin.py"
    code, out = run("extract_method.py", "extract", str(a), "money",
                    "--to", str(dest), "--trait", "MoneyMixin", cwd=repo)
    assert code == 0, out
    t = dest.read_text()
    assert "class MoneyMixin:" in t and "def money" in t, t
    code, out = run("extract_method.py", "remove", str(a), "money", cwd=repo)
    assert code == 0, out
    code, out = run("extract_method.py", "wire", str(a), "--mixin",
                    "money_mixin.MoneyMixin", cwd=repo)
    assert code == 0, out
    text = a.read_text()
    assert "from money_mixin import MoneyMixin" in text, text
    assert "class ASvc(MoneyMixin):" in text, text
    code, out = run("extract_method.py", "wire", str(a), "--import",
                    "from money_mixin import MoneyMixin", cwd=repo)
    assert code == 0 and "already present" in out, out


def test_js_with_treesitter_when_available(repo):
    import importlib.util
    import os
    import subprocess
    import sys as _sys
    if importlib.util.find_spec("tree_sitter") is None \
            or importlib.util.find_spec("tree_sitter_javascript") is None:
        import pytest
        pytest.skip("tree-sitter not installed")
    from conftest import SCRIPTS

    def run_ts(*args):
        env = {k: v for k, v in os.environ.items() if k != "SHRINKAGE_NO_TREESITTER"}
        r = subprocess.run([_sys.executable, str(SCRIPTS / "extract_method.py"), *args],
                           capture_output=True, text=True, cwd=repo, env=env)
        return r.returncode, r.stdout + r.stderr

    a = repo / "chart.js"
    a.write_text("import { base } from './base.js';\n\n"
                 "/** build the series */\n"
                 "function generateChartData(rows) {\n"
                 "  const t = `sum ${rows.length} }`;   // template + }\n"
                 "  const re = /}/;\n  return [t, re];\n}\n\n"
                 "export function draw(rows) { return generateChartData(rows); }\n")
    code, out = run_ts("find", str(a), "generateChartData")
    assert code == 0 and "build the series" in out, out
    dest = repo / "chartData.js"
    code, out = run_ts("extract", str(a), "generateChartData", "--to", str(dest))
    assert code == 0, out
    t = dest.read_text()
    assert "function generateChartData" in t and "export { generateChartData };" in t, t
    code, out = run_ts("remove", str(a), "generateChartData")
    assert code == 0, out
    code, out = run_ts("wire", str(a), "--import",
                       "import { generateChartData } from './chartData.js';")
    assert code == 0, out
    text = a.read_text()
    assert "generateChartData } from './chartData.js'" in text, text
    assert "function generateChartData(rows)" not in text
    # class methods refuse extract: this-binding is behavior
    m = repo / "widget.js"
    m.write_text("class W {\n  money(v) {\n    return `$${v}`;\n  }\n}\n")
    code, out = run_ts("extract", str(m), "money", "--to", str(repo / "m.js"))
    assert code == 2 and "this" in out, out


def test_new_home_in_other_dir_requires_namespace(repo):
    a = _host(repo, "RiskGuardService")
    (repo / "Support").mkdir()
    code, out = run("extract_method.py", "extract", str(a), "aggregateGuardResults",
                    "--to", str(repo / "Support" / "NewHome.php"), cwd=repo)
    assert code == 2 and "--namespace" in out, out
    assert not (repo / "Support" / "NewHome.php").exists()
