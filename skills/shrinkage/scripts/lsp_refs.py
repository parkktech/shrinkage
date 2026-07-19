#!/usr/bin/env python3
"""lsp_refs — the reference oracle. Asks a real language server the audit's
exact question: "is this x0 actually unreferenced?" via textDocument/references.

  check <file> <symbol> [<file> <symbol> ...]   verify map-x0 candidates
  servers                                       which oracles are installed
  install [lang ...] [--dry-run]                install missing oracle(s) via
                                                the ecosystem's package manager

`install` is EXPLICIT — it runs a package manager, so it never fires from
passive detection (`servers`/`check`); the agent or onboarding invokes it
directly, and onboarding asks first. Bare `install` does every missing
language; `install php python` scopes it. Each language tries its real
package manager (npm/pipx/pip/go/rustup), gated on that tool existing, then
re-checks that the server actually landed on PATH — a package that installed
off-PATH is reported as such, never as a false success.

Verdict semantics (asymmetric on purpose):
- oracle finds references  -> the x0 was a false positive. Candidate KILLED
  instantly — no checklist walk needed to keep it. Exit 1.
- oracle finds zero        -> "oracle-confirmed x0". Stronger than the map,
  but LSP can't see dynamic dispatch, DI containers, config strings, or
  reflection — the dynamic-reference checklist stays MANDATORY. Exit 0.
- no oracle installed      -> loud message with the install hint; the map
  stays a hint and the checklist carries the full load. Exit 2.

One server process per language is spawned and reused across the whole batch;
rootUri is the git toplevel (falls back to cwd) so workspace-wide search works.
Env override for testing/pinning: SRK_LSP_CMD_<LANG>="cmd args..." replaces
the registry lookup for that language.
"""
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parsers import language_of, parser_for  # noqa: E402

# language -> ordered candidates: (argv, install hint)
SERVERS = {
    "python": [(["pylsp"], "pip install python-lsp-server"),
               (["pyright-langserver", "--stdio"], "npm i -g pyright")],
    "javascript": [(["typescript-language-server", "--stdio"],
                    "npm i -g typescript typescript-language-server")],
    "php": [(["intelephense", "--stdio"], "npm i -g intelephense")],
    "go": [(["gopls"], "go install golang.org/x/tools/gopls@latest")],
    "rust": [(["rust-analyzer"], "rustup component add rust-analyzer")],
}

# language -> ordered install candidates: (prereq tool, argv). First candidate
# whose prereq tool exists wins. HARDCODED — install never runs a user string.
INSTALL = {
    "php": [("npm", ["npm", "install", "-g", "intelephense"])],
    "javascript": [("npm", ["npm", "install", "-g", "typescript",
                            "typescript-language-server"])],
    "python": [("pipx", ["pipx", "install", "python-lsp-server"]),
               ("pip3", ["pip3", "install", "--user", "python-lsp-server"]),
               ("pip", ["pip", "install", "--user", "python-lsp-server"])],
    "go": [("go", ["go", "install",
                  "golang.org/x/tools/gopls@latest"])],
    "rust": [("rustup", ["rustup", "component", "add", "rust-analyzer"])],
}

LANG_IDS = {".py": "python", ".js": "javascript", ".jsx": "javascriptreact",
            ".mjs": "javascript", ".ts": "typescript", ".tsx": "typescriptreact",
            ".php": "php", ".go": "go", ".rs": "rust"}

INIT_TIMEOUT = 60.0   # intelephense/gopls index on init; be patient once
REQ_TIMEOUT = 30.0


def die(code, msg):
    sys.stderr.write(msg.rstrip("\n") + "\n")
    sys.exit(code)


def server_cmd(lang):
    """Resolve the oracle command for a language, or (None, hint)."""
    env = os.environ.get(f"SRK_LSP_CMD_{lang.upper()}")
    if env:
        return shlex.split(env), None
    hints = []
    for argv, hint in SERVERS.get(lang, []):
        if shutil.which(argv[0]):
            return argv, None
        hints.append(f"{argv[0]} ({hint})")
    return None, " or ".join(hints) or f"no oracle registered for {lang}"


def _uri(path):
    return Path(path).resolve().as_uri()


def _pump(stdout, q):
    """Reader thread: parse Content-Length framed messages onto the queue."""
    try:
        while True:
            length = None
            while True:                       # headers until blank line
                line = stdout.readline()
                if not line:
                    q.put(None)
                    return
                if line in (b"\r\n", b"\n"):
                    break
                if line.lower().startswith(b"content-length:"):
                    length = int(line.split(b":", 1)[1].strip())
            if length is None:
                continue
            body = stdout.read(length)
            if not body or len(body) < length:
                q.put(None)
                return
            try:
                q.put(json.loads(body.decode("utf-8", errors="replace")))
            except ValueError:
                pass                          # skip malformed frames
    except Exception:
        q.put(None)


class Lsp:
    """Minimal JSON-RPC-over-stdio LSP client: init, didOpen, references."""

    def __init__(self, argv, root):
        self.proc = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, cwd=str(root))
        self.q = queue.Queue()
        threading.Thread(target=_pump, args=(self.proc.stdout, self.q),
                         daemon=True).start()
        self._id = 0
        root_uri = Path(root).resolve().as_uri()
        self.request("initialize", {
            "processId": os.getpid(), "rootUri": root_uri,
            "rootPath": str(Path(root).resolve()),
            "workspaceFolders": [{"uri": root_uri, "name": Path(root).name}],
            "capabilities": {"textDocument": {"references": {}},
                             "workspace": {"workspaceFolders": True}},
            "initializationOptions": {},
        }, timeout=INIT_TIMEOUT)
        self.notify("initialized", {})

    def _send(self, obj):
        data = json.dumps(obj).encode("utf-8")
        self.proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(data) + data)
        self.proc.stdin.flush()

    def notify(self, method, params):
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def request(self, method, params, timeout=REQ_TIMEOUT):
        self._id += 1
        rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method,
                    "params": params})
        deadline = time.monotonic() + timeout
        while True:
            remain = deadline - time.monotonic()
            if remain <= 0:
                raise TimeoutError(f"{method}: no reply in {timeout:.0f}s")
            try:
                msg = self.q.get(timeout=remain)
            except queue.Empty:
                raise TimeoutError(f"{method}: no reply in {timeout:.0f}s")
            if msg is None:
                raise RuntimeError("language server exited mid-conversation")
            if msg.get("id") == rid and ("result" in msg or "error" in msg):
                if "error" in msg:
                    raise RuntimeError(msg["error"].get("message", "LSP error"))
                return msg.get("result")
            if "method" in msg and "id" in msg:      # server->client request:
                self._send({"jsonrpc": "2.0", "id": msg["id"],
                            "result": None})         # answer, never stall
            # notifications (logMessage etc.) are dropped

    def did_open(self, path, text):
        self.notify("textDocument/didOpen", {"textDocument": {
            "uri": _uri(path), "languageId":
                LANG_IDS.get(Path(path).suffix.lower(), "plaintext"),
            "version": 1, "text": text}})

    def references(self, path, line0, char0):
        res = self.request("textDocument/references", {
            "textDocument": {"uri": _uri(path)},
            "position": {"line": line0, "character": char0},
            "context": {"includeDeclaration": False}})
        return res or []

    def close(self):
        try:
            self.request("shutdown", None, timeout=5.0)
            self.notify("exit", {})
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5.0)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


def find_position(path, symbol):
    """(line0, char0) of the symbol's name at its definition, via the map's
    own parsers — the oracle is asked about exactly what the map ranked."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    mod = parser_for(str(path))
    if mod is None:
        die(2, f"{path}: no parser for this extension — can't locate {symbol}.")
    want = symbol.split("::")[-1].split(".")[-1]
    syms = [s for s in mod.parse(text) if s.name == want]
    if "::" in symbol or "." in symbol.strip("."):
        parent = re.split(r"::|\.", symbol)[0]
        scoped = [s for s in syms if s.parent == parent]
        syms = scoped or syms
    if not syms:
        die(2, f"{symbol} not found in {path} (per the map's parser) — pass "
               "the file that DEFINES it.")
    line1 = syms[0].line
    lines = text.splitlines()
    if line1 - 1 >= len(lines):
        die(2, f"{path}: parser line {line1} is past EOF — refresh the map.")
    m = re.search(rf"\b{re.escape(want)}\b", lines[line1 - 1])
    char0 = m.start() if m else 0
    return text, line1 - 1, char0


def _fmt_loc(loc, root):
    p = loc.get("uri", "")
    if p.startswith("file://"):
        from urllib.parse import unquote, urlparse
        p = unquote(urlparse(p).path)
    try:
        p = str(Path(p).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        pass
    ln = loc.get("range", {}).get("start", {}).get("line", 0) + 1
    return f"{p}:{ln}"


def git_root(path):
    try:
        out = subprocess.run(
            ["git", "-C", str(Path(path).resolve().parent), "rev-parse",
             "--show-toplevel"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except Exception:
        pass
    return Path.cwd()


def cmd_servers():
    print("Reference oracles (LSP servers) by language:")
    for lang in SERVERS:
        argv, hint = server_cmd(lang)
        if argv:
            print(f"  ✓ {lang:<11} {' '.join(argv)}")
        else:
            print(f"  ✗ {lang:<11} not installed — {hint}")
    missing = [l for l in SERVERS if server_cmd(l)[0] is None]
    print("\nAny ✓ language upgrades x0 verification from lexical (the map) "
          "to semantic (the oracle).")
    if missing:
        print(f"Install a missing one: lsp_refs.py install "
              f"[{' | '.join(missing)}]  (runs the package manager; "
              "onboarding asks first).")


def cmd_check(pairs):
    if not pairs:
        die(2, "usage: lsp_refs.py check <file> <symbol> [<file> <symbol> ...]")
    root = git_root(pairs[0][0])
    by_lang, missing = {}, {}
    for path, symbol in pairs:
        lang = language_of(str(path))
        if lang not in SERVERS and not os.environ.get(
                f"SRK_LSP_CMD_{str(lang).upper()}"):
            missing.setdefault(str(lang), []).append((path, symbol))
            continue
        by_lang.setdefault(lang, []).append((path, symbol))

    killed, confirmed, skipped = [], [], []
    for lang, checks in by_lang.items():
        argv, hint = server_cmd(lang)
        if argv is None:
            print(f"✗ no {lang} oracle installed — install {hint}\n"
                  f"  ({len(checks)} candidate(s) stay UNVERIFIED: the map is "
                  "the only signal; the full checklist carries them.)")
            skipped.extend(checks)
            continue
        print(f"oracle: {' '.join(argv)} ({lang}, root {root})")
        client = None
        try:
            client = Lsp(argv, root)
            for path, symbol in checks:
                text, line0, char0 = find_position(path, symbol)
                client.did_open(path, text)
                refs = client.references(path, line0, char0)
                refs = [r for r in refs if not (
                    r.get("uri") == _uri(path) and
                    r.get("range", {}).get("start", {}).get("line") == line0)]
                if refs:
                    killed.append((path, symbol, refs))
                    print(f"  ✗ {symbol} ({path}) — map said x0; oracle found "
                          f"{len(refs)} reference(s) → candidate KILLED:")
                    for r in refs[:12]:
                        print(f"      {_fmt_loc(r, root)}")
                    if len(refs) > 12:
                        print(f"      … and {len(refs) - 12} more")
                else:
                    confirmed.append((path, symbol))
                    print(f"  ✓ {symbol} ({path}) — oracle-confirmed x0 "
                          "(dynamic-reference checklist still required)")
        except (RuntimeError, TimeoutError) as e:
            print(f"  ! {lang} oracle failed: {e} — remaining {lang} "
                  "candidates stay UNVERIFIED (checklist carries them).")
            skipped.extend(c for c in checks
                           if c not in confirmed and
                           c not in [(p, s) for p, s, _ in killed])
        finally:
            if client:
                client.close()

    for lang, checks in missing.items():
        print(f"– {lang}: no oracle protocol wired; checklist only.")
        skipped.extend(checks)

    n = len(killed) + len(confirmed) + len(skipped)
    print(f"\n{n} checked: {len(killed)} killed (were false x0), "
          f"{len(confirmed)} oracle-confirmed x0, {len(skipped)} unverified.")
    if confirmed:
        print("Oracle-confirmed ≠ safe-to-delete: run the dynamic-reference "
              "checklist (DI/config/reflection/templates/routes) before any cut.")
    sys.exit(1 if killed else (0 if confirmed or not skipped else 2))


def _server_exe(lang):
    return SERVERS[lang][0][0][0]        # first candidate's binary name


def _extra_bindirs(lang):
    """Where a fresh install lands when it's not yet on PATH — asked of the
    ecosystem's own tool, best-effort. rust returns the binary path directly."""
    out = []
    try:
        if lang in ("php", "javascript") and shutil.which("npm"):
            p = subprocess.run(["npm", "prefix", "-g"], capture_output=True,
                               text=True, timeout=30)
            if p.returncode == 0 and p.stdout.strip():
                out.append(Path(p.stdout.strip()) / "bin")
        elif lang == "python":
            p = subprocess.run([sys.executable, "-m", "site", "--user-base"],
                               capture_output=True, text=True, timeout=30)
            if p.returncode == 0 and p.stdout.strip():
                out.append(Path(p.stdout.strip()) / "bin")
            out.append(Path.home() / ".local" / "bin")
        elif lang == "go" and shutil.which("go"):
            for var in ("GOBIN", "GOPATH"):
                p = subprocess.run(["go", "env", var], capture_output=True,
                                   text=True, timeout=30)
                d = p.stdout.strip()
                if p.returncode == 0 and d:
                    out.append(Path(d) / "bin" if var == "GOPATH" else Path(d))
        elif lang == "rust" and shutil.which("rustup"):
            p = subprocess.run(["rustup", "which", "rust-analyzer"],
                               capture_output=True, text=True, timeout=30)
            if p.returncode == 0 and p.stdout.strip():
                out.append(Path(p.stdout.strip()))   # direct binary path
    except Exception:
        pass
    return out


def _locate(lang):
    """(path, on_path) for a language's server, or (None, False)."""
    exe = _server_exe(lang)
    hit = shutil.which(exe)
    if hit:
        return hit, True
    for d in _extra_bindirs(lang):
        cand = d if d.name == exe else d / exe
        if cand.exists():
            return str(cand), False
    return None, False


def cmd_install(langs, dry_run):
    if not langs:
        langs = [l for l in INSTALL if server_cmd(l)[0] is None]
        if not langs:
            print("all registered oracles are already installed — nothing "
                  "to do.")
            return
    unknown = [l for l in langs if l not in INSTALL]
    if unknown:
        die(2, f"no install recipe for: {', '.join(unknown)} "
               f"(known: {', '.join(INSTALL)})")

    failures = 0
    for lang in langs:
        if server_cmd(lang)[0] is not None:
            print(f"✓ {lang}: already installed — skipping.")
            continue
        candidate = next((c for c in INSTALL[lang] if shutil.which(c[0])), None)
        if dry_run:
            argv = candidate[1] if candidate else INSTALL[lang][0][1]
            flag = "" if candidate else (
                f"  (⚠ {INSTALL[lang][0][0]} not on PATH — install it first)")
            print(f"• {lang}: would run  {' '.join(argv)}{flag}")
            continue
        if candidate is None:
            need = " / ".join(c[0] for c in INSTALL[lang])
            print(f"✗ {lang}: can't auto-install — need one of [{need}] on "
                  f"PATH first. Manual: {server_cmd(lang)[1]}")
            failures += 1
            continue
        _, argv = candidate
        print(f"→ {lang}: {' '.join(argv)}")
        try:
            r = subprocess.run(argv, capture_output=True, text=True,
                               timeout=900)
        except subprocess.TimeoutExpired:
            print(f"✗ {lang}: install timed out (900s). Run it by hand: "
                  f"{' '.join(argv)}")
            failures += 1
            continue
        path, on_path = _locate(lang)
        if path and on_path:
            print(f"✓ {lang}: installed — {path}")
        elif path:
            print(f"⚠ {lang}: installed at {path}, but NOT on your PATH — the "
                  f"oracle invokes `{_server_exe(lang)}` by name, so add that "
                  "directory to PATH (or symlink it) for it to work.")
            failures += 1
        else:
            tail = "\n    ".join(
                (r.stderr or r.stdout or "").strip().splitlines()[-12:])
            note = ("\n  (PEP 668 externally-managed? try `pipx install "
                    "python-lsp-server`)" if lang == "python" else "")
            print(f"✗ {lang}: install ran (exit {r.returncode}) but "
                  f"`{_server_exe(lang)}` still isn't found.{note}"
                  + (f"\n    {tail}" if tail else ""))
            failures += 1

    if not dry_run:
        print(f"\n{len(langs) - failures}/{len(langs)} oracle(s) ready."
              + (" Re-run `lsp_refs.py servers` to confirm." if failures
                 else ""))
    sys.exit(1 if failures else 0)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        die(0, __doc__)
    if args[0] == "servers":
        cmd_servers()
        return
    if args[0] == "install":
        rest = [a for a in args[1:] if a != "--dry-run"]
        cmd_install([l.lower() for l in rest], "--dry-run" in args)
        return
    if args[0] == "check":
        rest = args[1:]
        if len(rest) < 2 or len(rest) % 2:
            die(2, "usage: lsp_refs.py check <file> <symbol> "
                   "[<file> <symbol> ...]")
        cmd_check([(rest[i], rest[i + 1]) for i in range(0, len(rest), 2)])
        return
    die(2, f"unknown subcommand {args[0]!r} — try: check, servers")


if __name__ == "__main__":
    main()
