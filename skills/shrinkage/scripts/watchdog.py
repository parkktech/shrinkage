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
