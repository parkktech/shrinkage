"""coverage_check.py bootstrap — detect the repo's coverage command (#10)."""
from conftest import run

import coverage_check


def test_detects_pest_with_clover(repo):
    (repo / "vendor" / "bin").mkdir(parents=True)
    (repo / "vendor" / "bin" / "pest").write_text("#!/bin/sh\n")
    cmd, artifact, note = coverage_check.detect_bootstrap(repo)
    assert cmd == "vendor/bin/pest --coverage-clover clover.xml"
    assert artifact == "clover.xml"


def test_detects_pytest_and_vitest(repo, tmp_path):
    (repo / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    cmd, artifact, _ = coverage_check.detect_bootstrap(repo)
    assert "pytest --cov --cov-report=xml" in cmd and artifact == "coverage.xml"
    js = tmp_path / "jsrepo"
    js.mkdir()
    (js / "package.json").write_text('{"devDependencies": {"vitest": "^1"}}')
    cmd, artifact, _ = coverage_check.detect_bootstrap(js)
    assert cmd.startswith("npx vitest run --coverage")


def test_bootstrap_command_is_dry_by_default(repo):
    (repo / "pyproject.toml").write_text("x = 1\n")
    code, out = run("coverage_check.py", "bootstrap", cwd=repo)
    assert code == 0, out
    assert "pytest --cov" in out and "Dry by default" in out, out
    assert "suite-gated to coverage-aware" in out, out
