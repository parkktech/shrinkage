"""ledger.py + its enforcement in codemap (exclude) and safe_commit (frozen)."""
from conftest import commit, run


def test_ledger_matches_globs_and_dirs():
    import ledger
    assert ledger.matches("junkdir/a.py", ["junkdir/"])
    assert ledger.matches("src/LAB/Seal.php", ["src/LAB/**"])
    assert ledger.matches("gen.php", ["gen.php"])
    assert not ledger.matches("src/App.php", ["src/LAB/**"])
    assert not ledger.matches("keep.py", ["junkdir/"])


def test_codemap_excludes_ledger_globs(repo):
    (repo / "keep.py").write_text("def kept():\n    return 1\n")
    (repo / "junkdir").mkdir()
    (repo / "junkdir" / "phantom.py").write_text("def phantom():\n    return 2\n")
    (repo / ".shrinkage").mkdir()
    (repo / ".shrinkage" / "ledger.md").write_text("## excluded\n- junkdir/\n")
    code, out = run("codemap.py", "build", cwd=repo)
    assert code == 0, out
    text = (repo / ".claude" / "codemap.txt").read_text()
    assert "kept" in text, text
    assert "phantom" not in text, "ledger `## excluded` globs must never enter the map"


def test_safe_commit_refuses_frozen(repo):
    (repo / "sealed.py").write_text("x = 1\n")
    commit(repo)
    (repo / ".shrinkage").mkdir()
    (repo / ".shrinkage" / "ledger.md").write_text("## frozen\nsealed.py  sealed subsystem\n")
    (repo / "sealed.py").write_text("x = 2\n")
    code, out = run("safe_commit.py", "-m", "shrink: edit sealed", "--", "sealed.py", cwd=repo)
    assert code == 2 and "FROZEN" in out.upper(), out
