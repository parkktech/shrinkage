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
