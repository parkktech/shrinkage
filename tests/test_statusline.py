"""statusline.py — trend line + GSD-style update hint (cached, never blocking)."""
import json
import subprocess
import time

from conftest import run

import statusline


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
