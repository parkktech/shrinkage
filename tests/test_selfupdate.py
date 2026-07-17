"""selfupdate.py — version detection + cache clear."""
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "shrinkage" / "scripts"


def run_home(home, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / "selfupdate.py"), *args],
                       capture_output=True, text=True,
                       env={**os.environ, "HOME": str(home), "CLAUDE_CONFIG_DIR": ""})
    return r.stdout + r.stderr


def test_detects_installed_version_and_cache(tmp_path):
    vd = tmp_path / ".claude/plugins/cache/parkktech/srk/0.14.0/.claude-plugin"
    vd.mkdir(parents=True)
    (vd / "plugin.json").write_text('{"version":"0.14.0"}')
    out = run_home(tmp_path)
    assert "installed: 0.14.0" in out and "cache:" in out


def test_clear_removes_cache_and_prints_steps(tmp_path):
    (tmp_path / ".claude/plugins/cache/parkktech/srk/0.14.0").mkdir(parents=True)
    out = run_home(tmp_path, "--clear")
    assert "cleared cache" in out and "/plugin install shrinkage@parkktech" in out
    assert not (tmp_path / ".claude/plugins/cache/parkktech").exists()


def test_no_cache_is_graceful(tmp_path):
    out = run_home(tmp_path)
    assert "none found" in out or "cache: none" in out
