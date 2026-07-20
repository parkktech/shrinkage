"""selfupdate.py — version detection + the reliable (non-destructive) update path."""
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


def test_guides_uninstall_then_install_without_deleting_cache(tmp_path):
    # A stale install must be guided to uninstall -> install, and the cache must
    # be LEFT IN PLACE — deleting it while the plugin stays registered is what
    # causes 'already installed' + 'cache-miss'.
    vd = tmp_path / ".claude/plugins/cache/parkktech/srk/0.14.0/.claude-plugin"
    vd.mkdir(parents=True)
    (vd / "plugin.json").write_text('{"version":"0.14.0"}')
    out = run_home(tmp_path)
    assert "/plugin uninstall srk@parkktech" in out
    assert "/plugin install srk@parkktech" in out
    assert (tmp_path / ".claude/plugins/cache/parkktech").exists(), "must not delete the cache"


def test_no_cache_is_graceful(tmp_path):
    out = run_home(tmp_path)
    assert "none found" in out or "cache: none" in out
