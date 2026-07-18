#!/usr/bin/env python3
"""safe_commit — commit ONLY an explicitly declared set of files.

The shave protocol requires every surgeon commit to touch exactly its
transform's files and nothing else. A broad `git add -A` on a working tree
carrying the user's in-flight work once swept 220 files / +85,027 insertions
into a single shave commit (safety-model §6). This helper makes "commit only
these paths" mechanical:

  1. refuse if the index already holds staged changes outside your list;
  2. stage exactly the declared paths (`git add -- <files>`, deletions included);
  3. refuse (and unstage the extras) if anything outside the list got staged;
  4. commit path-limited (`git commit -- <files>`);
  5. verify the resulting commit touched ONLY the declared paths.

Also refuses TYPECHANGES (symlink ↔ regular file) among the declared paths:
editing through a symlink silently replaces the link itself — a field run
converted a tracked CLAUDE.md → AGENTS.md symlink into a plain file this way.
Edit the link's TARGET (readlink <path>), keep the link. When the type change
IS the intended fix (restoring a link), pass --allow-typechange.

Usage:
  safe_commit.py [--allow-typechange] -m "<message>" -- <file> [<file>...]
  safe_commit.py [--allow-typechange] -F <message-file> -- <file> [<file>...]

Exit codes: 0 committed · 1 usage · 2 refused (index / extra path / frozen /
typechange) · 3 nothing to commit · 4 post-commit verification failed.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger  # noqa: E402


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def staged_set():
    return {l for l in git("diff", "--cached", "--name-only").splitlines() if l}


def die(code, msg):
    sys.stderr.write(msg if msg.endswith("\n") else msg + "\n")
    sys.exit(code)


def main():
    argv = sys.argv[1:]
    if "--" not in argv:
        die(1, "usage: safe_commit.py (-m MSG | -F FILE) -- <file>...")
    split = argv.index("--")
    opts, files = argv[:split], [f for f in argv[split + 1:] if f]
    msg, i = None, 0
    while i < len(opts):
        if opts[i] == "-m" and i + 1 < len(opts):
            msg, i = opts[i + 1], i + 2
        elif opts[i] == "-F" and i + 1 < len(opts):
            try:
                msg = open(opts[i + 1], encoding="utf-8").read()
            except OSError as e:
                die(1, f"cannot read message file: {e}")
            i += 2
        else:
            i += 1
    if not files:
        die(1, "refusing: no files declared after --")
    if not msg or not msg.strip():
        die(1, "refusing: empty commit message")

    declared = set(files)
    frozen_hit = sorted(f for f in files if ledger.matches(f, ledger.frozen(".")))
    if frozen_hit:
        die(2, "refusing: these files are FROZEN in the shrinkage ledger and must "
               "never be edited:\n  " + "\n  ".join(frozen_hit) +
               "\n(e.g. hash-sealed subsystems). Drop them from your transform.")
    extras_pre = staged_set() - declared
    if extras_pre:
        die(2, "refusing: the index already has staged changes outside your file "
               "list:\n  " + "\n  ".join(sorted(extras_pre)) +
               "\nA shave commit must stage only its transform's files. Unstage "
               "them first:  git restore --staged <files>")

    git("add", "--", *files)  # stages exactly these (deletions included)
    unexpected = staged_set() - declared
    if unexpected:
        git("reset", "-q", "--", *sorted(unexpected))  # unstage only the strays
        die(2, "refusing: staging your files also pulled in:\n  " +
               "\n  ".join(sorted(unexpected)) +
               "\n(unstaged them). Declare every path you intend to commit.")
    tc = sorted(l.split("\t", 1)[1] for l in
                git("diff", "--cached", "--name-status").splitlines()
                if l.startswith("T"))
    if tc and "--allow-typechange" not in opts:
        git("reset", "-q", "--", *tc)
        die(2, "refusing: these paths CHANGED TYPE (symlink ↔ regular file):\n  "
               + "\n  ".join(tc) +
               "\n(unstaged them). Editing through a symlink replaces the link "
               "itself — edit the link's TARGET (`readlink <path>`) and keep the "
               "link; a shave never converts file types. If the type change IS "
               "the intended fix (e.g. restoring a link), re-run with "
               "--allow-typechange.")
    if not staged_set():
        die(3, "nothing to commit for the declared files (no changes staged).")

    r = subprocess.run(["git", "commit", "-q", "-F", "-", "--", *files],
                       input=msg, capture_output=True, text=True)
    if r.returncode != 0:
        die(2, "git commit failed:\n" + r.stderr)

    landed = {l for l in git("diff-tree", "--no-commit-id", "--name-only", "-r",
                             "HEAD").splitlines() if l}
    extra = landed - declared
    if extra:
        die(4, "VERIFICATION FAILED: commit touched files outside your list:\n  "
               + "\n  ".join(sorted(extra)) +
               "\nInvestigate before continuing (git reset --soft HEAD^ to redo).")
    sha = git("rev-parse", "--short", "HEAD").strip()
    print(f"committed {sha}: {len(landed)} file(s) — {', '.join(sorted(landed))}")


if __name__ == "__main__":
    main()
