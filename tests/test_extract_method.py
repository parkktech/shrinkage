"""extract_method.py — tokenizer-guided C1/C9 method surgery (find/check/extract/remove/wire)."""
from conftest import run

import extract_method


def _balanced(text):
    return extract_method._balance(text) == 0

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
    assert code == 0 and "comment-only" in out, out
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


def test_php_only_guard_refuses_other_languages(repo):
    # The tokenizer is PHP-exact; on JS it would be actively wrong (backtick
    # templates, regex literals, # private fields). Refuse loudly, write nothing.
    js = repo / "utils.js"
    js.write_text("function helper(a) {\n  return `x ${a} y`;\n}\n")
    before = js.read_text()
    for args in (["find", str(js), "helper"],
                 ["remove", str(js), "helper"],
                 ["wire", str(js), "--use", "X\\Y"]):
        code, out = run("extract_method.py", *args, cwd=repo)
        assert code == 2 and "PHP-only" in out, (args, out)
    assert js.read_text() == before
    # extract refuses a non-PHP DEST too
    php = _host(repo, "GuardHost")
    code, out = run("extract_method.py", "extract", str(php), "aggregateGuardResults",
                    "--to", str(repo / "home.ts"), cwd=repo)
    assert code == 2 and "PHP-only" in out, out


def test_new_home_in_other_dir_requires_namespace(repo):
    a = _host(repo, "RiskGuardService")
    (repo / "Support").mkdir()
    code, out = run("extract_method.py", "extract", str(a), "aggregateGuardResults",
                    "--to", str(repo / "Support" / "NewHome.php"), cwd=repo)
    assert code == 2 and "--namespace" in out, out
    assert not (repo / "Support" / "NewHome.php").exists()
