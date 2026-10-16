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


def test_hook_refreshes_only_for_source_edits(repo):
    import json
    import subprocess
    import sys
    from conftest import SCRIPTS
    seed(repo)

    def hook(path):
        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(repo / path)}})
        r = subprocess.run([sys.executable, str(SCRIPTS / "codemap.py"), "refresh", "--hook"],
                           input=payload, capture_output=True, text=True, cwd=repo)
        return r.stdout + r.stderr

    assert hook("a.py") == "", "no map yet: un-onboarded repos must stay untouched"
    assert not (repo / ".claude" / "codemap.txt").exists()
    run("codemap.py", "build", cwd=repo)
    (repo / "c.py").write_text("def gamma():\n    return 3\n")
    assert hook("README.md") == "", "non-source edits must not rescan"
    assert "gamma" not in (repo / ".claude" / "codemap.txt").read_text()
    assert "map written" in hook("c.py")
    assert "gamma" in (repo / ".claude" / "codemap.txt").read_text()


def test_hooks_json_refreshes_map_after_edits():
    import json
    from pathlib import Path
    hooks = json.loads((Path(__file__).resolve().parent.parent / "hooks" / "hooks.json").read_text())
    block = hooks["hooks"]["PostToolUse"][0]
    assert "Edit" in block["matcher"] and "Write" in block["matcher"]
    assert "refresh --hook" in block["hooks"][0]["command"]


def test_rebuild_reparses_only_changed_files(repo, monkeypatch):
    import codemap
    seed(repo)
    first = codemap.build_index(repo)
    parsed = []
    real = codemap.parse_file
    monkeypatch.setattr(codemap, "parse_file", lambda p: parsed.append(p.name) or real(p))
    (repo / "b.js").write_text("export function beta() {\n  return 2;\n}\nexport function delta() {\n  return 4;\n}\n")
    second = codemap.build_index(repo)
    assert parsed == ["b.js"], "unchanged files must come from the parse cache"
    assert second["a.py"] == first["a.py"]
    assert any(s.name == "delta" for s in second["b.js"])


def test_build_wires_gsd_agents_and_intel_idempotently(repo):
    import json
    seed(repo)
    (repo / ".planning").mkdir()
    cfg = repo / ".planning" / "config.json"
    cfg.write_text(json.dumps({"agent_skills": {"gsd-planner": ["skills/mine"]}}))
    code, out = run("codemap.py", "build", cwd=repo)
    assert "gsd wired" in out
    data = json.loads(cfg.read_text())
    assert data["agent_skills"]["gsd-planner"] == ["skills/mine", "global:srk:shrinkage"]
    assert "global:srk:shrinkage" in data["agent_skills"]["gsd-pattern-mapper"]
    assert data["intel"]["enabled"] is True
    code, out = run("codemap.py", "refresh", cwd=repo)
    assert "gsd wired" not in out, "second run must be a no-op"


def test_gsd_wire_respects_explicit_intel_off_and_opt_out(repo):
    import json
    seed(repo)
    (repo / ".planning").mkdir()
    cfg = repo / ".planning" / "config.json"
    cfg.write_text(json.dumps({"intel": {"enabled": False}}))
    run("codemap.py", "build", cwd=repo)
    assert json.loads(cfg.read_text())["intel"]["enabled"] is False
    (repo / ".claude" / "shrinkage.json").write_text(json.dumps({"gsd_wire": False}))
    cfg.write_text("{}")
    run("codemap.py", "build", cwd=repo)
    assert json.loads(cfg.read_text()) == {}
