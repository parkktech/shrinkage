"""organize.py: area-first placement and catch-all names on new files."""
import json
import subprocess
import sys

from conftest import SCRIPTS


def hook(repo, rel, content="<?php\n"):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    r = subprocess.run([sys.executable, str(SCRIPTS / "organize.py"), "hook"], cwd=repo,
                       input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(path)}}),
                       capture_output=True, text=True, env={"CLAUDE_PROJECT_DIR": str(repo), "PATH": "/usr/bin:/bin"})
    return r.returncode, r.stderr


def laravel(repo):
    (repo / "artisan").write_text("")
    (repo / "app" / "Domains").mkdir(parents=True)


def test_catch_all_names_are_flagged(repo):
    code, err = hook(repo, "src/EmailManager.py", "x = 1\n")
    assert code == 2 and "catch-all" in err
    assert hook(repo, "src/send_email.py", "x = 1\n")[0] == 0


def test_laravel_base_dirs_flagged_once_domains_exist(repo):
    (repo / "artisan").write_text("")
    assert hook(repo, "app/Models/Lead.php")[0] == 0, "no domain root yet: follow existing layout"
    laravel(repo)
    code, err = hook(repo, "app/Services/LeadScorer.php")
    assert code == 2 and "app/Domains/<Area>" in err
    assert hook(repo, "app/Domains/Scoring/Actions/ScoreLead.php")[0] == 0
    assert hook(repo, "app/Http/Controllers/Controller.php")[0] == 0


def test_required_header(repo):
    (repo / ".claude").mkdir()
    (repo / ".claude" / "shrinkage.json").write_text(json.dumps({"require_header": "@copyright 2026 Acme"}))
    code, err = hook(repo, "src/charge.py", "x = 1\n")
    assert code == 2 and "header" in err
    assert hook(repo, "src/refund.py", "# @copyright 2026 Acme\nx = 1\n")[0] == 0


def test_non_source_and_opt_out(repo):
    assert hook(repo, "docs/HelperNotes.md", "x\n")[0] == 0
    (repo / ".claude").mkdir()
    (repo / ".claude" / "shrinkage.json").write_text(json.dumps({"organize": False}))
    assert hook(repo, "src/DataUtil.py", "x = 1\n")[0] == 0
