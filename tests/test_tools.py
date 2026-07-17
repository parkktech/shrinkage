"""gatelog, badge, coverage_check."""
import json

from conftest import run


def test_gatelog_add_list_and_rung7_guard(repo):
    code, out = run("gatelog.py", "add", "--task", "t", "--rung", "7", cwd=repo)
    assert code != 0, "rung 7 without --note must be rejected"
    code, out = run("gatelog.py", "add", "--task", "add csv", "--rung", "2",
                    "--symbols", "render,helper", cwd=repo)
    assert code == 0 and "gate recorded" in out
    code, out = run("gatelog.py", "list", cwd=repo)
    assert "add csv" in out and "render" in out


def test_badge_from_trend(repo):
    (repo / ".claude").mkdir()
    (repo / ".claude" / "shrinkage-log.jsonl").write_text(
        json.dumps({"net_app": -42, "net_test": 3}) + "\n")
    code, out = run("badge.py", cwd=repo)
    svg = (repo / ".claude" / "shrinkage-badge.svg").read_text()
    assert code == 0 and "-42 LOC" in svg and "#009E73" in svg


def test_coverage_lcov_and_tiers(repo):
    (repo / "lcov.info").write_text(
        "SF:src/a.py\nDA:1,5\nDA:2,0\nend_of_record\nSF:src/b.py\nDA:1,0\nend_of_record\n")
    code, out = run("coverage_check.py", "src/a.py", "src/b.py", "src/c.py", cwd=repo)
    assert "50%" in out and "T1 eligible" not in out.split("src/b.py")[1].split("\n")[0]
    assert "NOT IN REPORT" in out and "T2" in out


def test_coverage_missing_report_means_all_t2(repo):
    code, out = run("coverage_check.py", "x.py", cwd=repo)
    assert "no coverage report found" in out and "T2" in out
