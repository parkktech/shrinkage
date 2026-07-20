# Install Watchdog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When Shrinkage is installed but not loaded in a session, tell the user so in the conversation, with `/reload-plugins` as the first remedy.

**Architecture:** The plugin's SessionStart hook writes a consume-on-read heartbeat. A watchdog script — copied to a stable path outside the versioned plugin cache and registered in `~/.claude/settings.json` on both `SessionStart` and `UserPromptSubmit` — sees a session with no heartbeat and reports the plugin failed to load. Both watchdog hooks live outside plugin registration, so they fire whether or not the plugin loads.

**Tech Stack:** Python 3 stdlib only. pytest for tests. Claude Code hooks (`hooks.json`, `~/.claude/settings.json`).

**Spec:** `docs/superpowers/specs/2026-07-20-install-watchdog-design.md`

## Global Constraints

- **Stdlib only.** No third-party imports in `watchdog.py`. It runs before anything is guaranteed installed.
- **Fail open, always.** Any error — missing python, malformed JSON, unreadable path — must exit 0 silently. A diagnostic must never block a prompt.
- **Latency budget <50ms.** `UserPromptSubmit` runs on every prompt. A handful of `stat`/`read` calls, no subprocesses, no network.
- **Settings writes are atomic and merge-preserving.** Temp file + `os.replace`. Never drop unknown keys. Another tool may own `statusLine` (GSD does in the reporting environment) and must survive untouched.
- **Stable path only.** Never reference `~/.claude/plugins/cache/<mp>/shrinkage/<version>/` from user settings — it changes every release. The watchdog is copied to `~/.claude/shrinkage/watchdog.py`.
- **Warning copy, verbatim:**
  ```
  [shrinkage] installed but not loaded in this session.
  Try /reload-plugins first. If commands are still missing, quit and
  relaunch claude — without --continue or --resume.
  ```

## File Structure

| File | Responsibility |
|---|---|
| Create: `skills/shrinkage/scripts/watchdog.py` | Everything watchdog: pure decision logic, settings scope reading, the `plant`/`boot`/`check` subcommands, self-uninstall. One file because the planter must ship *inside* the copied artifact — splitting it would mean copying two files and keeping their versions in sync. |
| Create: `tests/test_watchdog.py` | Unit tests over fixture trees. |
| Modify: `hooks.json` | SessionStart gains heartbeat write + planter invocation. |
| Modify: `skills/shrinkage/scripts/statusline.py:189` (`srk_segment`) | Ambient `⚠ srk not loaded` badge. |
| Modify: `README.md`, `CHANGELOG.md` | Document the behavior. |

---

### Task 1: Pure decision logic

**Files:**
- Create: `skills/shrinkage/scripts/watchdog.py`
- Test: `tests/test_watchdog.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `decide(enabled: bool, installed: bool, heartbeat: bool) -> str` returning one of `"healthy"`, `"warn"`, `"uninstall"`. Tasks 2 and 4 call this.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_watchdog.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/src/shrinkage && python -m pytest tests/test_watchdog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'watchdog'`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/shrinkage/scripts/watchdog.py
"""Detects the "installed but not loaded" state and reports it in-conversation.

A hook inside the plugin cannot detect the plugin failing to load, so this
script lives at a stable path outside the plugin cache and is registered in
~/.claude/settings.json. The plugin's SessionStart hook writes a heartbeat;
absence of that heartbeat at first prompt means the plugin did not load.

Every entry point fails open: a diagnostic must never block a prompt.
"""

WARNING = (
    "[shrinkage] installed but not loaded in this session.\n"
    "Try /reload-plugins first. If commands are still missing, quit and\n"
    "relaunch claude — without --continue or --resume."
)


def decide(enabled, installed, heartbeat):
    """healthy | warn | uninstall — a pure function of the three observations."""
    if not enabled or not installed:
        return "uninstall"
    return "healthy" if heartbeat else "warn"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/src/shrinkage && python -m pytest tests/test_watchdog.py -v`
Expected: PASS — 4 passed

- [ ] **Step 5: Commit**

```bash
cd ~/src/shrinkage
git add skills/shrinkage/scripts/watchdog.py tests/test_watchdog.py
git commit -m "feat(watchdog): pure decision logic for installed-but-not-loaded"
```

---

### Task 2: Observation helpers — settings scopes, install presence, heartbeat

**Files:**
- Modify: `skills/shrinkage/scripts/watchdog.py`
- Test: `tests/test_watchdog.py`

**Interfaces:**
- Consumes: `decide()` from Task 1.
- Produces:
  - `STATE = Path.home() / ".claude" / "shrinkage" / "state"`
  - `STABLE = Path.home() / ".claude" / "shrinkage" / "watchdog.py"`
  - `USER_SETTINGS = Path.home() / ".claude" / "settings.json"`
  - `read_json(path) -> dict` — `{}` on any failure
  - `is_enabled(scopes: list[Path]) -> bool`
  - `is_installed() -> bool`
  - `take_heartbeat(session_id: str) -> bool` — consume-on-read

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_watchdog.py
import json


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/src/shrinkage && python -m pytest tests/test_watchdog.py -v`
Expected: FAIL — `AttributeError: module 'watchdog' has no attribute 'read_json'`

- [ ] **Step 3: Write minimal implementation**

Add to `skills/shrinkage/scripts/watchdog.py`, below `WARNING`:

```python
import json
import os
from pathlib import Path

HOME = Path.home()
ROOT = HOME / ".claude" / "shrinkage"
STATE = ROOT / "state"
STABLE = ROOT / "watchdog.py"
USER_SETTINGS = HOME / ".claude" / "settings.json"
PLUGIN_KEY_PREFIX = "shrinkage@"


def read_json(path):
    """Parsed JSON, or {} for missing/unreadable/malformed. Never raises."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return {}


def settings_scopes(cwd=None):
    """Every settings file Claude Code merges, narrowest last."""
    cwd = Path(cwd or Path.cwd())
    return [USER_SETTINGS,
            cwd / ".claude" / "settings.json",
            cwd / ".claude" / "settings.local.json"]


def is_enabled(scopes):
    """True when any scope enables a shrinkage@<marketplace> plugin."""
    for path in scopes:
        for key, on in (read_json(path).get("enabledPlugins") or {}).items():
            if key.startswith(PLUGIN_KEY_PREFIX):
                return bool(on)
    return False


def is_installed():
    """True when a shrinkage entry in installed_plugins.json points at a real dir."""
    data = read_json(HOME / ".claude" / "plugins" / "installed_plugins.json")
    for key, entries in (data.get("plugins") or {}).items():
        if not key.startswith(PLUGIN_KEY_PREFIX):
            continue
        for entry in entries or []:
            path = entry.get("installPath")
            if path and Path(path).is_dir():
                return True
    return False


def take_heartbeat(session_id):
    """True if this session has a heartbeat — and consume it.

    Consume-on-read keeps the check time-independent: no freshness window to
    tune, and no false alarm when a session idles for hours before its first
    prompt."""
    hb = STATE / "hb" / session_id
    try:
        hb.unlink()
        return True
    except OSError:
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/src/shrinkage && python -m pytest tests/test_watchdog.py -v`
Expected: PASS — 10 passed

- [ ] **Step 5: Commit**

```bash
cd ~/src/shrinkage
git add skills/shrinkage/scripts/watchdog.py tests/test_watchdog.py
git commit -m "feat(watchdog): settings-scope, install and heartbeat observations"
```

---

### Task 3: Atomic merge-preserving settings writer

**Files:**
- Modify: `skills/shrinkage/scripts/watchdog.py`
- Test: `tests/test_watchdog.py`

**Interfaces:**
- Consumes: `read_json`, `USER_SETTINGS` from Task 2.
- Produces:
  - `write_settings(path, data) -> bool` — atomic, `False` on failure
  - `hook_entry(event: str) -> dict` — the hook block this tool owns
  - `add_hooks(path, python: str, script: str) -> bool`
  - `remove_hooks(path) -> bool`
  - Ownership marker: an entry is ours iff its `command` string contains `shrinkage/watchdog.py`.

This is the one genuinely invasive component. It gets the heaviest tests.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_watchdog.py
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
    assert "UserPromptSubmit" not in out["hooks"] or out["hooks"]["UserPromptSubmit"] == []


def test_add_hooks_refuses_malformed_settings(tmp_path):
    s = tmp_path / "settings.json"
    s.write_text("{ this is not json", encoding="utf-8")

    assert watchdog.add_hooks(s, "/usr/bin/python3", "/x/watchdog.py") is False
    assert s.read_text(encoding="utf-8") == "{ this is not json"  # untouched
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/src/shrinkage && python -m pytest tests/test_watchdog.py -v`
Expected: FAIL — `AttributeError: module 'watchdog' has no attribute 'add_hooks'`

- [ ] **Step 3: Write minimal implementation**

Add to `skills/shrinkage/scripts/watchdog.py`:

```python
MARKER = "shrinkage/watchdog.py"
EVENTS = ("SessionStart", "UserPromptSubmit")


def looks_malformed(path):
    """True when the file exists with content but does not parse — never
    overwrite a file we failed to understand."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return True
    return bool(text.strip()) and read_json(p) == {} and text.strip() not in ("{}", "null")


def write_settings(path, data):
    """Atomic temp+replace. False on any failure; the original stays intact."""
    p = Path(path)
    tmp = p.with_suffix(".json.srk-tmp")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, p)
        return True
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        return False


def _ours(entry):
    return any(MARKER in (h.get("command") or "") for h in (entry.get("hooks") or []))


def add_hooks(path, python, script):
    """Register both watchdog hooks. Idempotent; preserves everything else."""
    if looks_malformed(path):
        return False
    data = read_json(path)
    if not Path(path).exists():
        data = {}
    hooks = data.setdefault("hooks", {})
    for event in EVENTS:
        arg = "boot" if event == "SessionStart" else "check"
        entries = [e for e in hooks.get(event, []) if not _ours(e)]
        entries.append({"hooks": [{
            "type": "command",
            "command": f'"{python}" "{script}" {arg}',
        }]})
        hooks[event] = entries
    return write_settings(path, data)


def remove_hooks(path):
    """Drop only our entries — another tool's hooks on the same event stay."""
    if looks_malformed(path):
        return False
    data = read_json(path)
    hooks = data.get("hooks") or {}
    changed = False
    for event in EVENTS:
        if event not in hooks:
            continue
        kept = [e for e in hooks[event] if not _ours(e)]
        if len(kept) != len(hooks[event]):
            changed = True
        hooks[event] = kept
    if not changed:
        return True
    return write_settings(path, data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/src/shrinkage && python -m pytest tests/test_watchdog.py -v`
Expected: PASS — 15 passed

- [ ] **Step 5: Commit**

```bash
cd ~/src/shrinkage
git add skills/shrinkage/scripts/watchdog.py tests/test_watchdog.py
git commit -m "feat(watchdog): atomic merge-preserving settings hook writer"
```

---

### Task 4: Subcommands — `plant`, `boot`, `check`

**Files:**
- Modify: `skills/shrinkage/scripts/watchdog.py`
- Test: `tests/test_watchdog.py`

**Interfaces:**
- Consumes: everything from Tasks 1-3.
- Produces: `main(argv, stdin_text) -> int`. Subcommands:
  - `plant` — copy self to `STABLE`, register hooks. Run from the plugin's SessionStart.
  - `boot` — clear this session's `checked` marker. Required because `--continue` reuses `session_id` (measured on 2.1.215).
  - `check` — the actual check; prints `WARNING` to stdout when warranted.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_watchdog.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/src/shrinkage && python -m pytest tests/test_watchdog.py -v`
Expected: FAIL — `AttributeError: module 'watchdog' has no attribute 'main'`

- [ ] **Step 3: Write minimal implementation**

Add to `skills/shrinkage/scripts/watchdog.py`:

```python
import shutil
import sys


def session_id(stdin_text):
    """Claude Code pipes session JSON on stdin. '' when unreadable."""
    try:
        return (json.loads(stdin_text) or {}).get("session_id") or ""
    except (TypeError, ValueError):
        return ""


def _checked(sid):
    return STATE / "checked" / sid


def cmd_boot(sid):
    """Clear the once-per-session marker. Fires on every process start,
    including --continue, which reuses session_id."""
    try:
        _checked(sid).unlink()
    except OSError:
        pass
    return 0


def cmd_check(sid):
    marker = _checked(sid)
    if marker.exists():
        return 0
    verdict = decide(is_enabled(settings_scopes()), is_installed(), take_heartbeat(sid))
    if verdict == "uninstall":
        remove_hooks(USER_SETTINGS)
        return 0
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("", encoding="utf-8")
    except OSError:
        pass
    if verdict == "warn":
        print(WARNING)
    return 0


def cmd_plant():
    """Copy this script to the stable path and register both hooks."""
    try:
        STABLE.parent.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).resolve()
        if source != STABLE.resolve(strict=False):
            shutil.copyfile(source, STABLE)
    except OSError:
        return 0
    add_hooks(USER_SETTINGS, sys.executable, str(STABLE))
    return 0


def main(argv, stdin_text):
    cmd = argv[0] if argv else "check"
    sid = session_id(stdin_text)
    if cmd == "plant":
        return cmd_plant()
    if not sid:
        return 0
    if cmd == "boot":
        return cmd_boot(sid)
    return cmd_check(sid)


if __name__ == "__main__":
    try:
        raw = "" if sys.stdin.isatty() else sys.stdin.read()
    except OSError:
        raw = ""
    try:
        sys.exit(main(sys.argv[1:], raw))
    except Exception:
        sys.exit(0)  # fail open: never block a prompt
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/src/shrinkage && python -m pytest tests/test_watchdog.py -v`
Expected: PASS — 22 passed

- [ ] **Step 5: Commit**

```bash
cd ~/src/shrinkage
git add skills/shrinkage/scripts/watchdog.py tests/test_watchdog.py
git commit -m "feat(watchdog): plant/boot/check subcommands with once-per-boot gating"
```

---

### Task 5: Wire the plugin hooks — heartbeat + planter

**Files:**
- Modify: `hooks.json` (the `SessionStart` block)
- Test: `tests/test_watchdog.py`

**Interfaces:**
- Consumes: `watchdog.py plant` from Task 4.
- Produces: `~/.claude/shrinkage/state/hb/<session_id>` written on every loaded session.

The heartbeat must be written by shell, not Python, so it lands even if the planter fails. `$CLAUDE_SESSION_ID` is not guaranteed; the heartbeat is written by a tiny Python one-liner reading the same stdin JSON the hook receives.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_watchdog.py
from pathlib import Path as _P


def test_hooks_json_writes_heartbeat_and_plants():
    hooks = json.loads((_P(__file__).resolve().parent.parent / "hooks.json")
                       .read_text(encoding="utf-8"))
    commands = " ".join(h["command"]
                        for block in hooks["hooks"]["SessionStart"]
                        for h in block["hooks"])
    assert "watchdog.py" in commands
    assert "plant" in commands
    assert "heartbeat" in commands
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/src/shrinkage && python -m pytest tests/test_watchdog.py::test_hooks_json_writes_heartbeat_and_plants -v`
Expected: FAIL — `AssertionError` (no watchdog reference in SessionStart)

- [ ] **Step 3: Write minimal implementation**

Add a `heartbeat` subcommand to `watchdog.py` — it needs the same stdin JSON, so it belongs in the same script:

```python
def cmd_heartbeat(sid):
    """Proof-of-life that the plugin loaded this session."""
    try:
        hb = STATE / "hb"
        hb.mkdir(parents=True, exist_ok=True)
        (hb / sid).write_text("", encoding="utf-8")
        cutoff = __import__("time").time() - 86400
        for old in hb.iterdir():
            if old.stat().st_mtime < cutoff:
                old.unlink()
    except OSError:
        pass
    return 0
```

Wire it into `main()`, immediately after the `boot` branch:

```python
    if cmd == "heartbeat":
        return cmd_heartbeat(sid)
```

Then in `hooks.json`, append one hook object to the existing `SessionStart` block's `hooks` array (leave the codemap/statusline hook untouched):

```json
{
  "type": "command",
  "command": "PY=$(command -v python3 || command -v python); [ -n \"$PY\" ] && { \"$PY\" \"${CLAUDE_PLUGIN_ROOT}/skills/shrinkage/scripts/watchdog.py\" heartbeat; \"$PY\" \"${CLAUDE_PLUGIN_ROOT}/skills/shrinkage/scripts/watchdog.py\" plant; }; true"
}
```

Note: `plant` receives no stdin here — it does not need a session id.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/src/shrinkage && python -m pytest tests/test_watchdog.py -v`
Expected: PASS — 23 passed

Then verify the hook JSON is still valid:

Run: `cd ~/src/shrinkage && python -c "import json;json.load(open('hooks.json'));print('hooks.json OK')"`
Expected: `hooks.json OK`

- [ ] **Step 5: Commit**

```bash
cd ~/src/shrinkage
git add hooks.json skills/shrinkage/scripts/watchdog.py tests/test_watchdog.py
git commit -m "feat(watchdog): heartbeat + planter on plugin SessionStart"
```

---

### Task 6: Statusline badge

**Files:**
- Modify: `skills/shrinkage/scripts/statusline.py:189` (`srk_segment`)
- Test: `tests/test_watchdog.py`

**Interfaces:**
- Consumes: nothing from the watchdog module — `statusline.py` must not import it, because the statusline runs when the plugin is loaded and the import would be a hard dependency between two independently-copied files. It re-derives the one fact it needs from the filesystem.
- Produces: `⚠ srk not loaded` prefix on the segment.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_watchdog.py
import statusline


def test_segment_flags_not_loaded(tmp_path, monkeypatch):
    monkeypatch.setattr(statusline, "NOT_LOADED_FLAG", tmp_path / "flag")
    (tmp_path / "flag").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert statusline.srk_segment().startswith("⚠ srk not loaded")


def test_segment_normal_when_no_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(statusline, "NOT_LOADED_FLAG", tmp_path / "flag")
    monkeypatch.chdir(tmp_path)
    assert not statusline.srk_segment().startswith("⚠")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/src/shrinkage && python -m pytest tests/test_watchdog.py -k segment -v`
Expected: FAIL — `AttributeError: module 'statusline' has no attribute 'NOT_LOADED_FLAG'`

- [ ] **Step 3: Write minimal implementation**

In `statusline.py`, add near the other module constants:

```python
NOT_LOADED_FLAG = Path.home() / ".claude" / "shrinkage" / "state" / "not-loaded"
```

And at the top of `srk_segment()` (currently line 193, before the `log = ...` line):

```python
    try:
        if NOT_LOADED_FLAG.exists():
            return "⚠ srk not loaded — /reload-plugins"
    except OSError:
        pass
```

Then have `cmd_check` in `watchdog.py` maintain that flag — replace its `if verdict == "warn":` tail with:

```python
    flag = STATE / "not-loaded"
    try:
        if verdict == "warn":
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.write_text("", encoding="utf-8")
            print(WARNING)
        else:
            flag.unlink()
    except OSError:
        pass
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/src/shrinkage && python -m pytest tests/ -v`
Expected: PASS — full suite green, 25 passed in test_watchdog.py

- [ ] **Step 5: Commit**

```bash
cd ~/src/shrinkage
git add skills/shrinkage/scripts/statusline.py skills/shrinkage/scripts/watchdog.py tests/test_watchdog.py
git commit -m "feat(watchdog): ambient not-loaded badge on the status line"
```

---

### Task 7: Documentation

**Files:**
- Modify: `README.md` (the "Get started" section, after the install block)
- Modify: `CHANGELOG.md` (new entry at top)

**Interfaces:**
- Consumes: behavior from Tasks 1-6.
- Produces: no code.

- [ ] **Step 1: Add the README note**

Insert after the `/plugin install shrinkage@parkktech` fenced block in "Get started":

```markdown
**If `/srk` shows no commands after installing:** the plugin is on disk but the
running session hasn't registered it. Run `/reload-plugins` — that fixes it
without losing your session. If commands are still missing, quit and relaunch
`claude` **without** `--continue` or `--resume`.

From your first loaded session onward Shrinkage detects this state on its own
and tells you, so you shouldn't need this note twice.
```

- [ ] **Step 2: Add the CHANGELOG entry**

Insert at the top of `CHANGELOG.md`:

```markdown
## Unreleased
- **Installed-but-not-loaded now announces itself.** A correct install could
  still leave `/srk` empty when the running session hadn't registered the
  plugin — and nothing said so, to the user or to Claude, who would report the
  install as healthy. A watchdog at a stable path outside the plugin cache
  (`~/.claude/shrinkage/watchdog.py`), registered on `SessionStart` and
  `UserPromptSubmit`, now reports the state in-conversation and recommends
  `/reload-plugins` before a relaunch. It self-uninstalls when Shrinkage is
  removed. Hooks inside the plugin can't catch this — they don't run when the
  plugin doesn't load.
- Measured on Claude Code 2.1.215: `--continue` reuses `session_id` and
  `SessionStart` still fires, which is why the watchdog re-arms per boot rather
  than trusting a session-keyed marker.
```

- [ ] **Step 3: Verify the suite is still green**

Run: `cd ~/src/shrinkage && python -m pytest tests/ -q`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
cd ~/src/shrinkage
git add README.md CHANGELOG.md
git commit -m "docs: document the installed-but-not-loaded watchdog"
```

---

## Manual verification (after Task 7)

Automated tests cover the decision logic; these two confirm the wiring against a live Claude Code.

- [ ] **End-to-end healthy path:** open a fresh session in any repo, send a prompt. Expect no `[shrinkage]` warning and `~/.claude/shrinkage/state/hb/<id>` consumed.
- [ ] **End-to-end warn path:** with Claude Code closed, temporarily rename `~/.claude/plugins/cache/parkktech/` aside, reopen, send a prompt. Expect the warning. Restore the directory afterwards.
