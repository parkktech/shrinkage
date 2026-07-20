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
