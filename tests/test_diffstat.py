"""diffstat: LOC splits, removed/added, ranges, signature flags, gate ledger, tally, total."""
import json
import re

from conftest import commit, run, stage


def base(repo):
    (repo / "app.py").write_text("def f(a):\n    return a\n")
    commit(repo)


def test_docs_and_config_excluded_from_loc(repo):
    base(repo)
    (repo / "app.py").write_text("def f(a):\n    return a\n\ndef g(b):\n    return b\n")
    (repo / "SPEC.md").write_text("# five\nlines\nof\ndoc\ntext\n")
    (repo / "config.json").write_text('{\n "a": 1,\n "b": 2\n}\n')
    stage(repo)
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    # +3 = the code change only; the 5 md + 4 json lines must NOT count.
    assert re.search(r"net change\s+\+3 lines", out), out
    assert re.search(r"test code\s+\+0 lines", out), out


def test_test_paths_split(repo):
    base(repo)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_app.py").write_text("def test_f():\n    assert True\n")
    stage(repo)
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    assert re.search(r"test code\s+\+2 lines", out), out


def test_removed_and_added_lines_split(repo):
    (repo / "app.py").write_text("a = 1\nb = 2\nc = 3\nd = 4\n")
    commit(repo)
    (repo / "app.py").write_text("a = 1\nZ = 9\n")  # removed 3 (b,c,d), added 1 (Z)
    stage(repo)
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    assert re.search(r"code removed\s+3 lines", out), out   # deletions shown on their own line
    assert re.search(r"code added\s+1 lines", out), out     # insertions shown on their own line
    assert re.search(r"net change\s+-2 lines", out), out


def test_commit_range_scores_committed_not_worktree(repo):
    (repo / "app.py").write_text("def f(a):\n    return a\n\ndef g(b):\n    return b\n")
    commit(repo)                                        # HEAD^: f + g
    (repo / "app.py").write_text("def f(a):\n    return a\n")
    commit(repo)                                        # HEAD: removed g (−3)
    (repo / "noise.py").write_text("x = 1\n" * 50)      # dirty, unrelated, uncommitted
    stage(repo)
    code, out = run("diffstat.py", "HEAD^..HEAD", cwd=repo)
    assert code == 0, out
    assert re.search(r"net change\s+-3 lines", out), out   # the committed deletion is scored
    assert "+50" not in out, out                           # uncommitted noise NOT in the range


def test_rename_does_not_crash(repo):
    base(repo)
    (repo / "app.py").rename(repo / "core.py")
    import subprocess
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    assert code == 0 and re.search(r"files changed\s+2", out), out


def test_signature_change_is_flagged_not_a_new_symbol(repo):
    base(repo)
    (repo / "app.py").write_text("def f(a, b=1):\n    return a\n")
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    assert "public method signature" in out and "f" in out, out
    assert re.search(r"definitions added\s+0", out), "param add is a change, not a new symbol"


def test_plan_tally_buckets(repo):
    base(repo)
    # A SHRINK-PLAN with finished items: struck removal (C6), Done merge (C9),
    # struck cleanup (C10).
    (repo / "SHRINK-PLAN.md").write_text(
        "# SHRINK-PLAN\n\n"
        "| # | candidate | file | catalog | tier |\n|---|---|---|---|---|\n"
        "| ~~1~~ | deadFn | a.py | C6 | T1 |\n"
        "| ~~2~~ | noise | c.py | C10 | T0 |\n\n"
        "## Done\n\n"
        "| # | candidate | file | catalog | tier |\n|---|---|---|---|---|\n"
        "| 3 | dupBlock | b.py | C9 | T1 |\n")
    (repo / "app.py").write_text("def f(a):\n    return a\n\ndef g(b):\n    return b\n")
    stage(repo)
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    assert re.search(r"1 dead-code", out) and re.search(r"1 duplicate", out) \
        and re.search(r"1 cleanup", out), out


def test_gate_ledger_flags_unjustified(repo):
    base(repo)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "shrinkage-gates.jsonl").write_text(
        json.dumps({"symbols": ["g"], "rung": 5, "task": "t"}) + "\n")
    (repo / "app.py").write_text(
        "def f(a):\n    return a\n\ndef g(b):\n    return b\n\ndef h(c):\n    return c\n")
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    line = next(l for l in out.splitlines() if "reuse-gate" in l)
    flagged = line.split(":")[1].split("—")[0]
    assert "h" in flagged and "g" not in flagged, line


def test_no_ledger_no_flag(repo):
    base(repo)
    (repo / "app.py").write_text("def f(a):\n    return a\n\ndef h(c):\n    return c\n")
    code, out = run("diffstat.py", "HEAD", cwd=repo)
    assert "reuse-gate" not in out


def test_trend_reports_pending_deprecations(repo):
    base(repo)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "shrinkage-log.jsonl").write_text(
        json.dumps({"ts": "t", "ref": "HEAD", "net_app": -3, "net_test": 0,
                    "files": 1, "new": [], "removed": ["x"]}) + "\n")
    (repo / "DEPRECATIONS.md").write_text(
        "# Shims\n- [ ] old_name -> new_name (remove 2026-09)\n- [ ] legacy() (remove 2026-10)\n- [x] done()\n")
    code, out = run("diffstat.py", "--trend", cwd=repo)
    assert "pending removal: 2" in out, out


def test_total_sums_all_shave_commits(repo):
    (repo / "app.py").write_text("".join(f"x{i} = {i}\n" for i in range(20)))
    commit(repo)                                                        # baseline (not a shave)
    (repo / "app.py").write_text("".join(f"x{i} = {i}\n" for i in range(15)))
    commit(repo, "shrink: remove dead\n\ncatalog: C6, tier T1\nnet LOC: -5")   # −5, removed
    (repo / "app.py").write_text("".join(f"x{i} = {i}\n" for i in range(11)))
    commit(repo, "shrink: dedup block\n\ncatalog: C9, tier T1\nnet LOC: -4")    # −4, merged
    code, out = run("diffstat.py", "--total", cwd=repo)
    assert code == 0, out
    assert re.search(r"shave commits\s+2", out), out
    assert re.search(r"net change\s+-9 lines", out), out        # summed across BOTH, not just last
    assert re.search(r"1 dead-code", out) and re.search(r"1 duplicate", out), out


def test_log_stores_cat_and_est(repo):
    (repo / "app.py").write_text("a = 1\nb = 2\n")
    commit(repo)
    (repo / "app.py").write_text("a = 1\n")
    stage(repo)
    run("diffstat.py", "HEAD", "--log", "--cat", "C6", "--est", "-1", cwd=repo)
    entry = json.loads((repo / ".git" / "info" / "shrinkage-log.jsonl").read_text().splitlines()[-1])
    assert entry["cat"] == "C6" and entry["est"] == -1 and entry["ref"] == "HEAD", entry


def test_trend_shows_realization_factor(repo):
    base(repo)
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / ".claude" / "shrinkage-log.jsonl").write_text(
        json.dumps({"ts": "t", "net_app": -40, "cat": "C9", "est": -100}) + "\n")
    code, out = run("diffstat.py", "--trend", cwd=repo)
    assert "C9" in out and "40%" in out, out          # actual 40 / est 100


def test_shave_only_isolates_matched_commits_in_a_mixed_range(repo):
    # P2.11: a range holding a shave (-4) AND unrelated feature work (+20) scores
    # +16 as a whole (misleading) — --shave-only isolates the shave and flags the rest.
    (repo / "app.py").write_text("".join(f"x{i} = {i}\n" for i in range(10)))
    commit(repo)
    (repo / "app.py").write_text("".join(f"x{i} = {i}\n" for i in range(6)))
    commit(repo, "shrink: drop dead tail\n\ncatalog: C6, tier T1\nnet LOC: -4")
    (repo / "feature.py").write_text("".join(f"f{i} = {i}\n" for i in range(20)))
    commit(repo, "feat: unrelated feature work")
    code, out = run("diffstat.py", "HEAD~2..HEAD", "--shave-only", "--no-color", cwd=repo)
    assert code == 0, out
    assert "1 of 2 commits match shrink:,fix:" in out, out
    assert "-4 lines" in out, out                       # the shave alone, not the +16 whole
    assert "entanglement" in out, out
    assert "1 of 2 commits are not shrink:,fix:" in out, out
    assert "+20 app lines" in out and "= +16 lines" in out, out


def test_shave_only_custom_prefix(repo):
    (repo / "app.py").write_text("a = 1\n")
    commit(repo)
    (repo / "app.py").write_text("a = 1\nb = 2\nc = 3\n")
    commit(repo, "feat: add two")
    (repo / "app.py").write_text("a = 1\nb = 2\n")
    commit(repo, "shrink: trim one\n\ncatalog: C6, tier T1\nnet LOC: -1")
    code, out = run("diffstat.py", "HEAD~2..HEAD", "--prefix", "feat:", "--no-color", cwd=repo)
    assert code == 0, out
    assert "1 of 2 commits match feat:" in out, out
    assert "+2 lines" in out, out                       # only the feat commit, not the -1 shave


def test_shave_only_requires_a_range(repo):
    (repo / "app.py").write_text("a = 1\n")
    commit(repo)
    code, out = run("diffstat.py", "HEAD", "--shave-only", "--no-color", cwd=repo)
    assert "needs a committed range" in out, out


def test_log_lives_in_git_dir_not_working_tree(repo):
    # P2.6: the log must land in .git/info/ so it can't block a checkout during
    # recovery or get swept into a commit — never in the working tree.
    (repo / "app.py").write_text("a = 1\nb = 2\n")
    commit(repo)
    (repo / "app.py").write_text("a = 1\n")
    stage(repo)
    run("diffstat.py", "HEAD", "--log", cwd=repo)
    assert (repo / ".git" / "info" / "shrinkage-log.jsonl").exists()
    assert not (repo / ".claude" / "shrinkage-log.jsonl").exists()


def test_log_migrates_from_old_working_tree_location(repo):
    # A log left at the old .claude/ path is moved into .git/info/ on first read,
    # preserving its entries — no history lost across the relocation.
    base(repo)
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / ".claude" / "shrinkage-log.jsonl").write_text(
        json.dumps({"ts": "t", "net_app": -7, "cat": "C6", "est": -10}) + "\n")
    run("diffstat.py", "--trend", cwd=repo)
    new = repo / ".git" / "info" / "shrinkage-log.jsonl"
    assert new.exists(), "log should have migrated into .git/info/"
    assert not (repo / ".claude" / "shrinkage-log.jsonl").exists(), "old log should be removed"
    assert "net_app" in new.read_text() and "-7" in new.read_text()
