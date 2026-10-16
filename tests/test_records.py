"""records.py: change-record gate, commit hook, ledger verify/protected, keeps integration."""
import json
import subprocess
import sys

from conftest import SCRIPTS, commit, run

import ledger
import records


def hook(repo, command):
    r = subprocess.run([sys.executable, str(SCRIPTS / "records.py"), "hook"], cwd=repo,
                       input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
                       capture_output=True, text=True, env={"CLAUDE_PROJECT_DIR": str(repo), "PATH": "/usr/bin:/bin"})
    return r.returncode, r.stderr


def setup_records(repo):
    run("records.py", "init", cwd=repo)
    (repo / "app.py").write_text("def a():\n    return 1\n")
    commit(repo, "init")


def test_no_records_files_means_no_gate(repo):
    (repo / "app.py").write_text("x = 1\n")
    code, _ = hook(repo, "git add app.py && git commit -m 'Add app'")
    assert code == 0, "repos without a ledger or changelog are never blocked"


def test_code_commit_without_records_is_blocked_then_allowed(repo):
    setup_records(repo)
    (repo / "app.py").write_text("def a():\n    return 2\n")
    code, err = hook(repo, "git add app.py && git commit -m 'Change a'")
    assert code == 2 and "CHANGELOG.md" in err and "FEATURE-LEDGER" in err
    code, _ = hook(repo, "git add app.py && git commit -m 'Refactor a\n\n[ledger: none]\n[changelog: none]'")
    assert code == 0
    code, _ = hook(repo, "git add app.py CHANGELOG.md docs/FEATURE-LEDGER.md && git commit -m 'Change a'")
    assert code == 0


def test_fix_needs_regression_row_even_with_ledger_none(repo):
    setup_records(repo)
    (repo / "app.py").write_text("def a():\n    return 3\n")
    code, err = hook(repo, "git add app.py && git commit -m \"$(cat <<'EOF'\nFix a returning wrong value\n\n[ledger: none]\n[changelog: none]\nEOF\n)\"")
    assert code == 2 and "regression row" in err


def test_docs_and_tests_only_commits_pass(repo):
    setup_records(repo)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_a.py").write_text("def test_a():\n    pass\n")
    (repo / "README.md").write_text("hi\n")
    code, _ = hook(repo, "git add tests README.md && git commit -m 'Add test'")
    assert code == 0


def test_opt_out(repo):
    setup_records(repo)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "shrinkage.json").write_text(json.dumps({"change_records": False}))
    (repo / "app.py").write_text("def a():\n    return 4\n")
    assert hook(repo, "git commit -am 'Change'")[0] == 0


def test_verify_protected_and_keeps(repo):
    run("records.py", "init", cwd=repo)
    (repo / "src").mkdir()
    (repo / "src" / "billing.py").write_text("def charge():\n    pass\n")
    led = repo / "docs" / "FEATURE-LEDGER.md"
    led.write_text(led.read_text().replace(
        "|---|---|---|---|---|---|\n",
        "|---|---|---|---|---|---|\n| F-BIL-01 | Charge cards | Live | `src/billing.py` | `tests/test_billing.py` | — |\n"
        "| F-BIL-02 | Refunds | Planned | `src/refund.py` | — | — |\n", 1))
    code, out = run("records.py", "verify", cwd=repo)
    assert code == 1 and "tests/test_billing.py" in out and "refund" not in out
    code, out = run("records.py", "protected", "src", cwd=repo)
    assert "F-BIL-01" in out
    assert "src/billing.py" in ledger.keeps(repo)
    assert records.protected(repo, ["src/billing.py"])[0][0] == "F-BIL-01"


def test_init_never_overwrites(repo):
    (repo / "CHANGELOG.md").write_text("mine\n")
    run("records.py", "init", cwd=repo)
    assert (repo / "CHANGELOG.md").read_text() == "mine\n"
    assert (repo / "docs" / "FEATURE-LEDGER.md").exists()
