#!/usr/bin/env python3
"""dirty_apply — safely shave a target whose file already carries the user's
uncommitted work, when the two changes are DISJOINT (advanced, opt-in).

Default shave policy is to SKIP dirty targets (safety-model / shave workflow).
`--allow-dirty-disjoint` uses this two-phase helper so the user's in-flight hunk
is never entangled with the shave commit and never lost:

  park <file>    save the user's HEAD-relative changes to a patch + full backup,
                 then reset the file to HEAD so the surgeon edits a clean base.
  unpark <file>  after the shave is committed (via safe_commit.py), re-apply the
                 saved user hunk on top. Clean apply → disjoint, done. Conflict →
                 NOT disjoint: restore the exact backup and exit non-zero (the
                 surgeon must revert the shave commit — this target stays blocked).

Nothing is destructive: a failed unpark restores the byte-exact pre-shave file.
Exit: 0 ok · 2 refused/precondition · 3 not-disjoint (backup restored).
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def store_dir():
    d = git("rev-parse", "--git-dir").stdout.strip() or ".git"
    p = Path(d) / "srk-dirty"
    p.mkdir(parents=True, exist_ok=True)
    return p


def slot(path):
    h = hashlib.sha1(path.encode()).hexdigest()[:16]
    d = store_dir()
    return d / f"{h}.patch", d / f"{h}.bak"


def die(code, msg):
    sys.stderr.write(msg.rstrip("\n") + "\n")
    sys.exit(code)


def park(path):
    tracked = git("ls-files", "--error-unmatch", "--", path).returncode == 0
    if not tracked:
        die(2, f"{path} is not tracked — dirty-disjoint only applies to a tracked "
               "file carrying uncommitted edits.")
    diff = git("diff", "HEAD", "--", path).stdout
    if not diff:
        die(2, f"{path} has no uncommitted changes vs HEAD — nothing to park "
               "(shave it normally).")
    patch, bak = slot(path)
    patch.write_text(diff, encoding="utf-8")
    bak.write_bytes(Path(path).read_bytes())
    r = git("checkout", "HEAD", "--", path)
    if r.returncode != 0:
        die(2, "could not reset the file to HEAD:\n" + r.stderr)
    print(f"parked {path}: user hunk saved, file reset to HEAD (edit the clean base, "
          "safe_commit it, then `dirty_apply.py unpark`).")


def unpark(path):
    patch, bak = slot(path)
    if not patch.exists() or not bak.exists():
        die(2, f"no parked state for {path} (run `park` first).")
    # Re-apply the user's hunk onto the (now shaved + committed) working file.
    r = git("apply", "--recount", str(patch))
    if r.returncode == 0:
        patch.unlink(missing_ok=True)
        bak.unlink(missing_ok=True)
        print(f"unparked {path}: user's in-flight hunk re-applied on top of the shave.")
        return
    # Not disjoint — restore the byte-exact pre-shave file, leave a signal.
    Path(path).write_bytes(bak.read_bytes())
    patch.unlink(missing_ok=True)
    bak.unlink(missing_ok=True)
    die(3, f"NOT DISJOINT: the user's hunk overlaps the shave region in {path}. "
           "Restored your exact pre-shave file. Revert the shave commit "
           "(git reset --soft HEAD^ && git restore --staged .) — this target "
           "stays blocked on the user's uncommitted work.")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("park", "unpark"):
        die(2, "usage: dirty_apply.py {park|unpark} <file>")
    (park if sys.argv[1] == "park" else unpark)(sys.argv[2])


if __name__ == "__main__":
    main()
