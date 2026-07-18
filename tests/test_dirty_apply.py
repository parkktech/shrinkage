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
