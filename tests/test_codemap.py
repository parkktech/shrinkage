"""codemap CLI: build, refresh (incl. deletion-awareness), dupes, clones, budget."""
from conftest import commit, run


def seed(repo):
    (repo / "a.py").write_text("def alpha():\n    return beta()\n\ndef beta():\n    return 1\n")
    (repo / "b.js").write_text("export function beta() {\n  return 2;\n}\n")


def test_build_and_query(repo):
    seed(repo)
    code, out = run("codemap.py", "build", cwd=repo)
    assert code == 0 and "map written" in out
    map_text = (repo / ".claude" / "codemap.txt").read_text()
    assert "alpha" in map_text and "| fp: " in map_text
    code, out = run("codemap.py", "query", "beta", cwd=repo)
    assert "a.py" in out or "b.js" in out


def test_refresh_noop_then_detects_deletion(repo):
    seed(repo)
    run("codemap.py", "build", cwd=repo)
    code, out = run("codemap.py", "refresh", cwd=repo)
    assert "up to date" in out
    # THE regression: deleting a file must trigger a rebuild (mtime-only misses it)
    (repo / "b.js").unlink()
    code, out = run("codemap.py", "refresh", cwd=repo)
    assert "map written" in out, "deletion must invalidate the map"
    assert "b.js" not in (repo / ".claude" / "codemap.txt").read_text()


def test_refcounts_ignore_comments(repo):
    (repo / "a.py").write_text(
        "def used():\n    return 1\n\ndef ghost():\n    return 2\n\n"
        "x = used()\n# ghost ghost ghost mentioned only in comments\n")
    run("codemap.py", "build", cwd=repo)
    map_text = (repo / ".claude" / "codemap.txt").read_text()
    used_line = next(l for l in map_text.splitlines() if "used(" in l)
    ghost_line = next(l for l in map_text.splitlines() if "ghost(" in l)
    assert "x" in used_line.split("@")[1], "real call should count"
    assert "x" not in ghost_line.split("@")[1], "comment mentions must not count as refs"


def test_dupes_and_clones(repo):
    block = "\n".join(f"    if x == {i}:\n        y += {i}" for i in range(4))
    (repo / "one.py").write_text(f"def calc(x):\n    y = 0\n{block}\n    return y\n")
    (repo / "two.py").write_text(f"def calc(z):\n    y = 0\n{block}\n    return y\n")
    code, out = run("codemap.py", "dupes", cwd=repo)
    assert "calc" in out and "2 definitions" in out
    code, out = run("codemap.py", "clones", cwd=repo)
    assert "one.py" in out and "two.py" in out


def test_budget_collapse(repo):
    seed(repo)
    code, out = run("codemap.py", "build", "--budget", "10", "--out", str(repo / "m.txt"), cwd=repo)
    assert "collapsed" in (repo / "m.txt").read_text().splitlines()[0]


def test_scope_writes_to_intel_dir_not_the_scanned_tree(repo):
    # P2.9: the scope artifact must land in the main map's intel dir, never
    # inside the scanned subtree (where it pollutes the tree and gets left behind).
    sub = repo / "pkg"
    sub.mkdir()
    (sub / "mod.py").write_text("def alpha():\n    return 1\n")
    code, out = run("codemap.py", "scope", "pkg", cwd=repo)
    assert code == 0, out
    assert not (sub / ".codemap-scope.txt").exists(), "must not write into the scanned subtree"
    scope_map = repo / ".claude" / "codemap-scope-pkg.txt"
    assert scope_map.exists(), out
    assert "alpha" in scope_map.read_text()
    # and it's kept out of git so auditors never have to clean it up
    assert "codemap-scope-pkg.txt" in (repo / ".gitignore").read_text()
