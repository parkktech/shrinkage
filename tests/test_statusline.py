"""statusline.py — trend line + GSD-style update hint (cached, never blocking)."""
import json
import subprocess
import sys
import time

from conftest import SCRIPTS, run

import statusline


def _run_stdin(args, stdin_text, cwd):
    r = subprocess.run([sys.executable, str(SCRIPTS / "statusline.py"), *args],
                       capture_output=True, text=True, input=stdin_text, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def test_semver_and_latest_from_tags():
    assert statusline.semver("v0.29.1") == (0, 29, 1)
    assert statusline.semver("0.9.10") == (0, 9, 10)
    assert statusline.semver("not-a-version") is None
    sample = "\n".join([
        "aaa\trefs/tags/v0.9.0",
        "bbb\trefs/tags/v0.29.1",
        "ccc\trefs/tags/v0.29.1^{}",          # peeled — ignored
        "ddd\trefs/tags/v0.10.0",             # 0.10 > 0.9 numerically, not lexically
        "eee\trefs/tags/release-candidate",   # non-semver — ignored
    ])
    assert statusline.latest_from_tags(sample) == "0.29.1"


def test_hint_shown_when_remote_is_newer(repo, monkeypatch):
    cache = repo / "update-cache.json"
    cache.write_text(json.dumps({"checked_at": int(time.time()), "latest": "9.9.9"}))
    monkeypatch.setenv("SRK_UPDATE_CACHE", str(cache))
    code, out = run("statusline.py", cwd=repo)
    assert code == 0, out
    assert "⬆ /srk:update to v9.9.9" in out, out


def test_no_hint_when_current(repo, monkeypatch):
    inst = statusline.installed_version()          # repo checkout's plugin.json
    cache = repo / "update-cache.json"
    cache.write_text(json.dumps({"checked_at": int(time.time()), "latest": inst}))
    monkeypatch.setenv("SRK_UPDATE_CACHE", str(cache))
    code, out = run("statusline.py", cwd=repo)
    assert code == 0, out
    assert "⬆" not in out, out


def test_standalone_bar_renders_session_basics(repo, monkeypatch):
    # Standalone mode: model │ dir │ ctx meter │ srk — so choosing Shrinkage's
    # bar never loses what an existing status line would have shown.
    cache = repo / "update-cache.json"
    cache.write_text(json.dumps({"checked_at": int(time.time()), "latest": "0.0.1"}))
    monkeypatch.setenv("SRK_UPDATE_CACHE", str(cache))
    info = json.dumps({"model": {"display_name": "Opus"},
                       "workspace": {"current_dir": str(repo)},
                       "context_window": {"used_percentage": 31}})
    code, out = _run_stdin([], info, repo)
    assert code == 0, out
    assert "Opus │" in out and repo.name in out, out
    assert "ctx ███░░░░░░░ 31%" in out, out
    assert "srk" in out, out


def test_segment_mode_prints_only_the_srk_part(repo, monkeypatch):
    # --segment is for chaining onto an EXISTING status line (e.g. GSD's):
    # just the srk part, no model/dir/ctx duplication.
    cache = repo / "update-cache.json"
    cache.write_text(json.dumps({"checked_at": int(time.time()), "latest": "9.9.9"}))
    monkeypatch.setenv("SRK_UPDATE_CACHE", str(cache))
    info = json.dumps({"model": {"display_name": "Opus"},
                       "context_window": {"used_percentage": 31}})
    code, out = _run_stdin(["--segment"], info, repo)
    assert code == 0, out
    assert "Opus" not in out and "ctx" not in out and "│" not in out, out
    assert out.startswith("srk"), out
    assert "⬆ /srk:update to v9.9.9" in out, out


def test_segment_shows_todo_gate(repo, monkeypatch):
    # #7 field report: the bar says at a glance whether shaving is unblocked.
    cache = repo / "update-cache.json"
    cache.write_text(json.dumps({"checked_at": int(time.time()), "latest": "0.0.1"}))
    monkeypatch.setenv("SRK_UPDATE_CACHE", str(cache))
    (repo / "SHRINK-PLAN.md").write_text(
        "# P\n\n## TODO before shaving\n\n- [ ] fix fees\n\n- [ ] update plugin\n")
    code, out = run("statusline.py", "--segment", cwd=repo)
    assert code == 0 and "TODO 2" in out, out
    (repo / "SHRINK-PLAN.md").write_text(
        "# P\n\n## TODO before shaving\n\n- [x] fix fees\n\n- [x] update plugin\n")
    code, out = run("statusline.py", "--segment", cwd=repo)
    assert "TODO clear" in out, out


def test_check_update_reads_tags_from_remote(repo, monkeypatch, tmp_path):
    # A local git repo stands in for the marketplace origin — fully offline.
    remote = tmp_path / "fake-remote"
    remote.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=remote, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.co"], cwd=remote, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=remote, check=True)
    (remote / "f.txt").write_text("x\n")
    subprocess.run(["git", "add", "-A"], cwd=remote, check=True)
    subprocess.run(["git", "commit", "-qm", "c"], cwd=remote, check=True)
    for tag in ("v0.9.0", "v0.30.0", "v0.10.0"):
        subprocess.run(["git", "tag", tag], cwd=remote, check=True)

    cache = tmp_path / "cache.json"
    monkeypatch.setenv("SRK_UPDATE_CACHE", str(cache))
    monkeypatch.setenv("SRK_REPO_URL", str(remote))
    code, out = run("statusline.py", "--check-update", cwd=repo)
    assert code == 0, out
    data = json.loads(cache.read_text())
    assert data["latest"] == "0.30.0", data
    assert data["checked_at"] > 0


# --- split cache TTL (spec: 2026-07-20-drift-in-conversation) ---------------


def test_successful_check_fresh_within_full_ttl():
    now = 1_000_000
    data = {"checked_at": now - 5 * 3600, "latest": "0.41.0"}
    assert statusline.cache_stale(data, now=now) is False


def test_successful_check_stale_past_full_ttl():
    now = 1_000_000
    data = {"checked_at": now - 7 * 3600, "latest": "0.41.0"}
    assert statusline.cache_stale(data, now=now) is True


def test_failed_check_stale_well_before_full_ttl():
    """Regression for the measured case: a null cached at 1.2h suppressed the
    hint for 6h because a failure aged at the success TTL."""
    now = 1_000_000
    data = {"checked_at": now - int(1.2 * 3600), "latest": None}
    assert statusline.cache_stale(data, now=now) is True


def test_failed_check_fresh_inside_retry_window():
    """Still backs off — a broken remote must not cause a respawn storm."""
    now = 1_000_000
    data = {"checked_at": now - 5 * 60, "latest": None}
    assert statusline.cache_stale(data, now=now) is False


def test_missing_cache_is_stale():
    assert statusline.cache_stale({}, now=1_000_000) is True


def test_future_checked_at_is_not_stale():
    """Clock skew must never trigger a refresh storm."""
    now = 1_000_000
    assert statusline.cache_stale({"checked_at": now + 9999, "latest": None}, now=now) is False


def test_failed_ttl_is_shorter_than_success_ttl():
    assert statusline.TTL_FAILED < statusline.TTL
