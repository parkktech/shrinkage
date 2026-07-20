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
