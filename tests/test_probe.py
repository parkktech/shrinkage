"""probe — runtime deprecation telemetry: exact insertion, honest status
classification (ALIVE / window open / BLIND / CLOSED-ZERO), clean removal."""
import json
import re

from conftest import run

PHP = """<?php

class Svc
{
    /**
     * Old path.
     */
    public function oldMethod(int $x): int
    {
        $y = $x + 1;
        return $y;
    }

    public function keeper(): string
    {
        return "ok { not a real brace }";
    }
}
"""

PY = '''def old_fn(a):
    """Docstring stays first."""
    b = a * 2
    return b
'''


def _probe_id(repo):
    reg = json.loads((repo / ".shrinkage/probes.json").read_text())
    assert len(reg["probes"]) == 1
    return reg["probes"][0]


def test_php_add_inserts_at_body_entry_balanced(repo):
    (repo / "Svc.php").write_text(PHP)
    code, out = run("probe.py", "add", "Svc.php", "oldMethod",
                    "--logs", "logs/*.log", cwd=repo)
    assert code == 0 and "armed probe" in out and "DEPLOY" in out
    lines = (repo / "Svc.php").read_text().splitlines()
    # marker is the first body line: directly after the opening brace
    assert lines[8].strip() == "{"
    assert lines[9].lstrip().startswith("error_log('srk-probe:")
    assert lines[9].startswith(" " * 8)          # sig indent + 4
    import extract_method as em
    assert em._balance((repo / "Svc.php").read_text(),
                       em.BRACE_CFGS["php"]) == 0
    pr = _probe_id(repo)
    assert pr["symbol"] == "oldMethod" and pr["lang"] == "php"
    dep = (repo / "DEPRECATIONS.md").read_text()
    assert f"- [ ] probe {pr['id']}: oldMethod (Svc.php)" in dep


def test_py_add_lands_after_docstring_and_parses(repo):
    import ast
    (repo / "util.py").write_text(PY)
    code, out = run("probe.py", "add", "util.py", "old_fn", cwd=repo)
    assert code == 0
    lines = (repo / "util.py").read_text().splitlines()
    assert lines[1].lstrip().startswith('"""')   # docstring still first
    assert "srk-probe:" in lines[2]              # probe right after it
    ast.parse((repo / "util.py").read_text())


def test_status_alive_vs_closed_zero_vs_blind(repo):
    (repo / "util.py").write_text(PY)
    (repo / "logs").mkdir()
    code, _ = run("probe.py", "add", "util.py", "old_fn",
                  "--window", "0", "--logs", "logs/*.log", cwd=repo)
    assert code == 0
    pr = _probe_id(repo)

    # BLIND: the glob matches nothing -> telemetry is off, say so
    code, out = run("probe.py", "status", cwd=repo)
    assert code == 0 and "BLIND" in out and "telemetry is off" in out

    # CLOSED-ZERO: a real log with zero hits, window already elapsed (0d)
    (repo / "logs/app.log").write_text("boot ok\n")
    code, out = run("probe.py", "status", cwd=repo)
    assert "CLOSED-ZERO" in out
    assert "Empirical chain closed" in out and f"probe {pr['id']}" in out

    # ALIVE: the marker shows up in the log -> keep the symbol
    (repo / "logs/app.log").write_text(f"warn {pr['marker']} fired\n")
    code, out = run("probe.py", "status", cwd=repo)
    assert "ALIVE" in out and "KEEP old_fn" in out


def test_status_window_open_counts_down(repo):
    (repo / "util.py").write_text(PY)
    (repo / "logs").mkdir()
    (repo / "logs/app.log").write_text("boot ok\n")
    run("probe.py", "add", "util.py", "old_fn",
        "--window", "30", "--logs", "logs/*.log", cwd=repo)
    code, out = run("probe.py", "status", cwd=repo)
    assert code == 0
    assert re.search(r"window open — 0d elapsed, 30d remaining", out)


def test_remove_restores_file_byte_exact(repo):
    (repo / "util.py").write_text(PY)
    run("probe.py", "add", "util.py", "old_fn", cwd=repo)
    pr = _probe_id(repo)
    code, out = run("probe.py", "remove", pr["id"], cwd=repo)
    assert code == 0 and "removed" in out
    assert (repo / "util.py").read_text() == PY   # byte-exact restore
    reg = json.loads((repo / ".shrinkage/probes.json").read_text())
    assert reg["probes"] == []
    dep = (repo / "DEPRECATIONS.md").read_text()
    assert f"- [x] probe {pr['id']}:" in dep and "probe removed" in dep


def test_refusals_are_loud_and_write_nothing(repo):
    (repo / "Edge.php").write_text(
        "<?php\nabstract class Edge\n{\n"
        "    abstract public function ghost(): void;\n\n"
        "    public function oneline(): int { return 1; }\n"
        "    public function kr(): int { $x = 1;\n        return $x;\n    }\n}\n")
    before = (repo / "Edge.php").read_text()
    for sym, why in [("ghost", "no body"), ("oneline", "single-line"),
                     ("kr", "code on the brace line")]:
        code, out = run("probe.py", "add", "Edge.php", sym, cwd=repo)
        assert code == 2 and why in out
    assert (repo / "Edge.php").read_text() == before
    assert not (repo / ".shrinkage/probes.json").exists()

    (repo / "one.py").write_text("def one(z): return z + 1\n")
    code, out = run("probe.py", "add", "one.py", "one", cwd=repo)
    assert code == 2 and "one-liner" in out

    (repo / "main.go").write_text("package main\nfunc main() {}\n")
    code, out = run("probe.py", "add", "main.go", "main", cwd=repo)
    assert code == 2 and "lsp_refs.py check" in out   # points at the oracle


def test_double_add_refuses(repo):
    (repo / "util.py").write_text(PY)
    assert run("probe.py", "add", "util.py", "old_fn", cwd=repo)[0] == 0
    code, out = run("probe.py", "add", "util.py", "old_fn", cwd=repo)
    assert code == 2 and "already armed" in out
