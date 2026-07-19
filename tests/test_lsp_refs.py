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
