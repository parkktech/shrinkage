#!/usr/bin/env python3
"""codemap — token-lean symbol map of a repo, with language auto-detection.

Commands:
  build   [--root DIR] [--out FILE] [--budget N] [--sync-intel]
  refresh [same flags]      rebuild only if sources are newer than the map
  query TERM [--deep]       grep the map; --deep re-parses matching files
  langs                     detected languages + which rules/<lang>.md to read
  scope DIR [--budget N]    deeper map for one subtree (monorepos)

GSD integration: when .planning/ exists (a GSD project), the map defaults to
.planning/intel/codemap.txt and `build`/`refresh` also sync symbol entries
into .planning/intel/api-map.json so GSD intel consumers (plan_review
source grounding, API-SURFACE.md) see every language this skill parses.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import settings  # noqa: E402
from parsers import EXTENSIONS, Symbol, is_ref_only, language_of, parse_file  # noqa: E402

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "out", "__pycache__",
    ".venv", "venv", ".planning", ".claude", ".agents", "coverage", ".next",
    ".nuxt", "target", "bower_components", ".idea", ".vscode",
}
MAX_FILE_BYTES = 1_000_000
IDENT = re.compile(r"\w{3,}")


def est_tokens(text):
    return len(text) // 4


COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.S)
COMMENT_LINE = re.compile(r"(//|#).*")


def strip_comments(text):
    """Remove comments before identifier counting so commented-out code doesn't
    inflate reference counts (a symbol mentioned only in comments is not alive)."""
    text = COMMENT_BLOCK.sub(" ", text)
    return "\n".join(COMMENT_LINE.sub(" ", l) for l in text.splitlines())


def fingerprint(root):
    """Content fingerprint of the source set: catches edits, ADDS, and DELETES
    (pure mtime comparison misses deletions and git checkouts to older refs)."""
    h = hashlib.sha1()
    for p in source_files(root):
        st = p.stat()
        h.update(f"{p.relative_to(root).as_posix()}:{st.st_size}:{st.st_mtime_ns}|".encode())
    return h.hexdigest()[:12]


def map_path(root):
    if (root / ".planning").is_dir():
        return root / ".planning" / "intel" / "codemap.txt"
    return root / ".claude" / "codemap.txt"


def source_files(root):
    for p in sorted(root.rglob("*")):
        if not p.is_file() or language_of(p.name) is None:
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield p


def ref_only_files(root):
    """Templates/config that reference code without defining it (parsers.is_ref_only)."""
    for p in sorted(root.rglob("*")):
        if not p.is_file() or not is_ref_only(p):
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield p


def build_index(root):
    """{relpath: [Symbol]} with reference counts filled in."""
    index, idents, defs = {}, Counter(), Counter()
    for path in source_files(root):
        rel = path.relative_to(root).as_posix()
        index[rel] = parse_file(path)
        try:
            idents.update(IDENT.findall(strip_comments(
                path.read_text(encoding="utf-8", errors="replace"))))
        except OSError:
            pass
    for path in ref_only_files(root):  # refs only — no symbols, no comment strip
        try:
            idents.update(IDENT.findall(path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            pass
    for syms in index.values():
        for s in syms:
            defs[s.name] += 1
    for syms in index.values():
        for s in syms:
            s.refs = max(0, idents[s.name] - defs[s.name])  # minus ALL definitions
    return index


def format_symbol(s):
    tag = f"@{s.line}"
    refs = f" x{s.refs}" if s.refs else ""
    if s.kind in ("c", "i"):
        base = f" : {s.base}" if s.base else ""
        return f"  {s.kind} {s.name}{base}  {tag}{refs}"
    indent = "    " if s.parent else "  "
    return f"{indent}{s.kind} {s.signature}  {tag}{refs}"


def format_map(index, root, budget):
    def render(collapsed):
        lines = []
        for rel in sorted(index):
            syms = index[rel]
            if not syms:
                continue
            lines.append(rel if rel not in collapsed else f"{rel}  (+{len(syms)} symbols, collapsed)")
            if rel not in collapsed:
                lines.extend(format_symbol(s) for s in syms)
        return "\n".join(lines)

    collapsed, body = set(), render(set())
    if budget:
        # Collapse lowest-signal files (by their best symbol's ref count) until under budget.
        by_signal = sorted((rel for rel in index if index[rel]),
                           key=lambda r: max(s.refs for s in index[r]))
        i = 0
        while est_tokens(body) > budget and i < len(by_signal):
            collapsed.add(by_signal[i])
            i += 1
            body = render(collapsed)
    n_syms = sum(len(v) for v in index.values())
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    header = (f"# codemap v1 | root: {root.name} | generated: {stamp} | "
              f"files: {len(index)} | symbols: {n_syms} | ~{est_tokens(body)} tokens"
              f" | fp: {fingerprint(root)}"
              + (f" | {len(collapsed)} files collapsed to fit budget {budget}" if collapsed else ""))
    return header + "\n" + body + "\n"


def detected_languages(index):
    counts = Counter()
    for rel, syms in index.items():
        lang = language_of(rel)
        if lang and syms:
            counts[lang] += 1
    return counts


def print_langs(index):
    skill_root = Path(__file__).resolve().parent.parent
    counts = detected_languages(index)
    if not counts:
        print("no supported languages detected")
        return
    print("languages detected — read the matching rules before implementing:")
    for lang, n in counts.most_common():
        print(f"  {lang:<12} {n:>4} files  -> {skill_root / 'rules' / (lang + '.md')}")


def sync_intel(index, root):
    intel_dir = root / ".planning" / "intel"
    intel_dir.mkdir(parents=True, exist_ok=True)
    api_path = intel_dir / "api-map.json"
    try:
        data = json.loads(api_path.read_text(encoding="utf-8")) if api_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        data = {}
    ours = {}
    for rel, syms in index.items():
        for s in syms:
            key = f"{s.parent}.{s.name}" if s.parent else s.name
            if key in ours:
                key = f"{key} ({rel})"
            ours[key] = {"file": rel, "kind": s.kind, "signature": s.signature,
                         "line": s.line, "refs": s.refs,
                         "language": language_of(rel), "src": "srk"}
    # Merge, don't clobber: keep entries other tools (e.g. GSD's intel-updater)
    # wrote; replace only entries we generated previously.
    old = data.get("entries") or {}
    entries = {k: v for k, v in old.items()
               if not (isinstance(v, dict) and v.get("src") == "srk")}
    entries.update(ours)
    data["entries"] = entries
    meta = data.get("_meta") or {}
    meta.update({"updated_at": datetime.now(timezone.utc).isoformat(),
                 "version": meta.get("version", 1),
                 "generator": "shrinkage/codemap.py"})
    data["_meta"] = meta
    api_path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return api_path


def ensure_ignored(root, out):
    """Keep the map out of git unless the user opted to commit it."""
    if not (root / ".git").exists():
        return
    try:
        rel = out.relative_to(root).as_posix()
    except ValueError:
        return
    gi = root / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    if rel not in lines:
        gi.write_text("\n".join(lines + [rel]) + "\n", encoding="utf-8")
        print(f"added {rel} to .gitignore (set commit_map=true in "
              f".claude/shrinkage.json to commit it instead)")


def cmd_build(root, out, budget, do_sync):
    index = build_index(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(format_map(index, root, budget), encoding="utf-8")
    print(f"map written: {out}")
    q = settings.quip(root, "build", n=sum(len(v) for v in index.values()))
    if q:
        print(q)
    if not settings.load(root)["commit_map"]:
        ensure_ignored(root, out)
    if do_sync or (root / ".planning").is_dir():
        print(f"gsd intel synced: {sync_intel(index, root)}")
    print_langs(index)
    if (root / "composer.json").exists():
        import platformmap as srk_platform
        srk_platform.print_frameworks(root)
    if any((root / m).exists() for m in ("build.gradle", "build.gradle.kts", "settings.gradle",
                                         "settings.gradle.kts", "app/src/main/AndroidManifest.xml")):
        skill_root = Path(__file__).resolve().parent.parent
        print("frameworks detected — read the framework rules before implementing:")
        print(f"  android    -> {skill_root / 'rules' / 'frameworks' / 'android.md'}")
        print("  platform sweep: check your modules, then Jetpack/androidx, before writing "
              "a manager/scheduler/cache by hand.")


def cmd_refresh(root, out, budget, do_sync):
    if out.exists():
        m = re.search(r"\| fp: (\w+)", out.read_text(encoding="utf-8").splitlines()[0])
        if m and m.group(1) == fingerprint(root):
            print(f"codemap up to date: {out}")
            q = settings.quip(root, "current")
            if q:
                print(q)
            return
    cmd_build(root, out, budget, do_sync)


def cmd_auto(root, out, budget, do_sync):
    """SessionStart hook — MUST be fast on large repos (60k+ files). Prints the
    status line from the cached map header instantly and builds only when the
    map is ABSENT (first time). Real staleness refresh happens at task time
    (core loop step 1), never on every session start. Silence with
    `"quiet_startup": true`."""
    if not out.exists():
        index = build_index(root)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(format_map(index, root, budget), encoding="utf-8")
        if not settings.load(root)["commit_map"]:
            ensure_ignored(root, out)
        if do_sync or (root / ".planning").is_dir():
            sync_intel(index, root)
        header = out.read_text(encoding="utf-8").splitlines()[0]
        verb = "codemap built"
    else:
        lines = out.read_text(encoding="utf-8").splitlines()
        header, verb = (lines[0] if lines else ""), "active"
    if settings.load(root).get("quiet_startup"):
        return
    n_m = re.search(r"symbols: (\d+)", header)
    n = int(n_m.group(1)) if n_m else 0
    map_fp_m = re.search(r"\| fp: (\w+)", header)
    map_fp = map_fp_m.group(1) if map_fp_m else ""
    print(f"[shrinkage] {verb} · {n:,} symbols · {_audit_tail(root, map_fp)}")


def _audit_tail(root, map_fp):
    """Audit-state hint for the startup line — cheap: reads only SHRINK-PLAN.md,
    compares its stamped map-fp to the current MAP's fp (no file-tree walk)."""
    plan = root / ".planning" / "SHRINK-PLAN.md"
    if not plan.exists():
        plan = root / "SHRINK-PLAN.md"
    if not plan.exists():
        return "no audit yet — run /srk:audit to find safe reductions"
    try:
        text = plan.read_text(encoding="utf-8")
    except OSError:
        return "run /srk:audit to refresh SHRINK-PLAN.md"
    planned = re.search(r"map-fp:\s*(\w+)", text)
    stale = " (stale — /srk:audit to refresh)" if (planned and map_fp and planned.group(1) != map_fp) else ""
    open_text = re.split(r"^#+\s+Done\b", text, maxsplit=1, flags=re.I | re.M)[0]
    open_items = _open_plan_items(text)
    if not open_items:
        return "SHRINK-PLAN.md clean — /srk:audit to rescan"
    # Tier mix and headline savings — from OPEN rows only (exclude the Done section).
    tiers = re.findall(r"\|\s*\d+\s*\|[^\n]*?\bT([0-3])\b", open_text)
    tier_bits = ""
    if tiers:
        from collections import Counter as _C
        c = _C(tiers)
        tier_bits = " · " + " ".join(f"T{t}×{c[t]}" for t in sorted(c))
    est = re.search(r"est-savings:\s*-?(\d+)", text)
    savings = f" · ~{est.group(1)} LOC to reclaim" if est else ""
    return (f"SHRINK-PLAN.md: {open_items} open{tier_bits}{savings}{stale} — "
            f"/srk:shave 1 to start")


def _open_plan_items(text):
    """Count unchecked candidate rows in a SHRINK-PLAN.md (best-effort).
    Ranked rows start with `| <number> |`; struck (`~~`) or Done rows don't count."""
    out, done = 0, False
    for l in text.splitlines():
        if re.match(r"^#+\s+Done\b", l, re.I):
            done = True
        if not done and re.match(r"\|\s*\d+\s*\|", l) and "~~" not in l:
            out += 1
    return out


SKIP_NAMES = {"__init__", "__str__", "__repr__", "constructor", "main", "index",
              "render", "setup", "handle", "toString", "run", "get", "set"}


def cmd_dupes(root):
    """Same-named callables in multiple places — C1/C9 consolidation leads."""
    index = build_index(root)
    by_name = {}
    for rel, syms in index.items():
        for s in syms:
            if s.kind in ("f", "m") and s.name not in SKIP_NAMES:
                by_name.setdefault(s.name, []).append((rel, s))
    groups = {n: hits for n, hits in by_name.items() if len(hits) > 1}
    if not groups:
        print("no duplicate-name symbols found — suspiciously tidy, or nicely shrunk")
        return
    print(f"{len(groups)} duplicate-name groups (consolidation catalog: C1/C9 leads):")
    for name, hits in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"\n{name}  ({len(hits)} definitions)")
        for rel, s in hits:
            owner = f"{s.parent}." if s.parent else ""
            print(f"  {rel}:{s.line}  {owner}{s.signature}")
    print("\nverify with source before consolidating — same name is a lead, not proof.")


NORM = re.compile(r"\b\w+\b")
WINDOW = 6  # lines per shingle window


def cmd_clones(root, min_lines=6):
    """Renamed copy-paste detector: normalized line-window hashing (C9 leads).

    Identifiers are replaced with a placeholder before hashing, so a block
    survives being copy-pasted-and-renamed. Windows that match across (or
    within) files merge into maximal duplicate block reports.
    """
    windows = {}  # hash -> [(rel, start_line)]
    texts = {}
    for path in source_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        norm = [NORM.sub("_", l.strip()) for l in lines]
        texts[rel] = lines
        for i in range(len(norm) - WINDOW + 1):
            body = [l for l in norm[i:i + WINDOW]]
            if sum(len(l) > 2 for l in body) < WINDOW - 1:  # skip blank/brace runs
                continue
            windows.setdefault("\n".join(body), []).append((rel, i + 1))
    groups = [locs for locs in windows.values() if len({l[0:1] + (l[1] // WINDOW,) for l in locs}) > 1 or len(locs) > 1]
    # merge overlapping windows into maximal blocks per location pair
    pairs = {}
    for locs in groups:
        for a in range(len(locs)):
            for b in range(a + 1, len(locs)):
                key = (locs[a][0], locs[b][0])
                pairs.setdefault(key, set()).add((locs[a][1], locs[b][1]))
    found = 0
    for (fa, fb), starts in sorted(pairs.items()):
        runs, current = [], None
        for sa, sb in sorted(starts):
            if current and sa == current[1] + 1 and sb == current[3] + 1:
                current = (current[0], sa, current[2], sb)
            else:
                if current:
                    runs.append(current)
                current = (sa, sa, sb, sb)
        if current:
            runs.append(current)
        for (a0, a1, b0, b1) in runs:
            length = a1 - a0 + WINDOW
            if length < min_lines or (fa == fb and a0 == b0):
                continue
            found += 1
            print(f"clone ~{length} lines: {fa}:{a0}-{a0+length-1} <-> {fb}:{b0}-{b0+length-1}")
            snippet = texts[fa][a0 - 1].strip()
            print(f"  starts: {snippet[:90]}")
    if not found:
        print("no structural clones found — either disciplined, or already shaved")
    else:
        print(f"\n{found} clone blocks — C9 candidates; verify divergence line-by-line before merging.")


def cmd_query(root, out, term, deep):
    if not out.exists():
        sys.exit(f"no map at {out} — run: codemap.py build")
    needle, current, hits = term.lower(), None, []
    for line in out.read_text(encoding="utf-8").splitlines()[1:]:
        if line and not line.startswith(" "):
            current = line
        elif needle in line.lower():
            hits.append((current, line))
    if not hits:
        print(f"no symbols matching '{term}' — consider `query` with a broader term, or --deep")
        return
    # Anti context-rot: a broad term on a big repo can match thousands of lines.
    # Cap the dump; tell the user to narrow rather than flooding the window.
    CAP = 60
    total = len(hits)
    last = None
    for group, line in hits[:CAP]:
        if group != last:
            print(group)
            last = group
        print(line)
    if total > CAP:
        print(f"... {total - CAP} more matches — narrow the term (currently '{term}')")
    if deep:
        for rel in dict.fromkeys(g.split("  ")[0] for g, _ in hits):
            print(f"\n{rel} (deep):")
            for s in parse_file(root / rel):
                print(format_symbol(s))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["build", "refresh", "query", "langs", "scope", "dupes", "clones", "vendor"])
    ap.add_argument("arg", nargs="?", help="query term / scope dir")
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    ap.add_argument("--out", help="map file (default: auto — GSD intel dir if .planning/ exists)")
    ap.add_argument("--budget", type=int, default=None,
                    help="token budget for the map (default: settings file, else 4000)")
    ap.add_argument("--sync-intel", action="store_true", help="force GSD api-map.json sync")
    ap.add_argument("--deep", action="store_true", help="query: re-parse matching files for full detail")
    ap.add_argument("--quiet", action="store_true", help="suppress output (for editor hooks)")
    ap.add_argument("--auto", action="store_true",
                    help="hook mode: exit silently when this isn't a code project "
                         "(no supported source files or no .git)")
    a = ap.parse_args()
    if a.quiet:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")

    root = Path(a.root).resolve()
    out = Path(a.out).resolve() if a.out else map_path(root)
    if a.auto and (not (root / ".git").exists() or next(source_files(root), None) is None):
        return  # not a code project — hooks must never spam unrelated dirs
    if a.budget is None:
        a.budget = settings.load(root)["budget"]

    if a.command == "build":
        cmd_build(root, out, a.budget, a.sync_intel)
    elif a.command == "refresh":
        if a.auto:
            cmd_auto(root, out, a.budget, a.sync_intel)  # default-on active line
        else:
            cmd_refresh(root, out, a.budget, a.sync_intel)
    elif a.command == "query":
        if not a.arg:
            sys.exit("usage: codemap.py query <term> [--deep]")
        cmd_query(root, out, a.arg, a.deep)
    elif a.command == "langs":
        print_langs(build_index(root))
    elif a.command == "dupes":
        cmd_dupes(root)
    elif a.command == "clones":
        cmd_clones(root)
    elif a.command == "vendor":
        import platformmap as srk_platform
        if not a.arg:
            sys.exit("usage: codemap.py vendor <term> [--deep]")
        proot = srk_platform.find_root(root)
        if not proot:
            sys.exit("no composer.json found — vendor search is for Composer projects")
        srk_platform.search(proot, a.arg, deep=a.deep)
    elif a.command == "scope":
        if not a.arg:
            sys.exit("usage: codemap.py scope <dir> [--budget N]")
        sub = (root / a.arg).resolve()
        cmd_build(sub, sub / ".codemap-scope.txt", a.budget, False)


if __name__ == "__main__":
    main()
