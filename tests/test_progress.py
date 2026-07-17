"""progress.py — SHRINK-PLAN progress line for context-durable runs."""
from conftest import run


def test_open_and_done_counts(repo):
    (repo / "SHRINK-PLAN.md").write_text(
        "<!-- map-fp: x -->\n| # | c | tier |\n|---|---|---|\n"
        "| 1 | a | T1 |\n| 2 | b | T1 |\n## Done\n| 3 | ~~c~~ | T0 |\n")
    code, out = run("progress.py", cwd=repo)
    assert "1/3 plan items done" in out and "2 open" in out and "--auto" in out


def test_all_done(repo):
    (repo / "SHRINK-PLAN.md").write_text(
        "<!-- map-fp: x -->\n| # | c |\n|---|---|\n## Done\n| 1 | ~~a~~ |\n| 2 | ~~b~~ |\n")
    code, out = run("progress.py", cwd=repo)
    assert "complete (2/2)" in out


def test_no_plan(repo):
    code, out = run("progress.py", cwd=repo)
    assert "no SHRINK-PLAN.md" in out
