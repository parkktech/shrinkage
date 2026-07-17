#!/usr/bin/env python3
"""platform — the Composer vendor surface, searchable for the reuse gate (v0.9).

Composer already indexes every vendor class in
vendor/composer/autoload_classmap.php (plus autoload_psr4.php namespace
roots). This module reads that prebuilt index instead of parsing the vendor
tree, so "does the framework already provide this?" costs one lookup even on
a 60k-class Magento install.

CLI (also exposed as `codemap.py vendor <term>`):
  platform.py search <term> [--deep] [--limit N]
  platform.py frameworks
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parsers import parse_text  # noqa: E402

CLASSMAP_ENTRY = re.compile(r"'((?:[^'\\]|\\.)+)'\s*=>\s*\$(\w+)\s*\.\s*'((?:[^'\\]|\\.)+)'")

# composer.json require -> (framework label, rules file stem)
FRAMEWORKS = {
    "laravel/framework": ("laravel", "laravel"),
    "magento/product-community-edition": ("magento2", "magento2"),
    "magento/product-enterprise-edition": ("magento2", "magento2"),
    "magento/framework": ("magento2", "magento2"),
    "drupal/core": ("drupal", "drupal"),
    "drupal/core-recommended": ("drupal", "drupal"),
    "symfony/framework-bundle": ("symfony", "laravel"),  # nearest rules until symfony.md exists
}


def find_root(start="."):
    p = Path(start).resolve()
    for d in (p, *p.parents):
        if (d / "composer.json").exists():
            return d
    return None


def classmap(root):
    """{FQCN: absolute file path} from Composer's generated classmap."""
    cm = root / "vendor" / "composer" / "autoload_classmap.php"
    if not cm.exists():
        return {}
    out = {}
    bases = {"vendorDir": root / "vendor", "baseDir": root}
    for m in CLASSMAP_ENTRY.finditer(cm.read_text(encoding="utf-8", errors="replace")):
        fqcn = m.group(1).replace("\\\\", "\\")
        base = bases.get(m.group(2), root / "vendor")
        out[fqcn] = (base / m.group(3).lstrip("/")).resolve()
    return out


def package_of(path, root):
    try:
        parts = path.relative_to(root / "vendor").parts
        return f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else parts[0]
    except ValueError:
        return "app"


def detect_frameworks(root):
    try:
        req = json.loads((root / "composer.json").read_text(encoding="utf-8"))
        deps = {**req.get("require", {}), **req.get("require-dev", {})}
    except (OSError, ValueError):
        return []
    found = {}
    for dep, (label, rules) in FRAMEWORKS.items():
        if dep in deps:
            found[label] = rules
    return sorted(found.items())


def print_frameworks(root, skill_root=None):
    fws = detect_frameworks(root)
    if not fws:
        return False
    skill_root = skill_root or Path(__file__).resolve().parent.parent
    print("frameworks detected — read the framework rules before implementing:")
    for label, rules in fws:
        print(f"  {label:<10} -> {skill_root / 'rules' / 'frameworks' / (rules + '.md')}")
    print("  platform sweep: `codemap.py vendor <term>` searches the vendor classmap "
          "before you write anything the framework may already provide.")
    return True


def search(root, term, deep=False, limit=25):
    cm = classmap(root)
    if not cm:
        print("no Composer classmap found — run `composer install` (or "
              "`composer dump-autoload -o`) so vendor/composer/autoload_classmap.php exists")
        return
    needle = term.lower()
    hits = [(fq, p) for fq, p in cm.items() if needle in fq.lower()]
    if not hits:
        print(f"no vendor classes matching '{term}' among {len(cm)} indexed — "
              f"try a broader term or a synonym")
        return
    by_pkg = {}
    for fq, p in sorted(hits)[:limit]:
        by_pkg.setdefault(package_of(p, root), []).append((fq, p))
    shown = sum(len(v) for v in by_pkg.values())
    print(f"{len(hits)} vendor classes match '{term}' (showing {shown}):")
    for pkg, entries in sorted(by_pkg.items()):
        print(pkg)
        for fq, p in entries:
            print(f"  {fq}")
            if deep and p.exists():
                for s in parse_text(str(p), p.read_text(encoding="utf-8", errors="replace")):
                    if s.kind == "m":
                        print(f"    m {s.signature}")
    if len(hits) > limit:
        print(f"... {len(hits) - limit} more — narrow the term or raise --limit")
    if not deep:
        print("(--deep parses the matched classes and lists their methods)")


def main():
    args = sys.argv[1:]
    root = find_root()
    if not root:
        sys.exit("no composer.json found upward from cwd")
    if not args or args[0] == "frameworks":
        if not print_frameworks(root):
            print("no known framework in composer.json (searched require/require-dev)")
        return
    if args[0] == "search":
        args = args[1:]
    term = next((a for a in args if not a.startswith("--")), None)
    if not term:
        sys.exit(__doc__)
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 25
    search(root, term, deep="--deep" in args, limit=limit)


if __name__ == "__main__":
    main()
