"""Detects the "installed but not loaded" state and reports it in-conversation.

A hook inside the plugin cannot detect the plugin failing to load, so this
script lives at a stable path outside the plugin cache and is registered in
~/.claude/settings.json. The plugin's SessionStart hook writes a heartbeat;
absence of that heartbeat at first prompt means the plugin did not load.

Every entry point fails open: a diagnostic must never block a prompt.
"""

import json
import os
from pathlib import Path

WARNING = (
    "[shrinkage] installed but not loaded in this session.\n"
    "Try /reload-plugins first. If commands are still missing, quit and\n"
    "relaunch claude — without --continue or --resume."
)

HOME = Path.home()
ROOT = HOME / ".claude" / "shrinkage"
STATE = ROOT / "state"
STABLE = ROOT / "watchdog.py"
USER_SETTINGS = HOME / ".claude" / "settings.json"
PLUGIN_KEY_PREFIX = "shrinkage@"


def decide(enabled, installed, heartbeat):
    """healthy | warn | uninstall — a pure function of the three observations."""
    if not enabled or not installed:
        return "uninstall"
    return "healthy" if heartbeat else "warn"


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
    try:
        (STATE / "hb" / session_id).unlink()
        return True
    except OSError:
        return False


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
        os.replace(str(tmp), str(p))
        return True
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        return False


def backup_once(path):
    """Keep one pristine copy of the settings as we first found them.

    Written only if absent, so a later run can never overwrite the pristine
    copy with an already-modified one."""
    p = Path(path)
    bak = p.with_suffix(".json.srk-bak")
    if bak.exists() or not p.exists():
        return
    try:
        bak.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        pass


def _ours(entry):
    return any(MARKER in (h.get("command") or "") for h in (entry.get("hooks") or []))


def add_hooks(path, python, script):
    """Register both watchdog hooks. Idempotent; preserves everything else."""
    if looks_malformed(path):
        return False
    backup_once(path)
    data = read_json(path) if Path(path).exists() else {}
    hooks = data.setdefault("hooks", {})
    for event in EVENTS:
        arg = "boot" if event == "SessionStart" else "check"
        entries = [e for e in hooks.get(event, []) if not _ours(e)]
        entries.append({"hooks": [{
            "type": "command",
            "command": '"{}" "{}" {}'.format(python, script, arg),
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
