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


GATES = """# SHRINK-PLAN
| # | candidate | file:line | catalog | tier | est. net LOC | effort | confidence | coverage | evidence |
|---|---|---|---|---|---|---|---|---|---|
| 1 | a | a.py:1 | C6 | T1 | -10 | S | high | gate: tests/GoodTest.php | x |
| 2 | b | b.py:1 | C6 | T1 | -10 | S | high | gate: tests/ZeroTest.php | x |
| 3 | c | c.py:1 | C9 | T1 | -10 | S | high | gate: tests/RedTest.php | x |
"""

FAKE_RUNNER = """import sys
s = sys.argv[-1]
if "Good" in s:
    print("OK (4 tests, 12 assertions)"); sys.exit(0)
if "Zero" in s:
    print("OK (21 tests, 0 assertions)"); sys.exit(0)
print("Tests: 5, Assertions: 2, Errors: 3.")
print("ERRORS!"); sys.exit(2)
"""


def test_verify_gates_runs_and_stamps_actual_colors(repo):
    # #1/#2 field report: a named gate nobody ran is how a red suite gets
    # recorded green. verify-gates runs each suite in its own process and
    # stamps the truth into the row; RED/0-ASSERT make it exit 1.
    import sys as _sys
    (repo / "SHRINK-PLAN.md").write_text(GATES)
    (repo / "fake_runner.py").write_text(FAKE_RUNNER)
    code, out = run("plan.py", "verify-gates", "--runner",
                    f"{_sys.executable} fake_runner.py", cwd=repo)
    assert code == 1, out                                      # RED + 0-ASSERT present
    text = (repo / "SHRINK-PLAN.md").read_text()
    assert "verified: green" in text and "verified: 0-ASSERT" in text \
        and "verified: RED" in text, text
    assert "repair-first" in out, out


def test_suite_tokens_and_classification_cover_the_language_matrix():
    import plan
    cell = ("gate: tests/Feature/InvoiceTest.php + src/test/java/AccTest.java + "
            "PricerTests.cs + FmtTest.kt + pkg/fmt_test.go + ui/chart.spec.ts + "
            "tests/test_plan.py")
    toks = set(plan._SUITE_TOKEN.findall(cell))
    for expect in ("tests/Feature/InvoiceTest.php", "src/test/java/AccTest.java",
                   "PricerTests.cs", "FmtTest.kt", "pkg/fmt_test.go",
                   "ui/chart.spec.ts", "tests/test_plan.py"):
        assert expect in toks, (expect, toks)
    assert plan._classify_run(0, "ok  \tpkg/fmt\t0.01s") == "green"        # go
    assert plan._classify_run(1, "--- FAIL: TestX\nFAIL") == "RED"          # go
    assert plan._classify_run(0, "test result: ok. 4 passed; 0 failed") == "green"  # cargo
    assert plan._classify_run(0, "BUILD SUCCESSFUL in 12s") == "green"      # gradle
    assert plan._classify_run(1, "BUILD FAILED in 3s") == "RED"             # gradle
    assert plan._classify_run(0, "Tests: 3 passed, 3 total") == "green"     # jest
    assert plan._classify_run(1, "Tests: 1 failed, 3 total") == "RED"       # jest
    assert plan._classify_run(0, "Passed!  - Failed: 0, Passed: 8") == "green"  # dotnet
    assert plan._classify_run(0, "no test files") == "SKIPPED"              # go
    assert plan._suite_arg("./gradlew test --tests", "src/test/AccTest.java") == "AccTest"
    assert plan._suite_arg("go test", "pkg/fmt_test.go") == "./pkg"
    assert plan._suite_arg("vendor/bin/phpunit", "tests/FooTest.php") == "tests/FooTest.php"


def test_done_handles_deferred_rows(repo):
    (repo / "SHRINK-PLAN.md").write_text(
        SAMPLE + "\n## Deferred\n\n"
        "| id | candidate | est | why it needs YOU |\n|---|---|---|---|\n"
        "| D-30 | orphan views | -2417 | eyeball the markup |\n")
    (repo / "app.py").write_text("x = 1\n")
    commit(repo, "shrink: views\n\ncatalog: C6, tier T1")
    code, out = run("plan.py", "done", "D-30", "HEAD", cwd=repo)
    assert code == 0, out
    text = (repo / "SHRINK-PLAN.md").read_text()
    assert "~~D-30~~" in text and "done " in text, text


def test_todo_check_and_adjudicate(repo):
    (repo / "SHRINK-PLAN.md").write_text(
        SAMPLE + "\n## TODO before shaving\n\n"
        "- [ ] **[bug]** fix the fees\n      → wire keys\n\n"
        "- [ ] **[tooling]** update plugin\n      → git pull\n\n"
        "## Deferred\n\n"
        "| id | candidate | est | why it needs YOU |\n|---|---|---|---|\n"
        "| D-32 | sharpe convention | -500 | pick canonical |\n")
    code, out = run("plan.py", "todo-check", "1", cwd=repo)
    assert code == 0 and "1 item(s) remaining" in out, out
    code, out = run("plan.py", "todo-check", "plugin", cwd=repo)
    assert code == 0 and "CLEAR" in out, out
    assert (repo / "SHRINK-PLAN.md").read_text().count("- [x]") == 2
    code, out = run("plan.py", "adjudicate", "D-32", "with-rf, note the change", cwd=repo)
    assert code == 0, out
    assert "⚖ ruled" in (repo / "SHRINK-PLAN.md").read_text()
