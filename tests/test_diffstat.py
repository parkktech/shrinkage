"""diffstat: LOC splits, non-code exclusion, renames, compat-watch, gate ledger."""
import json

from conftest import commit, run, stage


def base(repo):
    (repo / "app.py").write_text("def f(a):\n    return a\n")
    commit(repo)


def test_docs_and_config_excluded_from_loc(repo):
    base(repo)
    (repo / "app.py").write_text("def f(a):\n    return a\n\ndef g(b):\n    return b\n")
    (repo / "SPEC.md").write_text("# five\nlines\nof\ndoc\ntext\n")
    (repo / "config.json").write_text('{\n "a": 1,\n "b": 2\n}\n')
    stage(repo)
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    # +3 = the code change only (incl. its blank line); the 5 md + 4 json lines
    # must NOT appear in either bucket (they'd make it +12 / test +5).
    assert "app +3" in out and "test +0" in out, out


def test_test_paths_split(repo):
    base(repo)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_app.py").write_text("def test_f():\n    assert True\n")
    stage(repo)
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    assert "test +2" in out


def test_rename_does_not_crash(repo):
    base(repo)
    (repo / "app.py").rename(repo / "core.py")
    import subprocess
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    assert code == 0 and "files touched: 2" in out, out


def test_signature_change_compat_watch(repo):
    base(repo)
    (repo / "app.py").write_text("def f(a, b=1):\n    return a\n")
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    assert "compat-watch" in out and "f" in out, out
    assert "new symbols: 0" in out, "param add is a change, not a new symbol"


def test_gate_ledger_flags_unjustified(repo):
    base(repo)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "shrinkage-gates.jsonl").write_text(
        json.dumps({"symbols": ["g"], "rung": 5, "task": "t"}) + "\n")
    (repo / "app.py").write_text(
        "def f(a):\n    return a\n\ndef g(b):\n    return b\n\ndef h(c):\n    return c\n")
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    line = next(l for l in out.splitlines() if l.startswith("unjustified"))
    flagged = line.split(":")[1].split("—")[0]
    assert "h" in flagged and "g" not in flagged, line


def test_no_ledger_no_flag(repo):
    base(repo)
    (repo / "app.py").write_text("def f(a):\n    return a\n\ndef h(c):\n    return c\n")
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    assert "unjustified" not in out


def test_trend_reports_pending_deprecations(repo):
    base(repo)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "shrinkage-log.jsonl").write_text(
        json.dumps({"ts": "t", "ref": "HEAD", "net_app": -3, "net_test": 0,
                    "files": 1, "new": [], "removed": ["x"]}) + "\n")
    (repo / "DEPRECATIONS.md").write_text(
        "# Shims\n- [ ] old_name -> new_name (remove 2026-09)\n- [ ] legacy() (remove 2026-10)\n- [x] done()\n")
    code, out = run("diffstat.py", "--trend", cwd=repo)
    assert "pending removal: 2" in out, out
