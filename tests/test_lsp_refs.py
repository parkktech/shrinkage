"""lsp_refs — the reference oracle: framed-protocol client (against a fake
server) and a live pylsp round-trip when the oracle is installed."""
import shutil
import sys
import textwrap

import pytest
from conftest import run

FAKE_SERVER = textwrap.dedent('''
    import json, sys

    def read_msg():
        length = None
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                sys.exit(0)
            if line in (b"\\r\\n", b"\\n"):
                break
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":", 1)[1])
        return json.loads(sys.stdin.buffer.read(length))

    def send(obj):
        data = json.dumps(obj).encode()
        sys.stdout.buffer.write(b"Content-Length: %d\\r\\n\\r\\n" % len(data) + data)
        sys.stdout.buffer.flush()

    mode = sys.argv[1]
    while True:
        msg = read_msg()
        m = msg.get("method")
        if m == "initialize":
            # noise BEFORE the reply: a notification the client must drop and
            # a server->client request it must answer (not stall on)
            send({"jsonrpc": "2.0", "method": "window/logMessage",
                  "params": {"type": 3, "message": "indexing"}})
            send({"jsonrpc": "2.0", "id": 999,
                  "method": "workspace/configuration", "params": {"items": []}})
            send({"jsonrpc": "2.0", "id": msg["id"],
                  "result": {"capabilities": {}}})
        elif m == "textDocument/references":
            uri = msg["params"]["textDocument"]["uri"]
            base = uri.rsplit("/", 1)[0]
            locs = [] if mode == "zero" else [
                {"uri": base + "/caller.py",
                 "range": {"start": {"line": 2, "character": 6},
                           "end": {"line": 2, "character": 13}}},
                {"uri": base + "/caller.py",
                 "range": {"start": {"line": 3, "character": 6},
                           "end": {"line": 3, "character": 13}}}]
            send({"jsonrpc": "2.0", "id": msg["id"], "result": locs})
        elif m == "shutdown":
            send({"jsonrpc": "2.0", "id": msg["id"], "result": None})
        elif m == "exit":
            sys.exit(0)
''')

HELPERS = "def used_fn(x):\n    return x * 2\n\n\ndef unused_fn(y):\n    return y + 1\n"
CALLER = "from helpers import used_fn\n\nprint(used_fn(3))\nprint(used_fn(4))\n"


def _arm_fake(repo, monkeypatch, mode):
    fake = repo / "fake_lsp.py"
    fake.write_text(FAKE_SERVER)
    (repo / "helpers.py").write_text(HELPERS)
    (repo / "caller.py").write_text(CALLER)
    monkeypatch.setenv("SRK_LSP_CMD_PYTHON",
                       f"{sys.executable} {fake} {mode}")


def test_fake_oracle_kills_false_x0(repo, monkeypatch):
    """Refs found -> candidate killed, exit 1, locations listed — and the
    client survived interleaved notifications + a server->client request."""
    _arm_fake(repo, monkeypatch, "refs")
    code, out = run("lsp_refs.py", "check", "helpers.py", "used_fn", cwd=repo)
    assert code == 1
    assert "KILLED" in out and "caller.py:3" in out and "caller.py:4" in out
    assert "1 killed" in out


def test_fake_oracle_confirms_x0(repo, monkeypatch):
    _arm_fake(repo, monkeypatch, "zero")
    code, out = run("lsp_refs.py", "check", "helpers.py", "unused_fn", cwd=repo)
    assert code == 0
    assert "oracle-confirmed x0" in out
    assert "checklist still required" in out
    # confirmed is explicitly NOT a delete license
    assert "≠ safe-to-delete" in out


def test_no_oracle_is_loud_not_silent(repo, monkeypatch):
    (repo / "helpers.py").write_text(HELPERS)
    monkeypatch.delenv("SRK_LSP_CMD_PYTHON", raising=False)
    empty = repo / "emptybin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    code, out = run("lsp_refs.py", "check", "helpers.py", "unused_fn", cwd=repo)
    assert code == 2
    assert "pip install python-lsp-server" in out
    assert "UNVERIFIED" in out


def test_symbol_not_in_file_refuses(repo, monkeypatch):
    _arm_fake(repo, monkeypatch, "zero")
    code, out = run("lsp_refs.py", "check", "helpers.py", "ghost_fn", cwd=repo)
    assert code == 2
    assert "not found" in out and "DEFINES" in out


def test_servers_reports_both_states(repo, monkeypatch):
    monkeypatch.delenv("SRK_LSP_CMD_PYTHON", raising=False)
    empty = repo / "emptybin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    code, out = run("lsp_refs.py", "servers", cwd=repo)
    assert code == 0
    assert "not installed" in out and "intelephense" in out


def _fake_npm(path, target_bin, mode="ok", prefix="/nonexistent"):
    """A stand-in npm: `install` drops a fake `intelephense` into target_bin
    (unless mode='fail'); `prefix -g` reports prefix (for the off-PATH probe)."""
    path.write_text(
        f"#!{sys.executable}\n"
        "import sys\nfrom pathlib import Path\n"
        "a = sys.argv[1:]\n"
        f"if a[:2] == ['prefix', '-g']:\n    print({str(prefix)!r})\n"
        "    raise SystemExit(0)\n"
        "if a and a[0] == 'install':\n"
        f"    if {mode!r} == 'eacces':\n"
        "        sys.stderr.write('npm ERR! code EACCES\\n"
        "npm ERR! Error: EACCES: permission denied, mkdir "
        "/usr/lib/node_modules\\n'); raise SystemExit(1)\n"
        f"    if {mode!r} == 'fail':\n"
        "        sys.stderr.write('npm ERR! simulated\\n'); raise SystemExit(1)\n"
        f"    b = Path({str(target_bin)!r}); b.mkdir(parents=True, exist_ok=True)\n"
        "    e = b / 'intelephense'; e.write_text('#!/bin/sh\\necho i\\n')\n"
        "    e.chmod(0o755)\n"
        "raise SystemExit(0)\n")
    path.chmod(0o755)


def test_install_dry_run_shows_command_never_runs(repo, monkeypatch):
    empty = repo / "bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))          # no npm anywhere
    monkeypatch.delenv("SRK_LSP_CMD_PHP", raising=False)
    code, out = run("lsp_refs.py", "install", "php", "--dry-run", cwd=repo)
    assert code == 0
    assert "would run" in out and "npm install -g intelephense" in out
    assert "not on PATH" in out                     # honest about the gap
    assert not (empty / "intelephense").exists()    # nothing was installed


def test_install_already_present_skips(repo, monkeypatch):
    monkeypatch.setenv("SRK_LSP_CMD_PHP", "echo stub")
    code, out = run("lsp_refs.py", "install", "php", cwd=repo)
    assert code == 0 and "already installed" in out


def test_install_no_prereq_is_honest(repo, monkeypatch):
    empty = repo / "bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.delenv("SRK_LSP_CMD_PHP", raising=False)
    code, out = run("lsp_refs.py", "install", "php", cwd=repo)
    assert code == 1
    assert "can't auto-install" in out and "npm" in out


def test_install_runs_then_verifies_on_path(repo, monkeypatch):
    """End-to-end: prereq present → run it → server now on PATH → ✓."""
    binpath = repo / "bin"
    binpath.mkdir()
    _fake_npm(binpath / "npm", target_bin=binpath)   # installs onto PATH
    monkeypatch.setenv("PATH", str(binpath))
    monkeypatch.delenv("SRK_LSP_CMD_PHP", raising=False)
    code, out = run("lsp_refs.py", "install", "php", cwd=repo)
    assert code == 0
    assert "installed" in out and "intelephense" in out
    assert (binpath / "intelephense").exists()


def test_install_off_path_is_flagged_not_claimed(repo, monkeypatch):
    """Installed but landed off-PATH → ⚠, counted as a failure, never ✓."""
    binpath = repo / "bin"
    binpath.mkdir()
    prefix = repo / "npmprefix"                       # NOT on PATH
    _fake_npm(binpath / "npm", target_bin=prefix / "bin", prefix=str(prefix))
    monkeypatch.setenv("PATH", str(binpath))
    monkeypatch.delenv("SRK_LSP_CMD_PHP", raising=False)
    code, out = run("lsp_refs.py", "install", "php", cwd=repo)
    assert code == 1
    assert "NOT on your PATH" in out
    assert (prefix / "bin" / "intelephense").exists()  # it did install…
    # …but the oracle invokes by name, so this is a warning, not success


def test_install_permission_wall_points_to_admin(repo, monkeypatch):
    """EACCES → 'no-admin fix, or send this to your admin' — not a raw trace."""
    binpath = repo / "bin"
    binpath.mkdir()
    _fake_npm(binpath / "npm", target_bin=binpath, mode="eacces")
    monkeypatch.setenv("PATH", str(binpath))
    monkeypatch.delenv("SRK_LSP_CMD_PHP", raising=False)
    code, out = run("lsp_refs.py", "install", "php", cwd=repo)
    assert code == 1
    assert "PERMISSION" in out
    assert "server admin" in out
    assert "npm install -g intelephense" in out        # the exact command to forward
    assert "npm config set prefix" in out              # the no-admin escape hatch


def test_install_continues_to_next_language_after_failure(repo, monkeypatch):
    """One language failing must not abort the others — the loop moves on."""
    binpath = repo / "bin"
    binpath.mkdir()
    _fake_npm(binpath / "npm", target_bin=binpath, mode="eacces")  # php via npm fails
    monkeypatch.setenv("PATH", str(binpath))                       # go: no `go` on PATH
    for v in ("SRK_LSP_CMD_PHP", "SRK_LSP_CMD_GO"):
        monkeypatch.delenv(v, raising=False)
    code, out = run("lsp_refs.py", "install", "php", "go", cwd=repo)
    assert code == 1
    assert "php" in out and "PERMISSION" in out          # php: admin-wall reported
    assert "go" in out and "can't auto-install" in out   # go: reached and handled
    assert out.index("php") < out.index("go")            # processed in order, both


def test_install_failure_surfaces_error(repo, monkeypatch):
    binpath = repo / "bin"
    binpath.mkdir()
    _fake_npm(binpath / "npm", target_bin=binpath, mode="fail")
    monkeypatch.setenv("PATH", str(binpath))
    monkeypatch.delenv("SRK_LSP_CMD_PHP", raising=False)
    code, out = run("lsp_refs.py", "install", "php", cwd=repo)
    assert code == 1
    assert "still isn't found" in out
    assert not (binpath / "intelephense").exists()


@pytest.mark.skipif(shutil.which("pylsp") is None,
                    reason="pylsp not installed — live-oracle test")
def test_live_pylsp_round_trip(repo, monkeypatch):
    """The real oracle: a referenced fn is killed, an unreferenced one
    confirmed, in one batch over one server session."""
    monkeypatch.delenv("SRK_LSP_CMD_PYTHON", raising=False)
    (repo / "helpers.py").write_text(HELPERS)
    (repo / "caller.py").write_text(CALLER)
    code, out = run("lsp_refs.py", "check",
                    "helpers.py", "used_fn", "helpers.py", "unused_fn",
                    cwd=repo)
    assert code == 1                       # used_fn killed dominates
    assert "used_fn" in out and "KILLED" in out
    assert "unused_fn (helpers.py) — oracle-confirmed x0" in out
    assert "1 killed" in out and "1 oracle-confirmed" in out
