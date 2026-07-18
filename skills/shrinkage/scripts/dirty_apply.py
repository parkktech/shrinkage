#!/usr/bin/env python3
"""dirty_apply — safely shave a target whose file already carries the user's
uncommitted work, when the two changes are DISJOINT (advanced, opt-in).

Default shave policy is to SKIP dirty targets (safety-model / shave workflow).
`--allow-dirty-disjoint` uses this two-phase helper so the user's in-flight hunk
is never entangled with the shave commit and never lost:

  park <file>      save the user's HEAD-relative changes to a patch + full backup,
                   then reset the file to HEAD so the surgeon edits a clean base.
  precheck <file>  after the surgeon edits but BEFORE the commit: dry-run the
                   unpark merge on the shaved-but-uncommitted file. Would conflict
                   → restore the user's file and abort with NO commit made, so a
                   not-disjoint target never leaves a committed shave to hand-
                   revert (the failure mode that hit QuantDiscoverService). Clean
                   → undo the test, leaving the shave-only file ready to commit.
  unpark <file>    after the shave is committed (via safe_commit.py), re-apply the
                   saved user hunk on top. Clean apply → disjoint, done. Conflict →
                   NOT disjoint: restore the exact backup and exit non-zero (the
                   surgeon must revert the shave commit — this target stays blocked).

Verify disjointness against your ACTUAL edit, not the plan's region — `precheck`
tests the real edit shape (an import-block edit can collide even when the plan's
target region was disjoint). Nothing is destructive: a failed precheck/unpark
restores the byte-exact pre-shave file.
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


def precheck(path):
    """Pre-flight the unpark BEFORE any commit exists. Run the exact 3-way merge
    unpark would run, on the surgeon's shaved-but-uncommitted file; a conflict
    means the edit is NOT disjoint after all — restore the user's pre-shave file
    and abort so no committed shave is left behind to hand-revert. On success,
    undo the test so the pending commit stays shave-only (the real unpark
    re-applies the hunk after safe_commit)."""
    patch, bak = slot(path)
    if not patch.exists() or not bak.exists():
        die(2, f"no parked state for {path} (run `park` first).")
    p = Path(path)
    shaved = p.read_bytes()                     # the surgeon's edit, not yet committed
    # `git apply --3way` merges against the index and refuses if the working tree
    # doesn't match it — so stage the shave first, run the merge, then unwind below.
    git("add", "--", path)
    r = git("apply", "--3way", "--recount", str(patch))
    git("reset", "-q", "--", path)              # index back to HEAD, clearing merge residue
    if r.returncode == 0:
        p.write_bytes(shaved)                   # undo the test merge — commit stays shave-only
        print(f"precheck OK: parked hunk merges cleanly on the shave in {path}.")
        return
    # Would conflict — and no commit exists yet, so just restore the user's file.
    p.write_bytes(bak.read_bytes())
    patch.unlink(missing_ok=True)
    bak.unlink(missing_ok=True)
    die(3, f"NOT DISJOINT (pre-flight): the parked hunk conflicts with the shave edit in "
           f"{path}. Restored your pre-shave file; NO shave commit was made. Skip this target — "
           "it stays blocked on your uncommitted work. (Disjointness is a property of your "
           "ACTUAL edit, not the plan's target region.)")


def unpark(path):
    patch, bak = slot(path)
    if not patch.exists() or not bak.exists():
        die(2, f"no parked state for {path} (run `park` first).")
    # Re-apply the user's hunk with a real 3-way merge (against the base blob the
    # patch was cut from), NOT fragile context matching. This is the fix for the
    # false "NOT DISJOINT": a genuinely disjoint hunk must re-apply even when the
    # shave deleted lines that fell inside the hunk's few lines of diff *context*
    # — plain `git apply` refused exactly that (the common case this tool exists
    # for), while a real overlap still conflicts and is caught below.
    r = git("apply", "--3way", "--recount", str(patch))
    if r.returncode == 0:
        # Keep the restored WIP an UNSTAGED working-tree change (never let it slip
        # into the next commit); --3way can leave the merged path staged.
        git("reset", "-q", "--", path)
        patch.unlink(missing_ok=True)
        bak.unlink(missing_ok=True)
        print(f"unparked {path}: user's in-flight hunk re-applied on top of the shave.")
        return
    # Not disjoint — clear the unmerged index entry --3way leaves on conflict,
    # restore the byte-exact pre-shave file, and signal.
    git("reset", "-q", "--", path)
    Path(path).write_bytes(bak.read_bytes())
    patch.unlink(missing_ok=True)
    bak.unlink(missing_ok=True)
    die(3, f"NOT DISJOINT: the user's hunk overlaps the shave region in {path}. "
           "Restored your exact pre-shave file. Revert the shave commit "
           "(git reset --soft HEAD^ && git restore --staged .) — this target "
           "stays blocked on the user's uncommitted work.")


def main():
    ops = {"park": park, "precheck": precheck, "unpark": unpark}
    if len(sys.argv) != 3 or sys.argv[1] not in ops:
        die(2, "usage: dirty_apply.py {park|precheck|unpark} <file>")
    ops[sys.argv[1]](sys.argv[2])


if __name__ == "__main__":
    main()
