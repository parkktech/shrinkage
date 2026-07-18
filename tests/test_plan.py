"""plan.py — open / done / restamp on a sample SHRINK-PLAN.md."""
import json

from conftest import commit, run

SAMPLE = """# SHRINK-PLAN
<!-- map-fp: oldfp -->
<!-- est-savings: -999 -->

| # | candidate | file:line | catalog | tier | est. net LOC | effort | confidence | coverage | evidence |
|---|---|---|---|---|---|---|---|---|---|
| 1 | deadFn | a.py:10 | C6 | T1 | -50 | S | high | - | x0; grep 0 |
| 2 | dupBlk | b.py:20 | C9 | T1 | -30 | M | med | - | dupes |

## Done

| # | candidate | file:line | catalog | tier | est. net LOC | effort | confidence | coverage | evidence |
|---|---|---|---|---|---|---|---|---|---|
| 3 | old | c.py | C10 | T0 | -5 | S | high | - | done abc123 |
"""


def test_open_lists_open_rows_only(repo):
    (repo / "SHRINK-PLAN.md").write_text(SAMPLE)
    code, out = run("plan.py", "open", cwd=repo)
    assert code == 0, out
    assert "#1" in out and "#2" in out and "deadFn" in out
    assert "#3" not in out, "rows under ## Done are not open"


def test_done_strikes_annotates_and_calibrates(repo):
    (repo / "SHRINK-PLAN.md").write_text(SAMPLE)
    code, out = run("plan.py", "done", "1", "deadbeef", "-48", cwd=repo)
    assert code == 0, out
    text = (repo / "SHRINK-PLAN.md").read_text()
    assert "~~1~~" in text and "deadbeef" in text, text          # struck + annotated
    entry = json.loads((repo / ".git" / "info" / "shrinkage-log.jsonl").read_text().splitlines()[-1])
    assert entry["cat"] == "C6" and entry["est"] == -50 and entry["net_app"] == -48, entry
    _, out2 = run("plan.py", "open", cwd=repo)
    assert "#1" not in out2 and "#2" in out2, out2               # #1 no longer open


def test_done_derives_actual_and_sha_from_git(repo):
    # #5: with no actual passed, done resolves the ref to a real sha and computes
    # the net LOC from git — no literal "HEAD" stored, no hand-passed number.
    import re as _re
    (repo / "SHRINK-PLAN.md").write_text(SAMPLE)
    (repo / "app.py").write_text("".join(f"x{i} = 1\n" for i in range(10)))
    commit(repo)                                                   # baseline
    (repo / "app.py").write_text("".join(f"x{i} = 1\n" for i in range(4)))   # -6 app lines
    commit(repo, "shrink: drop tail")                             # the shave commit = HEAD
    code, out = run("plan.py", "done", "1", "HEAD", cwd=repo)     # NO actual argument
    assert code == 0, out
    text = (repo / "SHRINK-PLAN.md").read_text()
    assert "~~1~~" in text and "actual -6" in text, text
    assert _re.search(r"done [0-9a-f]{7,}", text), "stores a real sha, not the literal HEAD"
    assert "done HEAD" not in text
    entry = json.loads((repo / ".git" / "info" / "shrinkage-log.jsonl").read_text().splitlines()[-1])
    assert entry["cat"] == "C6" and entry["net_app"] == -6, entry


def test_restamp_recomputes_est_savings(repo):
    (repo / "SHRINK-PLAN.md").write_text(SAMPLE)
    code, out = run("plan.py", "restamp", cwd=repo)
    assert code == 0, out
    text = (repo / "SHRINK-PLAN.md").read_text()
    assert "est-savings: -80" in text, text                     # -50 + -30 (Done row excluded)
