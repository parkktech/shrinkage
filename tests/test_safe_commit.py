"""safe_commit.py (path-limited commits) + guard_staging.py (broad-staging hook)."""
import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import commit, run

HOOKS = Path(__file__).resolve().parent.parent / "hooks"


def run_hook(payload, cwd, extra_env=None):
    r = subprocess.run([sys.executable, str(HOOKS / "guard_staging.py")],
                       input=json.dumps(payload), capture_output=True, text=True,
                       cwd=cwd, env={**os.environ, **(extra_env or {})})
    return r.returncode, r.stdout + r.stderr


def _names_in_head(repo):
    out = subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
                         cwd=repo, capture_output=True, text=True).stdout
    return sorted(l for l in out.split() if l)


# --- safe_commit.py -----------------------------------------------------------

def test_safe_commit_commits_only_declared(repo):
    (repo / "a.py").write_text("x = 1\n")
    commit(repo)
    (repo / "a.py").write_text("x = 2\n")          # the transform
    (repo / "wip.py").write_text("junk = 1\n")     # user's unrelated in-flight file
    code, out = run("safe_commit.py", "-m", "shrink: edit a", "--", "a.py", cwd=repo)
    assert code == 0, out
    assert _names_in_head(repo) == ["a.py"], out                 # only a.py landed
    st = subprocess.run(["git", "status", "--porcelain", "wip.py"],
                        cwd=repo, capture_output=True, text=True).stdout
    assert "wip.py" in st, "the unrelated file must stay uncommitted"


def test_safe_commit_refuses_prestaged_extra(repo):
    (repo / "a.py").write_text("x = 1\n")
    (repo / "b.py").write_text("y = 1\n")
    commit(repo)
    (repo / "a.py").write_text("x = 2\n")
    (repo / "b.py").write_text("y = 2\n")
    subprocess.run(["git", "add", "b.py"], cwd=repo, check=True)  # b pre-staged, not declared
    code, out = run("safe_commit.py", "-m", "shrink: a", "--", "a.py", cwd=repo)
    assert code == 2 and "b.py" in out, out


def test_safe_commit_handles_deletion(repo):
    (repo / "dead.py").write_text("def gone():\n    return 1\n")
    commit(repo)
    (repo / "dead.py").unlink()                    # the transform deletes the file
    code, out = run("safe_commit.py", "-m", "shrink: drop dead.py", "--", "dead.py", cwd=repo)
    assert code == 0, out
    assert _names_in_head(repo) == ["dead.py"], out


# --- guard_staging.py (PreToolUse hook) --------------------------------------

def _shave_marker(repo):
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / ".claude" / "srk-shave-active").write_text("")


def test_hook_blocks_add_all_during_shave(repo):
    _shave_marker(repo)
    code, out = run_hook({"tool_name": "Bash", "tool_input": {"command": "git add -A"}},
                         cwd=repo, extra_env={"CLAUDE_PROJECT_DIR": str(repo)})
    assert code == 2 and "safe_commit" in out, out


def test_hook_blocks_commit_a_during_shave(repo):
    _shave_marker(repo)
    code, out = run_hook({"tool_name": "Bash", "tool_input": {"command": 'git commit -am "x"'}},
                         cwd=repo, extra_env={"CLAUDE_PROJECT_DIR": str(repo)})
    assert code == 2, out


def test_hook_allows_without_marker(repo):
    code, out = run_hook({"tool_name": "Bash", "tool_input": {"command": "git add -A"}},
                         cwd=repo, extra_env={"CLAUDE_PROJECT_DIR": str(repo)})
    assert code == 0, out


def test_hook_allows_explicit_path_during_shave(repo):
    _shave_marker(repo)
    for cmd in ("git add -- a.py", 'git commit -- a.py -m "shrink"', "ls -la"):
        code, out = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}},
                             cwd=repo, extra_env={"CLAUDE_PROJECT_DIR": str(repo)})
        assert code == 0, f"{cmd!r} -> {out}"


def test_hook_ignores_non_bash(repo):
    _shave_marker(repo)
    code, out = run_hook({"tool_name": "Edit", "tool_input": {"command": "git add -A"}},
                         cwd=repo, extra_env={"CLAUDE_PROJECT_DIR": str(repo)})
    assert code == 0, out


def test_refuses_typechange_symlink_to_regular_file(repo):
    # The CLAUDE.md → AGENTS.md incident: editing through a symlink converts the
    # link into a regular file; safe_commit must refuse the type change.
    (repo / "AGENTS.md").write_text("# agents\n")
    os.symlink("AGENTS.md", repo / "CLAUDE.md")
    commit(repo)
    (repo / "CLAUDE.md").unlink()
    (repo / "CLAUDE.md").write_text("# now a regular file, decoupled\n")
    code, out = run("safe_commit.py", "-m", "shrink: docs", "--", "CLAUDE.md", cwd=repo)
    assert code == 2 and "CHANGED TYPE" in out and "symlink" in out, out
    staged = subprocess.run(["git", "diff", "--cached", "--name-only"],
                            cwd=repo, capture_output=True, text=True).stdout
    assert "CLAUDE.md" not in staged, "refusal must unstage the typechange"
    # the intended-restore path stays available, explicitly
    code, out = run("safe_commit.py", "--allow-typechange", "-m",
                    "fix: restore symlink arrangement", "--", "CLAUDE.md", cwd=repo)
    assert code == 0, out
