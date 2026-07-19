"""User settings for the shrinkage skill.

Stored at .claude/shrinkage.json in the target repo; every field is
optional and these defaults apply when the file is absent or partial.
"""
import json
import random
from pathlib import Path

DEFAULTS = {
    "gate": "soft",          # soft: new files/modules need a stated justification.
                             # hard: additionally confirm with the user first.
    "commit_map": False,     # False: keep the codemap out of git (auto-gitignored).
    "pr_scoreboard": False,  # True: diffstat also emits a markdown block for PR descriptions.
    "budget": 4000,          # codemap token budget.
    "humor": True,           # False: the tools deliver their news with a straight face.
    "quiet_startup": False,  # True: no session-start [shrinkage] active line.
    "auto_max_items": 0,     # /srk:shave --auto: optional review cap (0 = run to completion).
    "auto_context_stop": 75, # fallback only: --auto offloads each item to a subagent so the
                             # main context stays flat; this % is the safety net if it doesn't.
    "allow_dangerous": True, # team kill-switch: False refuses `/srk:shave --auto --dangerous`.
    "oracle_autoinstall": False,  # True: onboard installs missing LSP oracles for the repo's
                                  # main languages WITHOUT asking (still only in interactive
                                  # sessions — never a background npm i -g on a scheduled run).
}

QUIPS = {
    "build": [
        "Map built — {n} symbols catalogued. That's the 'before' photo.",
        "{n} symbols on the board. The duplicates have nowhere to hide now.",
        "Map built. You now have zero excuses for writing a second UserHelper.",
    ],
    "current": [
        "Map's already current — the codebase didn't grow while you weren't looking. Suspicious, but welcome.",
        "Nothing to rebuild. Still fits into last sprint's jeans.",
    ],
    "shrunk": [
        "Net-negative diff. Shrinkage achieved — and before you ask: yes, we were in the pool.",
        "The feature landed and the codebase got SMALLER. Frame this diff.",
        "Less code, same goal. Tell the sprint review who did this.",
    ],
    "flat": [
        "Net zero. Perfectly balanced, as all refactors should be.",
    ],
    "grew": [
        "+{net} lines. Easy there, grower — did every one of those survive the reuse gate?",
        "The codebase grew by {net} lines. Growth is allowed; unjustified growth is just swelling.",
    ],
}


def quip(root, kind, **fmt):
    """One light line for the occasion — empty string when humor is off."""
    if not load(root)["humor"]:
        return ""
    return random.choice(QUIPS[kind]).format(**fmt)


def load(root):
    path = Path(root) / ".claude" / "shrinkage.json"
    try:
        return {**DEFAULTS, **json.loads(path.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return dict(DEFAULTS)
