"""Detects the "installed but not loaded" state and reports it in-conversation.

A hook inside the plugin cannot detect the plugin failing to load, so this
script lives at a stable path outside the plugin cache and is registered in
~/.claude/settings.json. The plugin's SessionStart hook writes a heartbeat;
absence of that heartbeat at first prompt means the plugin did not load.

Every entry point fails open: a diagnostic must never block a prompt.
"""

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

WARNING = (
    "[shrinkage] installed but not loaded in this session.\n"
    "Try /reload-plugins first. If commands are still missing, quit and\n"
    "relaunch claude — without --continue or --resume."
)

DRIFT = "[shrinkage] running v{installed} · v{latest} released. /srk:update for the steps."

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


def semver(s):
    """(major, minor, patch) or None. Re-derived rather than imported from
    statusline.py for the same reason as NOT_LOADED_FLAG: the two files ship
    and update independently, so an import would couple them."""
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)$", (s or "").strip())
    return tuple(int(g) for g in m.groups()) if m else None


def decide_drift(installed, latest):
    """drift | healthy — pure function of two version strings.

    Silent under every uncertainty: an unknown version on either side, an
    unparseable one, or a local build ahead of the newest tag. Only a
    confidently-behind install is worth interrupting a prompt for."""
    inst, new = semver(installed), semver(latest)
    if not inst or not new:
        return "healthy"
    return "drift" if new > inst else "healthy"


def update_cache_path():
    p = os.environ.get("SRK_UPDATE_CACHE")
    return Path(p) if p else HOME / ".claude" / "shrinkage-update.json"


def cached_latest():
    """The newest released version as last resolved by statusline.py's worker,
    or None. Read-only: the watchdog never calls the network and never writes
    this cache — exactly one component owns the remote call."""
    return read_json(update_cache_path()).get("latest") or None


def installed_version():
    """Version of the installed copy, from the plugin registry. The watchdog
    lives outside the plugin cache, so it cannot derive this from its own path
    the way statusline.py does; it reads the same installPath is_installed()
    validates. Prefers plugin.json (the source of truth per RELEASING.md) and
    falls back to the version the registry recorded at install."""
    data = read_json(HOME / ".claude" / "plugins" / "installed_plugins.json")
    for key, entries in (data.get("plugins") or {}).items():
        if not key.startswith(PLUGIN_KEY_PREFIX):
            continue
        for entry in entries or []:
            path = entry.get("installPath")
            if not path or not Path(path).is_dir():
                continue
            version = read_json(Path(path) / ".claude-plugin" / "plugin.json").get("version")
            return version or entry.get("version") or None
    return None


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


def cmd_heartbeat(sid):
    """Proof-of-life that the plugin loaded this session."""
    try:
        hb = STATE / "hb"
        hb.mkdir(parents=True, exist_ok=True)
        (hb / sid).write_text("", encoding="utf-8")
        cutoff = time.time() - 86400
        for old in hb.iterdir():
            if old.stat().st_mtime < cutoff:
                old.unlink()
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
    if verdict == "warn":
        # A plugin that did not load outranks a plugin that is merely behind:
        # reporting both in one prompt is noise, and /reload-plugins comes
        # first anyway. Drift is reported only from an otherwise-healthy state.
        return 0
    installed = installed_version()
    latest = cached_latest()
    if decide_drift(installed, latest) == "drift":
        print(DRIFT.format(installed=installed, latest=latest))
    return 0


def cmd_plant():
    """Copy this script to the stable path and register both hooks."""
    try:
        STABLE.parent.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).resolve()
        if source != Path(os.path.abspath(str(STABLE))):
            shutil.copyfile(str(source), str(STABLE))
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
    if cmd == "heartbeat":
        return cmd_heartbeat(sid)
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
