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
    b.write_text(json.dumps({"enabledPlugins": {"shrinkage@parkktech": True}}), encoding="utf-8")
    assert watchdog.is_enabled([a, b]) is True
    assert watchdog.is_enabled([a]) is False


def test_is_enabled_false_when_explicitly_disabled(tmp_path):
    a = tmp_path / "a.json"
    a.write_text(json.dumps({"enabledPlugins": {"shrinkage@parkktech": False}}), encoding="utf-8")
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
        "enabledPlugins": {"shrinkage@parkktech": True},
    }), encoding="utf-8")

    watchdog.add_hooks(s, "/usr/bin/python3", "/home/u/.claude/shrinkage/watchdog.py")

    out = json.loads(s.read_text(encoding="utf-8"))
    assert out["statusLine"] == {"type": "command", "command": "gsd-statusline.js"}
    assert out["enabledPlugins"] == {"shrinkage@parkktech": True}
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
