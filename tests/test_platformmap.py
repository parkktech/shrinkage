"""platformmap: Composer classmap search, framework detection, --auto hook guard."""
import json
import subprocess

from conftest import run


def laravel_fixture(repo):
    (repo / "composer.json").write_text(json.dumps(
        {"require": {"php": "^8.2", "laravel/framework": "^11.0"}}))
    vc = repo / "vendor" / "composer"
    vc.mkdir(parents=True)
    sup = repo / "vendor" / "illuminate" / "support"
    sup.mkdir(parents=True)
    vc.joinpath("autoload_classmap.php").write_text(
        "<?php\n$vendorDir = dirname(__DIR__);\n$baseDir = dirname($vendorDir);\n"
        "return array(\n"
        "    'Illuminate\\\\Support\\\\Str' => $vendorDir . '/illuminate/support/Str.php',\n"
        "    'App\\\\Exporters\\\\CsvExporter' => $baseDir . '/app/CsvExporter.php',\n"
        ");\n")
    sup.joinpath("Str.php").write_text(
        "<?php\nnamespace Illuminate\\Support;\nclass Str\n{\n"
        "    public static function slug(string $t, string $s = '-'): string\n    {\n"
        "        return $t;\n    }\n}\n")


def test_vendor_search_and_deep(repo):
    laravel_fixture(repo)
    code, out = run("platformmap.py", "search", "str", "--deep", cwd=repo)
    assert "Illuminate\\Support\\Str" in out and "illuminate/support" in out
    assert "slug(string $t" in out, "--deep must list methods"


def test_framework_detection(repo):
    laravel_fixture(repo)
    code, out = run("platformmap.py", "frameworks", cwd=repo)
    assert "laravel" in out and "frameworks/laravel.md" in out


def test_vendor_no_classmap_message(repo):
    (repo / "composer.json").write_text("{}")
    code, out = run("platformmap.py", "search", "x", cwd=repo)
    assert "no Composer classmap" in out


def test_auto_hook_silent_outside_projects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no .git, no code
    code, out = run("codemap.py", "refresh", "--auto", cwd=tmp_path)
    assert code == 0 and out.strip() == ""
    assert not (tmp_path / ".claude").exists(), "--auto must not touch non-projects"


def test_auto_hook_builds_in_code_repo(repo):
    (repo / "a.py").write_text("def f():\n    return 1\n")
    code, out = run("codemap.py", "refresh", "--auto", "--quiet", cwd=repo)
    assert code == 0 and (repo / ".claude" / "codemap.txt").exists()


def test_startup_line_audit_lifecycle(repo):
    (repo / "m.py").write_text("def a():\n    return b()\n\ndef b():\n    return 1\n")
    # 1) no audit yet -> prompt to run it
    code, out = run("codemap.py", "refresh", "--auto", cwd=repo)
    assert "no audit yet" in out and "/srk:audit" in out
    # 2) fresh plan with matching fingerprint -> open item count
    fp = None
    import re as _re
    hdr = (repo / ".claude" / "codemap.txt").read_text().splitlines()[0]
    fp = _re.search(r"\| fp: (\w+)", hdr).group(1)
    (repo / "SHRINK-PLAN.md").write_text(
        f"<!-- map-fp: {fp} -->\n\n| # | candidate | file |\n|---|---|---|\n"
        "| 1 | dead | m.py |\n| 2 | dup | m.py |\n")
    code, out = run("codemap.py", "refresh", "--auto", cwd=repo)
    assert "2 open item" in out
    # 3) code moves on AND a real (task-time) refresh rebuilds the map -> the
    #    plan's stamped fp no longer matches the map fp -> stale. (The hook
    #    itself never rebuilds on a big repo; task-time refresh does.)
    (repo / "m.py").write_text((repo / "m.py").read_text() + "\ndef c():\n    return 2\n")
    run("codemap.py", "refresh", cwd=repo)  # task-time rebuild -> new map fp
    code, out = run("codemap.py", "refresh", "--auto", cwd=repo)
    assert "stale" in out and "/srk:audit" in out
    # 4) quiet_startup silences it
    (repo / ".claude" / "shrinkage.json").write_text('{"quiet_startup": true}')
    code, out = run("codemap.py", "refresh", "--auto", cwd=repo)
    assert out.strip() == ""
