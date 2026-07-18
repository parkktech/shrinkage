"""dirty_apply.py — park/unpark a user's disjoint in-flight hunk around a shave."""
from conftest import commit, run


def _lines(repo, name="a.py"):
    return (repo / name).read_text().splitlines()


def _write(repo, lines, name="a.py"):
    (repo / name).write_text("\n".join(lines) + "\n")


def test_disjoint_hunk_round_trips(repo):
    _write(repo, [f"L{i}" for i in range(1, 11)])
    commit(repo)
    ls = _lines(repo); ls[0] = "L1_USER_EDIT"          # user's in-flight hunk (top)
    _write(repo, ls)

    code, out = run("dirty_apply.py", "park", "a.py", cwd=repo)
    assert code == 0, out
    assert _lines(repo)[0] == "L1", "file must be reset to HEAD for a clean base"

    shaved = [l for l in _lines(repo) if l not in ("L8", "L9")]  # disjoint shave
    _write(repo, shaved)
    run("safe_commit.py", "-m", "shrink: drop L8/L9", "--", "a.py", cwd=repo)

    code, out = run("dirty_apply.py", "unpark", "a.py", cwd=repo)
    assert code == 0, out
    final = _lines(repo)
    assert final[0] == "L1_USER_EDIT", "user's hunk re-applied on top of the shave"
    assert "L8" not in final and "L9" not in final, "shave stays committed"


def test_disjoint_hunk_adjacent_to_shave_still_round_trips(repo):
    # The production case that plain `git apply` false-refused: the user's edited
    # line doesn't overlap the shave, but the shave deletes lines that fall inside
    # the hunk's few lines of diff CONTEXT. A 3-way merge must still re-apply it.
    _write(repo, [f"L{i}" for i in range(1, 21)])
    commit(repo)
    ls = _lines(repo); ls[1] = "L2_USER_EDIT"          # WIP on line 2 (context reaches L5)
    _write(repo, ls)
    code, out = run("dirty_apply.py", "park", "a.py", cwd=repo)
    assert code == 0, out

    removed = {f"L{i}" for i in range(4, 13)}           # shave deletes L4..L12 (into the context)
    _write(repo, [l for l in _lines(repo) if l not in removed])
    run("safe_commit.py", "-m", "shrink: drop L4-L12", "--", "a.py", cwd=repo)

    code, out = run("dirty_apply.py", "unpark", "a.py", cwd=repo)
    assert code == 0, out                               # 3-way applies it; plain apply refused
    final = _lines(repo)
    assert final[0] == "L1" and final[1] == "L2_USER_EDIT", final
    assert "L4" not in final and "L12" not in final, "shave stays committed"
    # WIP must be an UNSTAGED change, never quietly staged into the next commit
    import subprocess
    staged = subprocess.run(["git", "diff", "--cached", "--name-only"],
                            cwd=repo, capture_output=True, text=True).stdout
    assert "a.py" not in staged, "restored WIP must be unstaged"


def test_overlap_restores_backup_and_signals(repo):
    _write(repo, [f"L{i}" for i in range(1, 11)])
    commit(repo)
    ls = _lines(repo); ls[4] = "L5_USER_EDIT"          # user's hunk on line 5
    _write(repo, ls)

    code, out = run("dirty_apply.py", "park", "a.py", cwd=repo)
    assert code == 0, out

    shaved = [l for l in _lines(repo) if l != "L5"]     # shave touches the SAME line
    _write(repo, shaved)
    run("safe_commit.py", "-m", "shrink: drop L5", "--", "a.py", cwd=repo)

    code, out = run("dirty_apply.py", "unpark", "a.py", cwd=repo)
    assert code == 3, out                               # not disjoint
    assert "L5_USER_EDIT" in _lines(repo), "the exact pre-shave file is restored"
