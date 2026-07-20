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
