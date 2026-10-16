#!/usr/bin/env python3
"""organize — class naming and code organization, checked on every new file (on by default,
`"organize": false` to opt out).

Rules:
- **Area first.** Once a repo has a domain root (`app/Domains`, `src/Domain(s)`, `app/Modules`,
  `modules`, or `"domain_root"` in .claude/shrinkage.json), new code goes in `<root>/<Area>/…`, never
  in the framework's base directories (Laravel: app/Models, app/Services, app/Jobs, …).
- **Say what it does.** No catch-all names: `*Manager`, `*Helper(s)`, `*Util(s)`, `*Misc`,
  `*Common`, `*Stuff` (extend with `"banned_names"`).
- **Header.** When `"require_header"` is set (e.g. "@copyright 2026 Acme Inc."), every new
  source file must contain it in its first 40 lines.

    organize.py check <path>...   report violations (exit 1 if any)
    organize.py hook              PostToolUse(Write) mode: feed violations back to the agent
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
from parsers import language_of  # noqa: E402

DOMAIN_ROOTS = ("app/Domains", "src/Domains", "src/Domain", "app/Modules", "modules")
BANNED = ("Manager", "Helper", "Helpers", "Util", "Utils", "Misc", "Common", "Stuff")
# Laravel base dirs that hold framework glue only once a domain root exists.
LARAVEL_GLUE = ("app/Models", "app/Services", "app/Jobs", "app/Events", "app/Listeners",
                "app/Policies", "app/Actions", "app/Enums", "app/Mail", "app/Notifications",
                "app/Filament", "app/Livewire", "app/Http/Controllers", "app/Http/Requests",
                "app/Http/Resources", "app/Console/Commands", "app/Rules", "app/Observers")
GLUE_ALLOWED = {"app/Http/Controllers/Controller.php"}
NON_SOURCE_PARTS = {"vendor", "node_modules", "storage", "bootstrap", "public", "config"}


def domain_root(root, cfg):
    if cfg.get("domain_root"):
        return cfg["domain_root"].rstrip("/")
    return next((d for d in DOMAIN_ROOTS if (Path(root) / d).is_dir()), None)


def violations(root, rel, cfg=None):
    cfg = cfg or settings.load(root)
    if not cfg.get("organize", True):
        return []
    rel = rel.replace("\\", "/")
    parts = rel.split("/")
    name = parts[-1]
    if language_of(name) is None or any(p in NON_SOURCE_PARTS for p in parts[:-1]):
        return []
    out = []
    stem = name.split(".")[0]
    for word in tuple(cfg.get("banned_names") or ()) + BANNED:
        if stem.endswith(word):
            out.append(f"{rel}: `{stem}` is a catch-all name — name it for what it does "
                       f"(verb-noun for actions, the concept for models), not `*{word}`.")
            break
    droot = domain_root(root, cfg)
    if droot and rel not in GLUE_ALLOWED and (Path(root) / "artisan").exists():
        for glue in LARAVEL_GLUE:
            if rel.startswith(glue + "/"):
                out.append(f"{rel}: custom code belongs in {droot}/<Area>/… (mirroring "
                           f"{glue[len('app/'):]}), not Laravel's base `{glue}/`.")
                break
    marker = cfg.get("require_header")
    if marker:
        try:
            head = "\n".join((Path(root) / rel).read_text(encoding="utf-8",
                                                           errors="replace").splitlines()[:40])
        except OSError:
            head = marker
        if marker not in head:
            out.append(f"{rel}: missing the project header (`{marker}`).")
    return out


def hook():
    try:
        data = json.load(sys.stdin)
        path = (data.get("tool_input") or {}).get("file_path", "")
    except Exception:
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        rel = os.path.relpath(path, root)
        if rel.startswith(".."):
            return 0
        found = violations(root, rel)
    except Exception:
        return 0
    if not found:
        return 0
    sys.stderr.write("[shrinkage] organization:\n  - " + "\n  - ".join(found)
                     + "\nFix it now (move/rename and update references) unless the user approved.\n")
    return 2


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "hook":
        return hook()
    if not argv or argv[0] != "check":
        print(__doc__)
        return 2
    root = os.getcwd()
    found = [v for p in argv[1:] for v in violations(root, p)]
    for v in found:
        print(v)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
