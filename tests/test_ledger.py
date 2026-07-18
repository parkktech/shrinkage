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


def test_ledger_reads_non_utf8_without_crashing(repo):
    # Regression: a ledger hand-saved as cp1252/latin-1 (byte 0x97 = em-dash there)
    # must parse leniently, not raise UnicodeDecodeError. The first token per row is
    # still recovered; the bad byte lands harmlessly in the human reason.
    import ledger
    (repo / ".shrinkage").mkdir()
    (repo / ".shrinkage" / "ledger.md").write_bytes(
        b"## excluded\nedge-trades/  stale clone \x97 369 phantoms\n"
        b"## frozen\nsrc/LAB/**  sealed \x97 hash-seal\n")
    assert ledger.excluded(repo) == ["edge-trades/"]
    assert ledger.frozen(repo) == ["src/LAB/**"]


def test_codemap_survives_non_utf8_ledger(repo):
    # The real crash path: `codemap.py build` calls ledger.excluded(); a non-UTF-8
    # ledger used to take the whole map down. It must build clean and still exclude.
    (repo / "keep.py").write_text("def kept():\n    return 1\n")
    (repo / "junkdir").mkdir()
    (repo / "junkdir" / "phantom.py").write_text("def phantom():\n    return 2\n")
    (repo / ".shrinkage").mkdir()
    (repo / ".shrinkage" / "ledger.md").write_bytes(
        b"## excluded\n- junkdir/  stale clone \x97 phantom files\n")
    code, out = run("codemap.py", "build", cwd=repo)
    assert code == 0, out
    text = (repo / ".claude" / "codemap.txt").read_text()
    assert "kept" in text and "phantom" not in text, out


def test_safe_commit_refuses_frozen(repo):
    (repo / "sealed.py").write_text("x = 1\n")
    commit(repo)
    (repo / ".shrinkage").mkdir()
    (repo / ".shrinkage" / "ledger.md").write_text("## frozen\nsealed.py  sealed subsystem\n")
    (repo / "sealed.py").write_text("x = 2\n")
    code, out = run("safe_commit.py", "-m", "shrink: edit sealed", "--", "sealed.py", cwd=repo)
    assert code == 2 and "FROZEN" in out.upper(), out
