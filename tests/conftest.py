import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "shrinkage" / "scripts"
sys.path.insert(0, str(SCRIPTS))

# Parser tests target the regex paths deterministically; the tree-sitter
# parity test opts back in explicitly.
os.environ.setdefault("SHRINKAGE_NO_TREESITTER", "1")


def run(script, *args, cwd=None):
    """Run a shrinkage script as a subprocess; returns (exit_code, output)."""
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                       capture_output=True, text=True, cwd=cwd,
                       env={**os.environ, "SHRINKAGE_NO_TREESITTER": "1"})
    return r.returncode, r.stdout + r.stderr


@pytest.fixture
def repo(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.co"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def commit(repo, msg="c"):
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", msg], cwd=repo, check=True)


def stage(repo):
    """git add -A — new files must be staged to appear in `git diff HEAD`."""
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
