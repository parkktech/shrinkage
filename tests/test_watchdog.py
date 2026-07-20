import json

import watchdog


def test_decide_healthy_when_heartbeat_present():
    assert watchdog.decide(enabled=True, installed=True, heartbeat=True) == "healthy"


def test_decide_warns_when_heartbeat_absent():
    assert watchdog.decide(enabled=True, installed=True, heartbeat=False) == "warn"


def test_decide_uninstalls_when_not_enabled():
    assert watchdog.decide(enabled=False, installed=True, heartbeat=False) == "uninstall"
    assert watchdog.decide(enabled=False, installed=True, heartbeat=True) == "uninstall"


def test_decide_uninstalls_when_files_gone():
    assert watchdog.decide(enabled=True, installed=False, heartbeat=False) == "uninstall"


def test_read_json_returns_empty_on_garbage(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert watchdog.read_json(p) == {}


def test_read_json_returns_empty_on_missing(tmp_path):
    assert watchdog.read_json(tmp_path / "nope.json") == {}


def test_is_enabled_scans_all_scopes(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({"enabledPlugins": {"gsd@x": True}}), encoding="utf-8")
    b.write_text(json.dumps({"enabledPlugins": {"srk@parkktech": True}}), encoding="utf-8")
    assert watchdog.is_enabled([a, b]) is True
    assert watchdog.is_enabled([a]) is False


def test_is_enabled_false_when_explicitly_disabled(tmp_path):
    a = tmp_path / "a.json"
    a.write_text(json.dumps({"enabledPlugins": {"srk@parkktech": False}}), encoding="utf-8")
    assert watchdog.is_enabled([a]) is False


def test_take_heartbeat_consumes_on_read(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, "STATE", tmp_path / "state")
    hb = tmp_path / "state" / "hb"
    hb.mkdir(parents=True)
    (hb / "sess-1").write_text("", encoding="utf-8")

    assert watchdog.take_heartbeat("sess-1") is True    # present, now consumed
    assert watchdog.take_heartbeat("sess-1") is False   # gone on second read


def test_take_heartbeat_false_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, "STATE", tmp_path / "state")
    assert watchdog.take_heartbeat("sess-1") is False


def test_write_settings_preserves_foreign_keys(tmp_path):
    s = tmp_path / "settings.json"
    s.write_text(json.dumps({
        "statusLine": {"type": "command", "command": "gsd-statusline.js"},
        "enabledPlugins": {"srk@parkktech": True},
    }), encoding="utf-8")

    watchdog.add_hooks(s, "/usr/bin/python3", "/home/u/.claude/shrinkage/watchdog.py")

    out = json.loads(s.read_text(encoding="utf-8"))
    assert out["statusLine"] == {"type": "command", "command": "gsd-statusline.js"}
    assert out["enabledPlugins"] == {"srk@parkktech": True}
    assert "SessionStart" in out["hooks"]
    assert "UserPromptSubmit" in out["hooks"]


def test_add_hooks_is_idempotent(tmp_path):
    s = tmp_path / "settings.json"
    s.write_text("{}", encoding="utf-8")

    watchdog.add_hooks(s, "/usr/bin/python3", "/home/u/.claude/shrinkage/watchdog.py")
    watchdog.add_hooks(s, "/usr/bin/python3", "/home/u/.claude/shrinkage/watchdog.py")

    out = json.loads(s.read_text(encoding="utf-8"))
    assert len(out["hooks"]["SessionStart"]) == 1
    assert len(out["hooks"]["UserPromptSubmit"]) == 1


def test_add_hooks_keeps_other_tools_hooks(tmp_path):
    s = tmp_path / "settings.json"
    s.write_text(json.dumps({
        "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "other-tool.sh"}]}]}
    }), encoding="utf-8")

    watchdog.add_hooks(s, "/usr/bin/python3", "/home/u/.claude/shrinkage/watchdog.py")

    entries = json.loads(s.read_text(encoding="utf-8"))["hooks"]["SessionStart"]
    assert len(entries) == 2
    assert any("other-tool.sh" in e["hooks"][0]["command"] for e in entries)


def test_remove_hooks_removes_only_ours(tmp_path):
    s = tmp_path / "settings.json"
    s.write_text(json.dumps({
        "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "other-tool.sh"}]}]}
    }), encoding="utf-8")
    watchdog.add_hooks(s, "/usr/bin/python3", "/home/u/.claude/shrinkage/watchdog.py")

    watchdog.remove_hooks(s)

    out = json.loads(s.read_text(encoding="utf-8"))
    entries = out["hooks"]["SessionStart"]
    assert len(entries) == 1
    assert "other-tool.sh" in entries[0]["hooks"][0]["command"]
    assert not out["hooks"].get("UserPromptSubmit")


def test_add_hooks_refuses_malformed_settings(tmp_path):
    s = tmp_path / "settings.json"
    s.write_text("{ this is not json", encoding="utf-8")

    assert watchdog.add_hooks(s, "/usr/bin/python3", "/x/watchdog.py") is False
    assert s.read_text(encoding="utf-8") == "{ this is not json"  # untouched


def test_add_hooks_backs_up_original_once(tmp_path):
    """Atomic replace protects against a torn write, not against writing
    valid-but-wrong JSON. Keep one pristine copy of what we found."""
    s = tmp_path / "settings.json"
    original = json.dumps({"statusLine": {"command": "mine.js"}})
    s.write_text(original, encoding="utf-8")

    watchdog.add_hooks(s, "/usr/bin/python3", "/x/shrinkage/watchdog.py")
    backup = tmp_path / "settings.json.srk-bak"
    assert json.loads(backup.read_text(encoding="utf-8")) == json.loads(original)

    # A later write must not clobber the pristine copy with an already-modified one.
    watchdog.add_hooks(s, "/usr/bin/python3", "/x/shrinkage/watchdog.py")
    assert json.loads(backup.read_text(encoding="utf-8")) == json.loads(original)


def test_add_hooks_skips_write_when_already_registered(tmp_path, monkeypatch):
    """plant fires every boot; a second identical add_hooks must NOT rewrite
    the user's global settings (no mtime churn, no race with other writers)."""
    s = tmp_path / "settings.json"
    s.write_text("{}", encoding="utf-8")
    writes = []
    real = watchdog.write_settings
    monkeypatch.setattr(watchdog, "write_settings",
                        lambda p, d: (writes.append(1), real(p, d))[1])

    assert watchdog.add_hooks(s, "/usr/bin/python3", "/x/shrinkage/watchdog.py") is True
    assert len(writes) == 1                       # first call: registers, writes
    assert watchdog.add_hooks(s, "/usr/bin/python3", "/x/shrinkage/watchdog.py") is True
    assert len(writes) == 1                       # second call: no write at all


def test_add_hooks_rewrites_when_command_changed(tmp_path, monkeypatch):
    """A changed interpreter/script path IS a real change → it must write."""
    s = tmp_path / "settings.json"
    s.write_text("{}", encoding="utf-8")
    watchdog.add_hooks(s, "/usr/bin/python3", "/x/shrinkage/watchdog.py")
    writes = []
    real = watchdog.write_settings
    monkeypatch.setattr(watchdog, "write_settings",
                        lambda p, d: (writes.append(1), real(p, d))[1])

    assert watchdog.add_hooks(s, "/usr/bin/python3.12", "/x/shrinkage/watchdog.py") is True
    assert len(writes) == 1                       # different python → rewrite
    cmd = json.loads(s.read_text())["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "python3.12" in cmd


def _wire(monkeypatch, tmp_path):
    """Point every filesystem anchor at a sandbox."""
    root = tmp_path / "claude" / "shrinkage"
    monkeypatch.setattr(watchdog, "ROOT", root)
    monkeypatch.setattr(watchdog, "STATE", root / "state")
    monkeypatch.setattr(watchdog, "STABLE", root / "watchdog.py")
    monkeypatch.setattr(watchdog, "USER_SETTINGS", tmp_path / "claude" / "settings.json")
    return root


def test_check_warns_when_no_heartbeat(monkeypatch, tmp_path, capsys):
    _wire(monkeypatch, tmp_path)
    monkeypatch.setattr(watchdog, "is_enabled", lambda scopes: True)
    monkeypatch.setattr(watchdog, "is_installed", lambda: True)

    rc = watchdog.main(["check"], json.dumps({"session_id": "s1"}))

    assert rc == 0
    assert "installed but not loaded" in capsys.readouterr().out


def test_check_silent_when_heartbeat_present(monkeypatch, tmp_path, capsys):
    root = _wire(monkeypatch, tmp_path)
    monkeypatch.setattr(watchdog, "is_enabled", lambda scopes: True)
    monkeypatch.setattr(watchdog, "is_installed", lambda: True)
    (root / "state" / "hb").mkdir(parents=True)
    (root / "state" / "hb" / "s1").write_text("", encoding="utf-8")

    watchdog.main(["check"], json.dumps({"session_id": "s1"}))

    assert capsys.readouterr().out == ""


def test_check_only_fires_once_per_session(monkeypatch, tmp_path, capsys):
    _wire(monkeypatch, tmp_path)
    monkeypatch.setattr(watchdog, "is_enabled", lambda scopes: True)
    monkeypatch.setattr(watchdog, "is_installed", lambda: True)

    watchdog.main(["check"], json.dumps({"session_id": "s1"}))
    capsys.readouterr()
    watchdog.main(["check"], json.dumps({"session_id": "s1"}))

    assert capsys.readouterr().out == ""


def test_boot_rearms_check_for_same_session(monkeypatch, tmp_path, capsys):
    """--continue reuses session_id; boot must re-arm or the continued
    session is silenced by the marker its own earlier run wrote."""
    _wire(monkeypatch, tmp_path)
    monkeypatch.setattr(watchdog, "is_enabled", lambda scopes: True)
    monkeypatch.setattr(watchdog, "is_installed", lambda: True)

    watchdog.main(["check"], json.dumps({"session_id": "s1"}))
    capsys.readouterr()
    watchdog.main(["boot"], json.dumps({"session_id": "s1"}))
    watchdog.main(["check"], json.dumps({"session_id": "s1"}))

    assert "installed but not loaded" in capsys.readouterr().out


def test_check_self_uninstalls_when_disabled(monkeypatch, tmp_path, capsys):
    _wire(monkeypatch, tmp_path)
    settings = tmp_path / "claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}", encoding="utf-8")
    watchdog.add_hooks(settings, "/usr/bin/python3", "/x/shrinkage/watchdog.py")
    monkeypatch.setattr(watchdog, "is_enabled", lambda scopes: False)
    monkeypatch.setattr(watchdog, "is_installed", lambda: True)

    watchdog.main(["check"], json.dumps({"session_id": "s1"}))

    out = json.loads(settings.read_text(encoding="utf-8"))
    assert all(not any("watchdog.py" in h["command"] for h in e["hooks"])
               for e in out["hooks"].get("SessionStart", []))
    assert capsys.readouterr().out == ""


def test_check_survives_garbage_stdin(monkeypatch, tmp_path, capsys):
    _wire(monkeypatch, tmp_path)
    assert watchdog.main(["check"], "not json at all") == 0
    assert capsys.readouterr().out == ""


def test_uninstall_clears_stale_not_loaded_flag(monkeypatch, tmp_path, capsys):
    """A warn-state flag must not outlive the plugin: uninstall clears it so
    the status line can't keep showing 'not loaded' after removal."""
    root = _wire(monkeypatch, tmp_path)
    flag = root / "state" / "not-loaded"
    flag.parent.mkdir(parents=True)
    flag.write_text("", encoding="utf-8")
    monkeypatch.setattr(watchdog, "is_enabled", lambda scopes: False)
    monkeypatch.setattr(watchdog, "is_installed", lambda: False)

    watchdog.main(["check"], json.dumps({"session_id": "s1"}))

    assert not flag.exists()


def test_plant_copies_script_and_registers(monkeypatch, tmp_path):
    root = _wire(monkeypatch, tmp_path)
    settings = tmp_path / "claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}", encoding="utf-8")

    watchdog.main(["plant"], "")

    assert (root / "watchdog.py").exists()
    cmds = json.dumps(json.loads(settings.read_text(encoding="utf-8")))
    assert "watchdog.py" in cmds


def test_hooks_json_writes_heartbeat_and_plants():
    from pathlib import Path as _P
    hooks = json.loads((_P(__file__).resolve().parent.parent / "hooks" / "hooks.json")
                       .read_text(encoding="utf-8"))
    commands = " ".join(h["command"]
                        for block in hooks["hooks"]["SessionStart"]
                        for h in block["hooks"])
    assert "watchdog.py" in commands
    assert "plant" in commands
    assert "heartbeat" in commands


def test_segment_flags_not_loaded(tmp_path, monkeypatch):
    import statusline
    monkeypatch.setattr(statusline, "NOT_LOADED_FLAG", tmp_path / "flag")
    (tmp_path / "flag").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert statusline.srk_segment().startswith("⚠ srk not loaded")


def test_segment_normal_when_no_flag(tmp_path, monkeypatch):
    import statusline
    monkeypatch.setattr(statusline, "NOT_LOADED_FLAG", tmp_path / "flag")
    monkeypatch.chdir(tmp_path)
    assert not statusline.srk_segment().startswith("⚠")


# --- version drift (spec: 2026-07-20-drift-in-conversation) -----------------


def test_drift_when_latest_exceeds_installed():
    assert watchdog.decide_drift("0.40.3", "0.41.0") == "drift"


def test_no_drift_when_equal():
    assert watchdog.decide_drift("0.41.0", "0.41.0") == "healthy"


def test_no_drift_when_local_build_ahead_of_tags():
    assert watchdog.decide_drift("0.42.0", "0.41.0") == "healthy"


def test_no_drift_when_latest_unknown():
    assert watchdog.decide_drift("0.40.3", None) == "healthy"


def test_no_drift_when_installed_unknown_vendored():
    assert watchdog.decide_drift(None, "0.41.0") == "healthy"


def test_no_drift_on_unparseable_semver():
    assert watchdog.decide_drift("0.40.3", "not-a-version") == "healthy"
    assert watchdog.decide_drift("main", "0.41.0") == "healthy"


def test_drift_across_minor_and_major():
    assert watchdog.decide_drift("0.9.0", "0.10.0") == "drift"
    assert watchdog.decide_drift("0.41.0", "1.0.0") == "drift"


def test_read_update_cache_missing_is_silent(tmp_path, monkeypatch):
    monkeypatch.setenv("SRK_UPDATE_CACHE", str(tmp_path / "nope.json"))
    assert watchdog.cached_latest() is None


def test_read_update_cache_malformed_is_silent(tmp_path, monkeypatch):
    p = tmp_path / "u.json"
    p.write_text("{broken", encoding="utf-8")
    monkeypatch.setenv("SRK_UPDATE_CACHE", str(p))
    assert watchdog.cached_latest() is None


def test_read_update_cache_null_latest_is_silent(tmp_path, monkeypatch):
    p = tmp_path / "u.json"
    p.write_text(json.dumps({"checked_at": 1, "latest": None}), encoding="utf-8")
    monkeypatch.setenv("SRK_UPDATE_CACHE", str(p))
    assert watchdog.cached_latest() is None


def test_read_update_cache_returns_latest(tmp_path, monkeypatch):
    p = tmp_path / "u.json"
    p.write_text(json.dumps({"checked_at": 1, "latest": "0.41.0"}), encoding="utf-8")
    monkeypatch.setenv("SRK_UPDATE_CACHE", str(p))
    assert watchdog.cached_latest() == "0.41.0"


def test_installed_version_from_install_path(tmp_path, monkeypatch):
    plug = tmp_path / "cache" / "shrinkage" / "0.40.3"
    (plug / ".claude-plugin").mkdir(parents=True)
    (plug / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"version": "0.40.3"}), encoding="utf-8")
    home = tmp_path / "home"
    (home / ".claude" / "plugins").mkdir(parents=True)
    (home / ".claude" / "plugins" / "installed_plugins.json").write_text(
        json.dumps({"plugins": {"srk@parkktech": [
            {"installPath": str(plug), "version": "ignored-if-plugin-json-wins"}]}}),
        encoding="utf-8")
    monkeypatch.setattr(watchdog, "HOME", home)
    assert watchdog.installed_version() == "0.40.3"


def test_installed_version_falls_back_to_registry_entry(tmp_path, monkeypatch):
    plug = tmp_path / "plug"
    plug.mkdir()  # real dir, but no .claude-plugin/plugin.json
    home = tmp_path / "home"
    (home / ".claude" / "plugins").mkdir(parents=True)
    (home / ".claude" / "plugins" / "installed_plugins.json").write_text(
        json.dumps({"plugins": {"srk@parkktech": [
            {"installPath": str(plug), "version": "0.40.3"}]}}), encoding="utf-8")
    monkeypatch.setattr(watchdog, "HOME", home)
    assert watchdog.installed_version() == "0.40.3"


def test_installed_version_none_when_not_installed(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude" / "plugins").mkdir(parents=True)
    (home / ".claude" / "plugins" / "installed_plugins.json").write_text(
        json.dumps({"plugins": {}}), encoding="utf-8")
    monkeypatch.setattr(watchdog, "HOME", home)
    assert watchdog.installed_version() is None


def test_warn_outranks_drift(tmp_path, monkeypatch, capsys):
    """A plugin that did not load is the more urgent problem; never report both."""
    monkeypatch.setattr(watchdog, "STATE", tmp_path / "state")
    monkeypatch.setattr(watchdog, "is_enabled", lambda *a: True)
    monkeypatch.setattr(watchdog, "is_installed", lambda: True)
    monkeypatch.setattr(watchdog, "take_heartbeat", lambda sid: False)  # not loaded
    monkeypatch.setattr(watchdog, "installed_version", lambda: "0.40.3")
    monkeypatch.setattr(watchdog, "cached_latest", lambda: "0.41.0")
    watchdog.cmd_check("s1")
    out = capsys.readouterr().out
    assert "installed but not loaded" in out
    assert "0.41.0" not in out


def test_drift_reported_when_healthy(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(watchdog, "STATE", tmp_path / "state")
    monkeypatch.setattr(watchdog, "is_enabled", lambda *a: True)
    monkeypatch.setattr(watchdog, "is_installed", lambda: True)
    monkeypatch.setattr(watchdog, "take_heartbeat", lambda sid: True)  # loaded
    monkeypatch.setattr(watchdog, "installed_version", lambda: "0.40.3")
    monkeypatch.setattr(watchdog, "cached_latest", lambda: "0.41.0")
    watchdog.cmd_check("s1")
    out = capsys.readouterr().out
    assert "0.40.3" in out and "0.41.0" in out
    assert "installed but not loaded" not in out


def test_drift_consumed_on_read(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(watchdog, "STATE", tmp_path / "state")
    monkeypatch.setattr(watchdog, "is_enabled", lambda *a: True)
    monkeypatch.setattr(watchdog, "is_installed", lambda: True)
    monkeypatch.setattr(watchdog, "take_heartbeat", lambda sid: True)
    monkeypatch.setattr(watchdog, "installed_version", lambda: "0.40.3")
    monkeypatch.setattr(watchdog, "cached_latest", lambda: "0.41.0")
    watchdog.cmd_check("s1")
    capsys.readouterr()
    watchdog.cmd_check("s1")  # same session, second prompt
    assert capsys.readouterr().out == ""


def test_drift_rearms_after_boot(tmp_path, monkeypatch, capsys):
    """--continue reuses session_id; boot clears the marker and re-arms drift."""
    monkeypatch.setattr(watchdog, "STATE", tmp_path / "state")
    monkeypatch.setattr(watchdog, "is_enabled", lambda *a: True)
    monkeypatch.setattr(watchdog, "is_installed", lambda: True)
    monkeypatch.setattr(watchdog, "take_heartbeat", lambda sid: True)
    monkeypatch.setattr(watchdog, "installed_version", lambda: "0.40.3")
    monkeypatch.setattr(watchdog, "cached_latest", lambda: "0.41.0")
    watchdog.cmd_check("s1")
    capsys.readouterr()
    watchdog.cmd_boot("s1")
    watchdog.cmd_check("s1")
    assert "0.41.0" in capsys.readouterr().out


def test_drift_silent_when_no_cache(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(watchdog, "STATE", tmp_path / "state")
    monkeypatch.setattr(watchdog, "is_enabled", lambda *a: True)
    monkeypatch.setattr(watchdog, "is_installed", lambda: True)
    monkeypatch.setattr(watchdog, "take_heartbeat", lambda sid: True)
    monkeypatch.setattr(watchdog, "installed_version", lambda: "0.40.3")
    monkeypatch.setattr(watchdog, "cached_latest", lambda: None)
    watchdog.cmd_check("s1")
    assert capsys.readouterr().out == ""
