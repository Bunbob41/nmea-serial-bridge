/**
 * Serial Link Dashboard — vanilla ES6
 * No frameworks. No NMEA/socket logic. REST only.
 * Covers: US1 telemetry, US2 start/stop, US3 unlock, US4 discovery + COM picker.
 */

// ── Constants ─────────────────────────────────────────────────────────────────
const TOKEN_KEY     = "nmea-bridge-web-token";
const SHOW_QR_KEY   = "nmea-bridge-show-qr";
const MAP_ENABLED_KEY = "nmea-bridge-map-enabled";
const MAP_BASE_LAYER_KEY = "nmea-bridge-map-base-layer";
const MAP_TRACK_MAX = 120;
/** Bumped when dashboard.js changes — used for ?v= cache bust on script tags. */
const DASHBOARD_SCRIPT_REV = "1.15.1";
let lastDashboardStatus = null;
// Keep in sync with ui/connection_fields.py BAUD_PRESETS
const BAUD_PRESETS = [4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800];
const DEFAULT_BAUD = 115200;

const GNSS_BADGE_STYLE = "padding: 6px; border-radius: 4px; font-weight: bold; display: inline-block;";

function gnssBadgeStylesheet(quality, streamIdle, stale) {
  if (streamIdle || stale || quality === 0) {
    return `background-color: #F8D7DA; color: #721C24; ${GNSS_BADGE_STYLE}`;
  }
  if (quality === 4 || quality === 5) {
    return `background-color: #D4EDDA; color: #155724; ${GNSS_BADGE_STYLE}`;
  }
  if (quality === 1 || quality === 2) {
    return `background-color: #CCE5FF; color: #004085; ${GNSS_BADGE_STYLE}`;
  }
  return `background-color: #F8D7DA; color: #721C24; ${GNSS_BADGE_STYLE}`;
}

function applyGnssStatusStyles(status) {
  const q = status.gnss_quality;
  const idle = !!status.gnss_stream_idle;
  const stale = !!status.gnss_stale;
  const ss = gnssBadgeStylesheet(
    typeof q === "number" ? q : null,
    idle,
    stale
  );
  const gEl = document.getElementById("stat-gnss");
  if (gEl) gEl.style.cssText = ss;
  const card = document.getElementById("status-card");
  if (card) {
    card.classList.remove("gnss-tone-rtk", "gnss-tone-gps", "gnss-tone-bad", "gnss-tone-idle");
    if (!status.running) {
      /* no tone when stopped */
    } else if (idle || stale || q === 0) {
      card.classList.add("gnss-tone-bad");
    } else if (q === 4 || q === 5) {
      card.classList.add("gnss-tone-rtk");
    } else if (q === 1 || q === 2) {
      card.classList.add("gnss-tone-gps");
    } else {
      card.classList.add("gnss-tone-idle");
    }
  }
}

const POLL_INTERVAL = 1000;           // status poll ms
const DISC_POLL_MS  = 500;            // discovery poll after refresh
const DISC_TIMEOUT  = 25_000;         // stop discovery poll after 25 s (LAN scan ~6 s)

// ── Session state ─────────────────────────────────────────────────────────────
let connected         = false;
let commandInFlight   = false;
let discoveryScanning = false;
let discPollTimer     = null;
let discPollStart     = 0;
let lastDiscMono      = 0;
let token             = localStorage.getItem(TOKEN_KEY) || "";
let tokenRequired     = false;
let lanBind           = false;
let bridgeRunning     = false;

// ── Token helpers ─────────────────────────────────────────────────────────────
function saveToken(val) {
  token = (val || "").trim();
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else       localStorage.removeItem(TOKEN_KEY);
}

function clearToken() {
  saveToken("");
  const inp = document.getElementById("token-input");
  if (inp) inp.value = "";
}

function hashFragment(text) {
  const s = (text || "").trim();
  const i = s.indexOf("#");
  return i >= 0 ? s.slice(i + 1) : s;
}

function parseTokenFromText(text) {
  const s = (text || "").trim();
  if (!s) return null;
  if (s.includes("bridge-token=")) {
    const frag = hashFragment(s);
    try {
      const v = new URLSearchParams(frag).get("bridge-token");
      if (v) {
        try {
          return decodeURIComponent(v);
        } catch (_) {
          return v;
        }
      }
    } catch (_) { /* ignore */ }
    const m = frag.match(/bridge-token=([^&]+)/);
    if (m) {
      try {
        return decodeURIComponent(m[1]);
      } catch (_) {
        return m[1];
      }
    }
  }
  if (s.length >= 20 && !/\s/.test(s)) return s;
  return null;
}

function applyTokenValue(val) {
  const t = parseTokenFromText(val) || (val || "").trim();
  if (!t) return false;
  saveToken(t);
  const inp = document.getElementById("token-input");
  if (inp) inp.value = token;
  return true;
}

function consumeTokenFromHash() {
  const hash = location.hash.slice(1);
  if (!hash) return false;
  if (!applyTokenValue(`#${hash}`)) return false;
  history.replaceState(null, "", location.pathname + location.search);
  showAlert("run-alert", "API token saved from setup link.", "ok");
  return true;
}

function isCoarseMobile() {
  return (
    window.matchMedia("(max-width: 768px)").matches ||
    (navigator.maxTouchPoints > 0 && window.innerWidth < 1024)
  );
}

function buildSetupUrl(base, tok) {
  const b = (base || location.origin || "").replace(/\/$/, "");
  const t = encodeURIComponent((tok || token || "").trim());
  return `${b}/#bridge-token=${t}`;
}

function clipboardCopyHint() {
  if (window.isSecureContext) return "";
  return " Copy may be blocked on HTTP (Tailscale) — use Share link, open the setup URL from Messages, or Paste setup link.";
}

async function copyToClipboard(text) {
  if (!text) return false;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (_) { /* fall through */ }
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.top = "0";
  ta.style.left = "0";
  ta.style.width = "2em";
  ta.style.height = "2em";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  ta.setSelectionRange(0, text.length);
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch (_) { /* ignore */ }
  document.body.removeChild(ta);
  return ok;
}

async function copyTokenToClipboard() {
  const t = (document.getElementById("token-input")?.value || token || "").trim();
  if (!t) {
    showAlert("run-alert", "No token yet — get one from the PC (see steps below).", "warn");
    return;
  }
  if (await copyToClipboard(t)) {
    showAlert("run-alert", "Token copied to clipboard.", "ok");
  } else {
    showAlert(
      "run-alert",
      "Could not copy." + clipboardCopyHint() + " To move token to another device, use Copy setup link on the PC.",
      "warn"
    );
  }
}

async function copySetupLink() {
  const t = (document.getElementById("token-input")?.value || token || "").trim();
  if (!t) {
    showAlert("run-alert", "No token yet — on the PC use Tools → Phone → Copy phone setup link.", "warn");
    return;
  }
  const url = buildSetupUrl(location.origin, t);
  if (await copyToClipboard(url)) {
    showAlert(
      "run-alert",
      "Setup link copied — open it once in Safari or use Paste setup link on the other device.",
      "ok"
    );
  } else if (navigator.share) {
    await shareSetupLink();
  } else {
    showAlert(
      "run-alert",
      "Could not copy link." + clipboardCopyHint(),
      "warn"
    );
  }
}

async function pasteSetupLink() {
  let raw = "";
  try {
    raw = await navigator.clipboard.readText();
  } catch (_) {
    raw = window.prompt("Paste setup link or token from the other device:", "") || "";
  }
  if (!applyTokenValue(raw)) {
    showAlert("run-alert", "Could not find a token in that text.", "warn");
    return;
  }
  showAlert("run-alert", "Token applied.", "ok");
}

async function shareSetupLink() {
  const t = (document.getElementById("token-input")?.value || token || "").trim();
  if (!t) {
    showAlert("run-alert", "Save a token first.", "warn");
    return;
  }
  const url = buildSetupUrl(location.origin, t);
  if (navigator.share) {
    try {
      await navigator.share({
        title: "Serial Link dashboard",
        text: "Open to save API token",
        url,
      });
      showAlert("run-alert", "Share the link to your PC (email, Teams, etc.), then Paste setup link in Tools → Phone on the PC.", "ok");
      return;
    } catch (e) {
      if (e && e.name === "AbortError") return;
    }
  }
  await copySetupLink();
}

function updateTransferHint() {
  const body = document.getElementById("token-transfer-body");
  const shareBtn = document.getElementById("btn-share-setup");
  if (!body) return;
  const mobile = isCoarseMobile();
  if (shareBtn) shareBtn.hidden = !navigator.share;
  if (mobile) {
    body.innerHTML =
      "<strong>First time (get token from PC):</strong> On the survey PC open <strong>Tools → Phone</strong> → " +
      "<strong>Copy phone setup link</strong>. Send that link to this iPhone (Messages, email). " +
      "Then either <strong>tap the link</strong> in Messages (best) or scroll to Tools here and tap <strong>Paste setup link</strong>. " +
      "Do not use Copy token on the phone until the field above already has a token.<br><br>" +
      "<strong>Note:</strong> Copy buttons often fail on HTTP; Paste setup link and opening the link work.";
  } else {
    body.innerHTML =
      "<strong>To phone:</strong> Copy setup link here → open on the phone once (or Paste setup link in phone Tools). " +
      "<strong>From phone:</strong> Copy/Share setup link on the phone → <strong>Paste setup link</strong> here and in <strong>Tools → Phone</strong> on the PC app.";
  }
}

function toggleTokenReveal() {
  const inp = document.getElementById("token-input");
  const btn = document.getElementById("btn-token-reveal");
  if (!inp) return;
  const show = inp.type === "password";
  inp.type = show ? "text" : "password";
  if (btn) btn.textContent = show ? "Hide" : "Show";
}

function authHeaders() {
  const h = { "Content-Type": "application/json" };
  if (token) h["X-Bridge-Token"] = token;
  return h;
}

// ── API error extraction ──────────────────────────────────────────────────────
// FastAPI detail can be a string (e.g. 401) or an object with .message (our models).
function extractApiError(body, fallback) {
  const d = body && body.detail;
  if (!d) return fallback;
  if (typeof d === "string") return d;
  if (d.message) return d.message;
  return JSON.stringify(d);
}

// ── Fetch wrapper ─────────────────────────────────────────────────────────────
async function apiFetch(url, opts = {}) {
  const res = await fetch(url, {
    headers: authHeaders(),
    ...opts,
  });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
}

// ── Initialise ────────────────────────────────────────────────────────────────
async function init() {
  try {
    consumeTokenFromHash();
    const qrChk = document.getElementById("chk-show-qr");
    if (qrChk) qrChk.checked = localStorage.getItem(SHOW_QR_KEY) === "1";
    const modeSel = document.getElementById("cfg-netmode-select");
    if (modeSel) modeSel.addEventListener("change", updateConfigModeFields);
    await loadMeta();
    await loadConfig();
    await pollDiscovery();
    updateTransferHint();
    updateQrDisplay();
    initMonitorSections();
    initDashboardPanels();
    if (!isGridstackLayoutPage()) {
      initDashboardPanelOrder();
    }
    initDashboardPanelReorder();
    initPositionMap();
    initDashboardChromeMenus();
    initDeviceListClicks();
  } catch (e) {
    showAlert("run-alert", "Dashboard init error: " + e.message, "error");
  }
  try {
    initWebLog();
  } catch (e) {
    console.warn("Live log panel failed:", e);
  }
  startStatusPoll();
  if (isGridstackLayoutPage() && typeof window.initGridstackDashboard === "function") {
    window.initGridstackDashboard();
  }
  initLayoutLockControl();
}

function updateTokenSectionVisibility() {
  const ts = document.getElementById("token-section");
  if (ts) ts.hidden = !(tokenRequired || lanBind);
}

// ── Meta / version ────────────────────────────────────────────────────────────
async function loadMeta() {
  try {
    const { ok, body } = await apiFetch("/meta");
    if (!ok) return;
    // version tag
    const vt = document.getElementById("ver-tag");
    if (vt) vt.textContent = body.version || "";
    tokenRequired = !!body.token_required;
    lanBind = !!body.lan_bind;
    updateTokenSectionVisibility();
    if (tokenRequired || lanBind) {
      const inp = document.getElementById("token-input");
      if (inp) inp.value = token;
      if (!token) {
        const msg = isCoarseMobile()
          ? "LAN mode: get a setup link from the PC (Tools → Phone → Copy phone setup link) and open it here, or Paste setup link below."
          : "LAN mode: use Copy setup link / Paste setup link below, or Tools → Phone on the PC app.";
        showAlert("run-alert", msg, "warn");
      } else {
        const runAlert = document.getElementById("run-alert");
        if (runAlert && runAlert.classList.contains("warn")) {
          runAlert.className = "alert ok";
          runAlert.textContent = "";
        }
      }
    }
    if (body.commands_ready === false) {
      showAlert(
        "run-alert",
        "Desktop bridge window not linked to the web API — fully quit and restart Serial Link (need v1.8.2+), then hard-refresh this page (Ctrl+F5).",
        "warn"
      );
    }
    // footer
    const fn = document.getElementById("footer-note");
    if (fn) fn.textContent = `NMEA Serial Bridge v${body.version || "?"}  —  Dashboard`;
  } catch (_) { /* meta non-critical */ }
}

// ── Status poll ───────────────────────────────────────────────────────────────
function startStatusPoll() {
  pollStatus();
  setInterval(pollStatus, POLL_INTERVAL);
}

async function pollStatus() {
  try {
    const { ok, body } = await apiFetch("/status");
    if (!ok) { setOffline(); return; }
    setOnline(body);
  } catch (_) {
    setOffline();
  }
}

function setOnline(status) {
  const wasOffline = !connected;
  connected = true;
  bridgeRunning = !!status.running;
  setConfigFormDisabled(false);
  setConfigLocked(bridgeRunning);
  // Clear stale "Application window not available" alerts that accumulated at startup.
  if (wasOffline) {
    ["run-alert", "unlock-alert", "discovery-alert"].forEach(id => {
      const el = document.getElementById(id);
      if (el && el.textContent.includes("window not available")) el.hidden = true;
    });
  }
  // connection indicator
  const dot   = document.getElementById("conn-dot");
  const label = document.getElementById("conn-label");
  if (dot) {
    dot.className = "conn-dot " + (status.running ? "running" : "online");
  }
  if (label) label.textContent = status.running ? "Running" : "Online";

  // offline banner
  const ob = document.getElementById("offline-banner");
  if (ob) ob.hidden = true;
  const sg = document.getElementById("status-grid");
  if (sg) sg.hidden = false;

  setEl("stat-state", status.running ? "running" : "stopped");
  setBadgeClass("stat-state", status.running ? "running" : "stopped");
  setEl("stat-com", status.com_port || "—");
  setEl("stat-baud", status.baud != null ? String(status.baud) : "—");
  setEl("stat-udp", formatUdpBindDisplay(status));
  setEl("stat-nmea", formatNmeaModeDisplay(status.nmea_mode));

  const transportOk = status.transport_ok !== false;
  setEl("stat-transport", transportOk ? "OK" : "Warn");
  const tEl = document.getElementById("stat-transport");
  if (tEl) {
    tEl.className = `stat-value ${transportOk ? "ok-val" : "alert-val"}`;
  }

  setEl("stat-hz-down", fmtHz(status.hz_net_to_com));
  setEl("stat-hz-up", fmtHz(status.hz_com_to_net));
  setEl("stat-hz-inject", fmtHz(status.hz_inject));

  setEl("stat-lines-down", fmtCount(status.lines_net_to_com));
  setEl("stat-lines-up", fmtCount(status.lines_com_to_net));

  const gnssStale = !!status.gnss_stale || !!status.gnss_stream_idle;
  let gnssText = (status.gnss_summary || status.gnss_fix || "—").trim() || "—";
  if (status.gnss_stream_idle) gnssText = "No Data Stream";
  setEl("stat-gnss", gnssText);
  applyGnssStatusStyles(status);

  setEl("stat-sats", status.gnss_sats != null ? String(status.gnss_sats) : "—");
  setEl(
    "stat-hdop",
    status.gnss_hdop != null ? Number(status.gnss_hdop).toFixed(1) : "—"
  );

  markWarnStat("stat-drop-n2s", status.drops_net_to_com ?? status.drops);
  markWarnStat("stat-drop-s2n", status.drops_com_to_net ?? 0);
  markWarnStat("stat-rej-n2s", status.rejects_net_to_com ?? status.rejects);
  markWarnStat("stat-rej-s2n", status.rejects_com_to_net ?? 0);
  setEl("stat-q-n2s", String(status.queue_net_to_com ?? 0));
  setEl("stat-q-s2n", String(status.queue_com_to_net ?? 0));
  markQueueStat("stat-q-n2s", status.queue_net_to_com);
  markQueueStat("stat-q-s2n", status.queue_com_to_net);
  updateMonitorSummaries(status);
  updateDashboardPanelSummaries(status);
  updateHeaderStatusChip(status);
  lastDashboardStatus = status;
  updatePositionMap(status);
}

function updateHeaderStatusChip(status) {
  const chip = document.getElementById("header-status-chip");
  if (!chip) return;
  chip.classList.remove("chip-running", "chip-stopped", "chip-offline");
  if (!status) {
    chip.textContent = "Offline";
    chip.classList.add("chip-offline");
    return;
  }
  const com = (status.com_port || "—").trim() || "—";
  const port = status.udp_listen_port != null ? String(status.udp_listen_port) : "—";
  const run = status.running ? "Running" : "Stopped";
  const hz = fmtHz(status.hz_net_to_com);
  chip.textContent = `${com} · ${port} · ${run} · ${hz} net→COM`;
  chip.classList.add(status.running ? "chip-running" : "chip-stopped");
}

function isGridstackLayoutPage() {
  return document.body.classList.contains("layout-gridstack");
}

// ── Right-click panel chrome (hide headers, log terminal-only, map focus) ─────
const DASHBOARD_CHROME_KEY = "nmea-dashboard-chrome-v1";
const LAYOUT_LOCK_KEY = "nmea-dashboard-layout-locked";

function isDashboardLayoutLocked() {
  return localStorage.getItem(LAYOUT_LOCK_KEY) === "1";
}

function initLayoutLockControl() {
  const wrap = document.getElementById("layout-lock-wrap");
  const chk = document.getElementById("layout-lock");
  if (!wrap || !chk) return;
  const onGrid = isGridstackLayoutPage();
  wrap.hidden = !onGrid;
  chk.checked = isDashboardLayoutLocked();
  if (!chk.dataset.wired) {
    chk.dataset.wired = "1";
    chk.addEventListener("change", () => {
      localStorage.setItem(LAYOUT_LOCK_KEY, chk.checked ? "1" : "0");
      if (typeof window.applyGridstackLayoutLock === "function") {
        window.applyGridstackLayoutLock(chk.checked);
      }
    });
  }
  if (onGrid && typeof window.applyGridstackLayoutLock === "function") {
    window.applyGridstackLayoutLock(chk.checked);
  }
}
const DASHBOARD_PANEL_IDS = [
  "com-setup",
  "status",
  "map",
  "configuration",
  "tools",
  "log",
  "discovery",
];

let chromeMenuEl = null;
/** Ignore outside-close until after open (blocks scroll/autoclick right after contextmenu). */
let chromeMenuCloseGuardUntil = 0;

const MONITOR_LAYOUT_MODES = ["rows", "columns", "simple"];

function defaultChromePrefs() {
  return {
    hiddenHeaders: [],
    logTerminalOnly: false,
    mapPrioritized: false,
    mapShowTrack: true,
    mapBaseLayer: "street",
    monitorLayout: "rows",
    hideResizeGrips: false,
  };
}

function loadChromePrefs() {
  try {
    const raw = JSON.parse(localStorage.getItem(DASHBOARD_CHROME_KEY) || "{}");
    const prefs = defaultChromePrefs();
    if (Array.isArray(raw.hiddenHeaders)) {
      prefs.hiddenHeaders = raw.hiddenHeaders.filter((id) => DASHBOARD_PANEL_IDS.includes(id));
    }
    prefs.logTerminalOnly = !!raw.logTerminalOnly;
    prefs.mapPrioritized = !!raw.mapPrioritized;
    if (raw.mapShowTrack === false) prefs.mapShowTrack = false;
    const base = raw.mapBaseLayer;
    prefs.mapBaseLayer = base === "satellite" ? "satellite" : "street";
    const layout = raw.monitorLayout;
    prefs.monitorLayout = MONITOR_LAYOUT_MODES.includes(layout) ? layout : "rows";
    prefs.hideResizeGrips = !!raw.hideResizeGrips;
    return prefs;
  } catch (_) {
    return defaultChromePrefs();
  }
}

function saveChromePrefs(prefs) {
  localStorage.setItem(DASHBOARD_CHROME_KEY, JSON.stringify(prefs));
}

function applyChromePrefs(prefs) {
  DASHBOARD_PANEL_IDS.forEach((id) => {
    const panel = document.querySelector(`.dashboard-panel[data-panel="${id}"]`);
    if (!panel) return;
    const hide = prefs.hiddenHeaders.includes(id);
    panel.classList.toggle("chrome-header-hidden", hide);
    if (hide && typeof setDashboardPanelOpen === "function") {
      setDashboardPanelOpen(panel, true, false);
    }
    syncPanelChromeFab(panel);
  });

  const logCard = document.getElementById("log-card");
  if (logCard) {
    logCard.classList.toggle("log-terminal-only", prefs.logTerminalOnly);
    if (prefs.logTerminalOnly && typeof setDashboardPanelOpen === "function") {
      setDashboardPanelOpen(logCard, true, false);
    }
  }

  const mapCard = document.getElementById("map-card");
  if (mapCard) {
    mapCard.classList.toggle("map-prioritized", prefs.mapPrioritized);
    if (prefs.mapPrioritized) {
      const chk = document.getElementById("map-enabled");
      if (chk && !chk.checked) {
        chk.checked = true;
        localStorage.setItem(MAP_ENABLED_KEY, "1");
      }
      syncMapVisibility();
      ensureBridgeMap();
      setTimeout(() => mapInstance?.invalidateSize(), 150);
    }
    syncMapTrackVisibility(prefs.mapShowTrack !== false);
  }

  applyMonitorLayout(prefs.monitorLayout || "rows");

  document.body.classList.toggle(
    "layout-gridstack-hide-resize-grips",
    isGridstackLayoutPage() && !!prefs.hideResizeGrips
  );
}

function setHideResizeGrips(on) {
  const prefs = loadChromePrefs();
  prefs.hideResizeGrips = on;
  saveChromePrefs(prefs);
  applyChromePrefs(prefs);
}

/** Restores .stat-item shells after Columns table teardown. */
const monitorGridItemStore = new WeakMap();

function _clearMonitorTableCellStyle(el) {
  el.classList.remove(
    "monitor-table-head",
    "monitor-table-body",
    "monitor-table-gnss-head",
    "monitor-table-gnss-body"
  );
  el.style.gridRow = "";
  el.style.gridColumn = "";
}

function teardownMonitorColumnsTable(card) {
  if (!card) return;
  card.querySelectorAll(".monitor-grid[data-columns-table]").forEach((grid) => {
    const shells = monitorGridItemStore.get(grid);
    const labels = [...grid.querySelectorAll(":scope > .stat-label")];
    const values = [...grid.querySelectorAll(":scope > .stat-value")];
    grid.replaceChildren();
    grid.classList.remove("monitor-data-table");
    grid.style.removeProperty("--monitor-cols");
    if (shells?.length) {
      shells.forEach((shell, i) => {
        if (labels[i]) {
          _clearMonitorTableCellStyle(labels[i]);
          shell.appendChild(labels[i]);
        }
        if (values[i]) {
          _clearMonitorTableCellStyle(values[i]);
          shell.appendChild(values[i]);
        }
        grid.appendChild(shell);
      });
    }
    delete grid.dataset.columnsTable;
    monitorGridItemStore.delete(grid);
  });
}

function buildMonitorColumnsTable(card) {
  if (!card) return;
  card.querySelectorAll(".monitor-grid").forEach((grid) => {
    if (grid.dataset.columnsTable) return;
    const items = [...grid.querySelectorAll(":scope > .stat-item")];
    if (!items.length) return;

    monitorGridItemStore.set(
      grid,
      items.map((item) => {
        const shell = document.createElement("div");
        shell.className = item.className;
        if (item.id) shell.id = `${item.id}-shell`;
        return shell;
      })
    );

    const regular = items.filter((item) => !item.classList.contains("monitor-stat-gnss"));
    const gnssItems = items.filter((item) => item.classList.contains("monitor-stat-gnss"));
    const cols = Math.max(regular.length, 1);

    grid.classList.add("monitor-data-table");
    grid.dataset.columnsTable = "1";
    grid.style.setProperty("--monitor-cols", String(cols));

    let col = 1;
    regular.forEach((item) => {
      const lab = item.querySelector(".stat-label");
      const val = item.querySelector(".stat-value");
      if (lab) {
        lab.classList.add("monitor-table-head");
        lab.style.gridRow = "1";
        lab.style.gridColumn = String(col);
        grid.appendChild(lab);
      }
      if (val) {
        val.classList.add("monitor-table-body");
        val.style.gridRow = "2";
        val.style.gridColumn = String(col);
        grid.appendChild(val);
      }
      item.remove();
      col += 1;
    });

    const gnssLabelRow = regular.length > 0 ? 3 : 1;
    const gnssValueRow = gnssLabelRow + 1;
    gnssItems.forEach((item) => {
      const lab = item.querySelector(".stat-label");
      const val = item.querySelector(".stat-value");
      if (lab) {
        lab.classList.add("monitor-table-head", "monitor-table-gnss-head");
        lab.style.gridRow = String(gnssLabelRow);
        lab.style.gridColumn = "1 / -1";
        grid.appendChild(lab);
      }
      if (val) {
        val.classList.add("monitor-table-body", "monitor-table-gnss-body");
        val.style.gridRow = String(gnssValueRow);
        val.style.gridColumn = "1 / -1";
        grid.appendChild(val);
      }
      item.remove();
    });
  });
}

function applyMonitorLayout(mode) {
  const card = document.getElementById("status-card");
  if (!card) return;
  const layout = MONITOR_LAYOUT_MODES.includes(mode) ? mode : "rows";

  if (card.classList.contains("monitor-layout-columns") && layout !== "columns") {
    teardownMonitorColumnsTable(card);
  }

  card.classList.remove(
    "monitor-layout-rows",
    "monitor-layout-columns",
    "monitor-layout-simple"
  );
  card.classList.add(`monitor-layout-${layout}`);

  if (layout === "columns") {
    teardownMonitorColumnsTable(card);
    buildMonitorColumnsTable(card);
  } else {
    teardownMonitorColumnsTable(card);
  }

  if (layout === "simple") {
    teardownMonitorColumnsTable(card);
    ["connection", "rates", "session"].forEach((id) => {
      const sec = document.querySelector(`.monitor-section[data-section="${id}"]`);
      if (sec) setMonitorSectionOpen(sec, true, false);
    });
  }
  syncMonitorFieldLabels(layout);
  if (lastDashboardStatus) setOnline(lastDashboardStatus);
}

function setMonitorLayout(mode) {
  const prefs = loadChromePrefs();
  prefs.monitorLayout = mode;
  saveChromePrefs(prefs);
  applyMonitorLayout(mode);
}

function hideChromeMenu() {
  if (chromeMenuEl) {
    chromeMenuEl.hidden = true;
    chromeMenuEl.innerHTML = "";
  }
}

function armChromeMenuCloseGuard(ms = 450) {
  chromeMenuCloseGuardUntil = Date.now() + ms;
}

function showChromeMenuAt(clientX, clientY, items) {
  hideChromeMenu();
  armChromeMenuCloseGuard();
  if (!chromeMenuEl) {
    chromeMenuEl = document.createElement("div");
    chromeMenuEl.id = "dashboard-chrome-menu";
    chromeMenuEl.className = "dashboard-chrome-menu";
    chromeMenuEl.hidden = true;
    document.body.appendChild(chromeMenuEl);
  }
  items.forEach((item) => {
    if (item.separator) {
      const hr = document.createElement("div");
      hr.className = "dashboard-chrome-menu-sep";
      hr.setAttribute("role", "separator");
      chromeMenuEl.appendChild(hr);
      return;
    }
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "dashboard-chrome-menu-item";
    btn.textContent = item.label;
    if (item.disabled) btn.disabled = true;
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      hideChromeMenu();
      item.action();
    });
    chromeMenuEl.appendChild(btn);
  });
  chromeMenuEl.hidden = false;
  const pad = 8;
  const rect = chromeMenuEl.getBoundingClientRect();
  let left = clientX;
  let top = clientY;
  if (left + rect.width > window.innerWidth - pad) left = window.innerWidth - rect.width - pad;
  if (top + rect.height > window.innerHeight - pad) top = window.innerHeight - rect.height - pad;
  chromeMenuEl.style.left = `${Math.max(pad, left)}px`;
  chromeMenuEl.style.top = `${Math.max(pad, top)}px`;
}

function openChromeMenuForPanel(panelId, anchor) {
  if (!panelId || !DASHBOARD_PANEL_IDS.includes(panelId)) return;
  const items = buildChromeMenuItems(panelId);
  let x = window.innerWidth / 2;
  let y = 72;
  if (anchor && typeof anchor.clientX === "number") {
    x = anchor.clientX;
    y = anchor.clientY;
  } else if (anchor && typeof anchor.getBoundingClientRect === "function") {
    const r = anchor.getBoundingClientRect();
    x = r.left;
    y = r.bottom + 4;
  }
  showChromeMenuAt(x, y, items);
}

function syncPanelChromeFab(panel) {
  const panelId = panel?.dataset?.panel;
  if (!panelId) return;
  const hidden = panel.classList.contains("chrome-header-hidden");
  let fab = panel.querySelector(".panel-chrome-fab");
  if (hidden) {
    if (!fab) {
      fab = document.createElement("button");
      fab.type = "button";
      fab.className = "panel-chrome-fab";
      fab.setAttribute("aria-label", "Section options");
      fab.title = "Section options";
      fab.textContent = "⋯";
      fab.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        openChromeMenuForPanel(panelId, fab);
      });
      panel.insertBefore(fab, panel.firstChild);
    }
    fab.hidden = false;
  } else if (fab) {
    fab.remove();
  }
}

function ensurePanelChromeMenuButtons() {
  document.querySelectorAll(".dashboard-panel[data-panel]").forEach((panel) => {
    syncPanelChromeFab(panel);
    const toggle = panel.querySelector(".dashboard-panel-toggle");
    if (!toggle || toggle.querySelector(".panel-chrome-menu-btn")) return;
    const panelId = panel.dataset.panel;
    const menuBtn = document.createElement("button");
    menuBtn.type = "button";
    menuBtn.className = "panel-chrome-menu-btn";
    menuBtn.setAttribute("aria-label", "Section options");
    menuBtn.title = "Section options";
    menuBtn.textContent = "⋯";
    menuBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openChromeMenuForPanel(panelId, menuBtn);
    });
    toggle.appendChild(menuBtn);
  });
}

let chromeLongPressTimer = null;
let chromeLongPressPanelId = null;

function findChromePanelFromTarget(target) {
  let panel = target.closest(".dashboard-panel[data-panel]");
  if (!panel && target.closest(".status-card .monitor-wrap, .status-card .monitor-section")) {
    panel = document.getElementById("status-card");
  }
  return panel;
}

function clearChromeLongPress() {
  if (chromeLongPressTimer) {
    clearTimeout(chromeLongPressTimer);
    chromeLongPressTimer = null;
  }
  chromeLongPressPanelId = null;
}

function initChromeLongPress() {
  document.addEventListener(
    "touchstart",
    (e) => {
      if (!isCoarseMobile()) return;
      if (e.target.closest(".panel-chrome-menu-btn, .panel-chrome-fab, .dashboard-chrome-menu")) {
        return;
      }
      const panel = findChromePanelFromTarget(e.target);
      if (!panel) return;
      const panelId = panel.dataset.panel;
      if (!panelId || !DASHBOARD_PANEL_IDS.includes(panelId)) return;
      const touch = e.touches[0];
      if (!touch) return;
      clearChromeLongPress();
      chromeLongPressPanelId = panelId;
      const tx = touch.clientX;
      const ty = touch.clientY;
      chromeLongPressTimer = window.setTimeout(() => {
        chromeLongPressTimer = null;
        openChromeMenuForPanel(panelId, { clientX: tx, clientY: ty });
        if (navigator.vibrate) navigator.vibrate(12);
      }, 550);
    },
    { passive: true }
  );
  document.addEventListener("touchend", clearChromeLongPress);
  document.addEventListener("touchcancel", clearChromeLongPress);
  document.addEventListener("touchmove", () => {
    if (chromeLongPressTimer) clearChromeLongPress();
  });
}

function setPanelHeaderHidden(panelId, hidden) {
  const prefs = loadChromePrefs();
  const set = new Set(prefs.hiddenHeaders);
  if (hidden) set.add(panelId);
  else set.delete(panelId);
  prefs.hiddenHeaders = [...set];
  saveChromePrefs(prefs);
  applyChromePrefs(prefs);
}

function setAllPanelHeadersHidden(hidden) {
  const prefs = loadChromePrefs();
  prefs.hiddenHeaders = hidden ? [...DASHBOARD_PANEL_IDS] : [];
  saveChromePrefs(prefs);
  applyChromePrefs(prefs);
}

function setLogTerminalOnly(on) {
  const prefs = loadChromePrefs();
  prefs.logTerminalOnly = on;
  saveChromePrefs(prefs);
  applyChromePrefs(prefs);
}

function setMapPrioritized(on) {
  const prefs = loadChromePrefs();
  prefs.mapPrioritized = on;
  saveChromePrefs(prefs);
  applyChromePrefs(prefs);
}

function statusHasMapFix(status) {
  if (!status || status.gnss_stream_idle) return false;
  const lat = status.position_lat;
  const lon = status.position_lon;
  return (
    lat != null &&
    lon != null &&
    Number.isFinite(Number(lat)) &&
    Number.isFinite(Number(lon))
  );
}

function ensureMapEnabledFromChrome() {
  const chk = document.getElementById("map-enabled");
  if (!chk || chk.checked) return;
  chk.checked = true;
  localStorage.setItem(MAP_ENABLED_KEY, "1");
  syncMapVisibility();
  ensureBridgeMap();
}

function syncMapTrackVisibility(show) {
  if (!mapTrackLine || !mapInstance) return;
  const onMap = mapInstance.hasLayer(mapTrackLine);
  if (show && !onMap) mapTrackLine.addTo(mapInstance);
  if (!show && onMap) mapTrackLine.remove();
}

function setMapShowTrack(on) {
  const prefs = loadChromePrefs();
  prefs.mapShowTrack = !!on;
  saveChromePrefs(prefs);
  syncMapTrackVisibility(prefs.mapShowTrack);
}

function clearMapTrack() {
  mapTrackPoints = [];
  if (mapTrackLine) mapTrackLine.setLatLngs([]);
}

function centerMapOnFix() {
  ensureMapEnabledFromChrome();
  ensureBridgeMap();
  if (!mapInstance || !mapMarker || !statusHasMapFix(lastDashboardStatus)) return;
  const lat = Number(lastDashboardStatus.position_lat);
  const lon = Number(lastDashboardStatus.position_lon);
  const ll = [lat, lon];
  const stale = !!lastDashboardStatus.position_stale;
  const zoom = stale ? Math.min(mapInstance.getZoom(), 14) : 16;
  mapInstance.setView(ll, zoom, { animate: true });
  mapMarker.setLatLng(ll);
  setTimeout(() => mapInstance?.invalidateSize(), 80);
}

function fitMapToTrack() {
  ensureMapEnabledFromChrome();
  ensureBridgeMap();
  if (!mapInstance || typeof L === "undefined") return;
  if (mapTrackPoints.length >= 2) {
    const bounds = L.latLngBounds(mapTrackPoints);
    mapInstance.fitBounds(bounds, { padding: [24, 24], maxZoom: 17, animate: true });
    setTimeout(() => mapInstance?.invalidateSize(), 80);
    return;
  }
  centerMapOnFix();
}

function toggleMapEnabledFromChrome() {
  const chk = document.getElementById("map-enabled");
  if (!chk) return;
  chk.checked = !chk.checked;
  localStorage.setItem(MAP_ENABLED_KEY, chk.checked ? "1" : "0");
  syncMapVisibility();
  if (chk.checked) {
    ensureBridgeMap();
    setTimeout(() => mapInstance?.invalidateSize(), 120);
  }
}

function setLogPauseFromChrome(on) {
  logUiPaused = !!on;
  const chk = document.getElementById("log-pause-ui");
  if (chk) chk.checked = logUiPaused;
  if (!logUiPaused) renderWebLog(true);
  updateLogMeta();
}

function setLogAutoscrollFromChrome(on) {
  logAutoscroll = !!on;
  const chk = document.getElementById("log-autoscroll");
  if (chk) chk.checked = logAutoscroll;
  if (logAutoscroll) scrollLogToEnd();
}

function expandAllMonitorSections() {
  document.querySelectorAll(".monitor-section").forEach((sec) => {
    setMonitorSectionOpen(sec, true, false);
  });
}

function resolveChromePanelFromEvent(e) {
  const el = e.target;
  if (!el || !el.closest) return null;
  if (
    el.closest(
      "#map-card, .map-card, #map-frame, #bridge-map, .bridge-map, .leaflet-container, .leaflet-pane, .map-hint, .map-coords, .map-enable-row"
    )
  ) {
    return document.getElementById("map-card");
  }
  if (el.closest("#log-card, .log-card, #log-panel, .log-panel, .log-toolbar, .log-view")) {
    return document.getElementById("log-card");
  }
  if (el.closest("#status-card, .status-card, .monitor-wrap, .monitor-section")) {
    return document.getElementById("status-card");
  }
  if (el.closest("#com-setup-card, .com-setup-card")) {
    return document.getElementById("com-setup-card");
  }
  if (el.closest("#discovery-card, .discovery-card")) {
    return document.getElementById("discovery-card");
  }
  if (el.closest("#tools-card, .tools-card")) {
    return document.getElementById("tools-card");
  }
  if (el.closest("#config-card, .config-card")) {
    return document.getElementById("config-card");
  }
  return el.closest(".dashboard-panel[data-panel]");
}

function appendMapChromeMenuItems(items, prefs) {
  const mapOn = !!document.getElementById("map-enabled")?.checked;
  const hasFix = statusHasMapFix(lastDashboardStatus);
  const trackLen = mapTrackPoints.length;
  items.push({
    label: mapOn ? "✓ Show map" : "Show map",
    action: () => toggleMapEnabledFromChrome(),
  });
  items.push({
    label: "Center on fix",
    disabled: !hasFix,
    action: () => centerMapOnFix(),
  });
  items.push({
    label: "Fit track in view",
    disabled: trackLen < 2 && !hasFix,
    action: () => fitMapToTrack(),
  });
  items.push({
    label: trackLen ? `Clear track (${trackLen} pts)` : "Clear track",
    disabled: trackLen === 0,
    action: () => clearMapTrack(),
  });
  items.push({
    label: prefs.mapShowTrack ? "✓ Show position track" : "Show position track",
    action: () => setMapShowTrack(!prefs.mapShowTrack),
  });
  const mapBase = loadMapBaseLayer();
  items.push({ separator: true });
  items.push({
    label: mapBase === "street" ? "✓ Map layer: Street" : "Map layer: Street",
    action: () => setMapBaseLayer("street"),
  });
  items.push({
    label: mapBase === "satellite" ? "✓ Map layer: Satellite" : "Map layer: Satellite",
    action: () => setMapBaseLayer("satellite"),
  });
  items.push({
    label: prefs.mapPrioritized ? "Show map controls" : "Prioritize map",
    action: () => setMapPrioritized(!prefs.mapPrioritized),
  });
  items.push({
    label: "Refresh map size",
    disabled: !mapOn,
    action: () => {
      ensureBridgeMap();
      invalidateDashboardMap();
    },
  });
}

function buildChromeMenuItems(panelId) {
  const prefs = loadChromePrefs();
  const headerHidden = prefs.hiddenHeaders.includes(panelId);
  const items = [];

  if (panelId === "map") {
    appendMapChromeMenuItems(items, prefs);
    items.push({ separator: true });
  }

  items.push({
    label: headerHidden ? "Show section header" : "Hide section header",
    action: () => setPanelHeaderHidden(panelId, !headerHidden),
  });

  const allHidden = DASHBOARD_PANEL_IDS.every((id) => prefs.hiddenHeaders.includes(id));
  items.push({
    label: allHidden ? "Show all section headers" : "Hide all section headers",
    action: () => setAllPanelHeadersHidden(!allHidden),
  });

  if (panelId === "log") {
    items.push({ separator: true });
    items.push({
      label: prefs.logTerminalOnly ? "Show log controls" : "Terminal only",
      action: () => setLogTerminalOnly(!prefs.logTerminalOnly),
    });
    items.push({
      label: logUiPaused ? "Resume log view" : "Pause log view",
      action: () => setLogPauseFromChrome(!logUiPaused),
    });
    items.push({
      label: logAutoscroll ? "✓ Auto-scroll" : "Auto-scroll",
      action: () => setLogAutoscrollFromChrome(!logAutoscroll),
    });
    items.push({
      label: "Clear log view",
      action: () => clearWebLogView(),
    });
    const logExpanded = document.body.classList.contains("dashboard-log-expanded");
    items.push({
      label: logExpanded ? "✓ Expand log (full screen)" : "Expand log (full screen)",
      action: () => setLogExpanded(!logExpanded),
    });
  }

  if (panelId === "status") {
    const cur = prefs.monitorLayout || "rows";
    items.push({ separator: true });
    items.push({
      label: "Expand all sections",
      action: () => expandAllMonitorSections(),
    });
    items.push({
      label: cur === "rows" ? "✓ Rows (metric tiles)" : "Rows (metric tiles)",
      action: () => setMonitorLayout("rows"),
    });
    items.push({
      label: cur === "columns" ? "✓ Columns (aligned table)" : "Columns (aligned table)",
      action: () => setMonitorLayout("columns"),
    });
    items.push({
      label: cur === "simple" ? "✓ Simple (state · transport · GNSS)" : "Simple (state · transport · GNSS)",
      action: () => setMonitorLayout("simple"),
    });
  }

  if (panelId === "com-setup") {
    items.push({ separator: true });
    items.push({
      label: "Refresh COM ports",
      action: () => refreshComPorts(),
    });
  }

  if (panelId === "discovery") {
    items.push({ separator: true });
    items.push({
      label: "Refresh discovery",
      action: () => refreshDiscovery(),
    });
  }

  if (panelId === "tools") {
    items.push({ separator: true });
    items.push({
      label: "Unlock ports",
      action: () => unlockPorts(),
    });
    items.push({
      label: "Copy setup link",
      action: () => copySetupLink(),
    });
  }

  if (isGridstackLayoutPage()) {
    items.push({ separator: true });
    items.push({
      label: prefs.hideResizeGrips ? "Show resize bars" : "Hide resize bars",
      action: () => setHideResizeGrips(!prefs.hideResizeGrips),
    });
  }

  return items;
}

function onDashboardContextMenu(e) {
  const inMenu = e.target.closest(".dashboard-chrome-menu");
  if (inMenu) return;

  const toggle = e.target.closest(".dashboard-panel-toggle");
  let panel = resolveChromePanelFromEvent(e);
  if (!panel && !toggle) return;

  const panelId = panel?.dataset?.panel;
  if (!panelId || !DASHBOARD_PANEL_IDS.includes(panelId)) return;

  e.preventDefault();
  e.stopPropagation();
  armChromeMenuCloseGuard();
  showChromeMenuAt(e.clientX, e.clientY, buildChromeMenuItems(panelId));
}

function onChromeMenuOutsidePointer(e) {
  if (!chromeMenuEl || chromeMenuEl.hidden) return;
  if (Date.now() < chromeMenuCloseGuardUntil) return;
  if (e.target.closest(".dashboard-chrome-menu")) return;
  if (e.target.closest(".panel-chrome-menu-btn, .panel-chrome-fab")) return;
  hideChromeMenu();
}

function initDashboardChromeMenus() {
  applyChromePrefs(loadChromePrefs());
  ensurePanelChromeMenuButtons();
  initChromeLongPress();
  document.addEventListener("contextmenu", onDashboardContextMenu, true);
  document.addEventListener("pointerdown", onChromeMenuOutsidePointer, true);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideChromeMenu();
  });
}

const MONITOR_COLLAPSE_KEY = "nmea-monitor-collapse";
const DASHBOARD_PANEL_COLLAPSE_KEY = "nmea-dashboard-panels";
const DASHBOARD_PANEL_ORDER_KEY = "nmea-dashboard-order";
const DASHBOARD_PANEL_DEFAULT_ORDER = [
  "com-setup",
  "status",
  "map",
  "configuration",
  "tools",
  "log",
  "discovery",
];

function initMonitorSections() {
  let saved = {};
  try {
    saved = JSON.parse(localStorage.getItem(MONITOR_COLLAPSE_KEY) || "{}");
  } catch (_) { /* ignore */ }

  const mobile = isCoarseMobile();
  const defaults = mobile
    ? { connection: true, rates: true, session: false, backpressure: false }
    : { connection: true, rates: true, session: true, backpressure: true };

  document.querySelectorAll(".monitor-section[data-section]").forEach((sec) => {
    const id = sec.dataset.section;
    const open = saved[id] !== undefined ? !!saved[id] : !!defaults[id];
    setMonitorSectionOpen(sec, open, false);
    const btn = sec.querySelector(".monitor-section-toggle");
    if (btn) {
      btn.addEventListener("click", () => {
        const nowOpen = !sec.classList.contains("monitor-section-open");
        setMonitorSectionOpen(sec, nowOpen, true);
      });
    }
  });
}

function setMonitorSectionOpen(section, open, persist) {
  const id = section.dataset.section;
  const btn = section.querySelector(".monitor-section-toggle");
  const panel = section.querySelector(".monitor-panel");
  const chev = section.querySelector(".monitor-chevron");
  section.classList.toggle("monitor-section-open", open);
  if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
  if (panel) panel.hidden = !open;
  if (chev) chev.textContent = open ? "▼" : "▶";
  if (persist && id) {
    let saved = {};
    try {
      saved = JSON.parse(localStorage.getItem(MONITOR_COLLAPSE_KEY) || "{}");
    } catch (_) { /* ignore */ }
    saved[id] = open;
    localStorage.setItem(MONITOR_COLLAPSE_KEY, JSON.stringify(saved));
  }
}

function updateDashboardPanelSummaries(status) {
  const com = status.com_port || "—";
  setEl("panel-sum-com-setup", com);
  setEl("com-setup-current", com);
  const qSel = document.getElementById("com-quick-select");
  if (qSel && com !== "—" && Array.from(qSel.options).some((o) => o.value === com)) {
    qSel.value = com;
  }
  setEl(
    "panel-sum-status",
    `${fmtHz(status.hz_net_to_com)} net→COM · ${com}`
  );
  setEl(
    "panel-sum-configuration",
    `${com} · ${status.udp_listen_port || ""}`
  );
  const logMeta = document.getElementById("log-meta");
  const logSum = logMeta ? logMeta.textContent : "";
  if (logSum) setEl("panel-sum-log", logSum);
}

function initDashboardPanels() {
  let saved = {};
  try {
    saved = JSON.parse(localStorage.getItem(DASHBOARD_PANEL_COLLAPSE_KEY) || "{}");
  } catch (_) { /* ignore */ }

  const mobile = isCoarseMobile();
  const defaults = mobile
    ? {
        "com-setup": true,
        status: true,
        configuration: false,
        tools: false,
        log: false,
        discovery: false,
      }
    : {
        "com-setup": true,
        status: true,
        configuration: true,
        tools: true,
        log: true,
        discovery: true,
      };

  document.querySelectorAll(".dashboard-panel[data-panel]").forEach((panel) => {
    const id = panel.dataset.panel;
    const open = saved[id] !== undefined ? !!saved[id] : !!defaults[id];
    setDashboardPanelOpen(panel, open, false);
    const btn = panel.querySelector(".dashboard-panel-toggle");
    if (btn) {
      btn.addEventListener("click", (e) => {
        if (e.target.closest(".panel-nudge-btn, .panel-chrome-menu-btn, .panel-chrome-fab")) return;
        const nowOpen = !panel.classList.contains("dashboard-panel-open");
        setDashboardPanelOpen(panel, nowOpen, true);
      });
    }
  });
  ensureDashboardReorderControls();
}

function loadDashboardPanelOrder() {
  try {
    const raw = JSON.parse(localStorage.getItem(DASHBOARD_PANEL_ORDER_KEY) || "[]");
    if (!Array.isArray(raw)) return [...DASHBOARD_PANEL_DEFAULT_ORDER];
    const known = new Set(DASHBOARD_PANEL_DEFAULT_ORDER);
    const order = raw.filter((id) => known.has(id) && id !== "control");
    DASHBOARD_PANEL_DEFAULT_ORDER.forEach((id) => {
      if (!order.includes(id)) order.push(id);
    });
    return order;
  } catch (_) {
    return [...DASHBOARD_PANEL_DEFAULT_ORDER];
  }
}

function saveDashboardPanelOrder(order) {
  localStorage.setItem(DASHBOARD_PANEL_ORDER_KEY, JSON.stringify(order));
}

function initDashboardPanelOrder() {
  if (isGridstackLayoutPage()) return;
  const root = document.getElementById("dashboard-panels");
  if (!root) return;
  const order = loadDashboardPanelOrder();
  order.forEach((id, index) => {
    const panel = root.querySelector(`.dashboard-panel[data-panel="${id}"]`);
    if (!panel) return;
    panel.style.order = String(index);
    root.appendChild(panel);
  });
}

function moveDashboardPanel(panelId, delta) {
  if (isGridstackLayoutPage() && isDashboardLayoutLocked()) return;
  const order = loadDashboardPanelOrder();
  const idx = order.indexOf(panelId);
  if (idx < 0) return;
  const next = idx + delta;
  if (next < 0 || next >= order.length) return;
  const otherId = order[next];
  order.splice(idx, 1);
  order.splice(next, 0, panelId);
  saveDashboardPanelOrder(order);
  if (isGridstackLayoutPage() && typeof window.swapGridstackTiles === "function") {
    window.swapGridstackTiles(panelId, otherId);
  } else {
    initDashboardPanelOrder();
  }
}

function ensureDashboardReorderControls() {
  document.querySelectorAll(".dashboard-panel[data-panel]").forEach((panel) => {
    const btn = panel.querySelector(".dashboard-panel-toggle");
    if (!btn) return;
    btn.querySelectorAll(".dashboard-drag-handle").forEach((el) => el.remove());
    if (btn.querySelector(".panel-nudge-group")) return;
    const id = panel.dataset.panel;
    const nudge = document.createElement("span");
    nudge.className = "panel-nudge-group";
    nudge.setAttribute("aria-label", "Reorder section");
    const up = document.createElement("button");
    up.type = "button";
    up.className = "panel-nudge-btn";
    up.textContent = "▲";
    up.title = "Move section up";
    const down = document.createElement("button");
    down.type = "button";
    down.className = "panel-nudge-btn";
    down.textContent = "▼";
    down.title = "Move section down";
    const nudgePanel = (e, delta) => {
      e.preventDefault();
      e.stopPropagation();
      moveDashboardPanel(id, delta);
    };
    up.addEventListener("click", (e) => nudgePanel(e, -1));
    down.addEventListener("click", (e) => nudgePanel(e, 1));
    nudge.append(up, down);
    const chev = btn.querySelector(".dashboard-chevron");
    if (chev) btn.insertBefore(nudge, chev);
    else btn.appendChild(nudge);
  });
}

function initDashboardPanelReorder() {
  ensureDashboardReorderControls();
  ensurePanelChromeMenuButtons();
}

async function refreshComPorts() {
  if (commandInFlight) return;
  if (!ensureCanMutate()) return;
  setCommandFlight(true);
  hideComAlerts();
  try {
    const { ok, body } = await apiFetch("/ports/refresh", { method: "POST" });
    if (!ok) {
      showComAlerts(extractApiError(body, "Port scan failed."), "error");
      return;
    }
    const disc = await apiFetch("/discovery");
    if (disc.ok) renderDiscovery(disc.body);
    showComAlerts(body.message || "Ports refreshed.", "ok");
  } catch (e) {
    showComAlerts("Network error: " + e.message, "error");
  } finally {
    setCommandFlight(false);
  }
}

function setDashboardPanelOpen(panel, open, persist) {
  const id = panel.dataset.panel;
  const btn = panel.querySelector(".dashboard-panel-toggle");
  const body = panel.querySelector(".dashboard-panel-body");
  const chev = panel.querySelector(".dashboard-chevron");
  panel.classList.toggle("dashboard-panel-open", open);
  if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
  if (body) body.hidden = !open;
  if (chev) chev.textContent = open ? "▼" : "▶";
  if (persist && id) {
    let saved = {};
    try {
      saved = JSON.parse(localStorage.getItem(DASHBOARD_PANEL_COLLAPSE_KEY) || "{}");
    } catch (_) { /* ignore */ }
    saved[id] = open;
    localStorage.setItem(DASHBOARD_PANEL_COLLAPSE_KEY, JSON.stringify(saved));
  }
  if (isGridstackLayoutPage() && typeof window.syncGridstackPanelCollapse === "function") {
    window.syncGridstackPanelCollapse(panel, open);
  }
}

function updateMonitorSummaries(status) {
  const run = status.running ? "running" : "stopped";
  setEl(
    "monitor-sum-connection",
    `${run} · ${status.com_port || "—"}`
  );
  setEl(
    "monitor-sum-rates",
    `${fmtHz(status.hz_net_to_com)} / ${fmtHz(status.hz_com_to_net)}`
  );
  const gnss = (status.gnss_summary || status.gnss_fix || "—").trim();
  setEl(
    "monitor-sum-session",
    `${fmtCount(status.lines_net_to_com)}→COM · ${gnss}`
  );
  const drops =
    Number(status.drops_net_to_com ?? 0) + Number(status.drops_com_to_net ?? 0);
  const q = Number(status.queue_net_to_com ?? 0);
  setEl(
    "monitor-sum-backpressure",
    drops > 0 ? `drops ${drops}` : q >= 12 ? `queue ${q}` : "OK"
  );
}

function coerceBaud(val) {
  const n = parseInt(String(val ?? DEFAULT_BAUD), 10);
  if (BAUD_PRESETS.includes(n)) return n;
  if (!Number.isFinite(n) || n <= 0) return DEFAULT_BAUD;
  return BAUD_PRESETS.reduce((best, p) =>
    Math.abs(p - n) < Math.abs(best - n) ? p : best
  );
}

function fmtCount(val) {
  const n = Number(val ?? 0);
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 10_000) return (n / 1000).toFixed(1) + "k";
  if (n >= 1000) return (n / 1000).toFixed(2) + "k";
  return String(n);
}

function formatNmeaModeDisplay(mode) {
  const m = String(mode ?? "").trim().toLowerCase();
  if (m === "passthrough") return "PassThru";
  if (m === "strict") return "Strict";
  if (m === "raw") return "Raw";
  const raw = String(mode ?? "").trim();
  return raw || "—";
}

function getMonitorLayoutMode() {
  const card = document.getElementById("status-card");
  if (!card) return "rows";
  for (const mode of MONITOR_LAYOUT_MODES) {
    if (card.classList.contains(`monitor-layout-${mode}`)) return mode;
  }
  return "rows";
}

function formatUdpBindDisplay(status) {
  const port =
    status.udp_listen_port != null && status.udp_listen_port !== ""
      ? String(status.udp_listen_port)
      : "";
  const host = (status.udp_listen_host || "").trim();
  if (getMonitorLayoutMode() === "simple") {
    return port || "—";
  }
  if (!host && !port) return "—";
  return `${host}:${port}`;
}

function syncMonitorFieldLabels(layout) {
  const mode = MONITOR_LAYOUT_MODES.includes(layout) ? layout : "rows";
  const simple = mode === "simple";
  const udpLabel = document.querySelector(".monitor-stat-udp .stat-label");
  if (udpLabel) udpLabel.textContent = simple ? "UDP port" : "UDP bind";
  const nmeaLabel = document.querySelector(".monitor-stat-nmea .stat-label");
  if (nmeaLabel) nmeaLabel.textContent = simple ? "NMEA" : "NMEA mode";
  const hzLabel = document.querySelector(".monitor-stat-hz-down .stat-label");
  if (hzLabel) hzLabel.textContent = simple ? "Hz → COM" : "Hz net→COM";
}

function markWarnStat(id, val) {
  const n = Number(val ?? 0);
  setEl(id, String(n));
  const el = document.getElementById(id);
  if (el) el.dataset.nonzero = n > 0 ? "true" : "false";
}

function markQueueStat(id, val) {
  const n = Number(val ?? 0);
  const el = document.getElementById(id);
  if (!el) return;
  el.dataset.nonzero = n >= 12 ? "true" : "false";
}

function setOffline() {
  connected = false;
  bridgeRunning = false;
  setConfigLocked(false);
  setConfigFormDisabled(true);
  const dot   = document.getElementById("conn-dot");
  const label = document.getElementById("conn-label");
  if (dot)   dot.className = "conn-dot offline";
  if (label) label.textContent = "Backend offline";

  const ob = document.getElementById("offline-banner");
  if (ob) ob.hidden = false;
  const sg = document.getElementById("status-grid");
  if (sg) sg.hidden = true;

  const badgeEl = document.getElementById("stat-state");
  if (badgeEl) { badgeEl.textContent = "offline"; badgeEl.className = "stat-value state-badge"; }
  updateHeaderStatusChip(null);
  lastDashboardStatus = null;
}

// ── Configuration form ────────────────────────────────────────────────────────
async function loadConfig() {
  try {
    const { ok, body } = await apiFetch("/config");
    if (!ok) return;
    bindConfigForm(body);
  } catch (_) { /* non-critical */ }
}

function bindConfigForm(cfg) {
  const comSel = document.getElementById("cfg-com-select");
  const baudSel = document.getElementById("cfg-baud-select");
  const modeSel = document.getElementById("cfg-netmode-select");
  const udpHost = document.getElementById("cfg-udp-host");
  const udpPort = document.getElementById("cfg-udp-port");
  const remHost = document.getElementById("cfg-remote-host");
  const remPort = document.getElementById("cfg-remote-port");
  const nmeaRo = document.getElementById("cfg-nmea-readonly");
  const quickSel = document.getElementById("com-quick-select");
  for (const sel of [comSel, quickSel]) {
    if (!sel || !cfg.com_port) continue;
    if (!Array.from(sel.options).some((o) => o.value === cfg.com_port)) {
      const opt = document.createElement("option");
      opt.value = cfg.com_port;
      opt.textContent = cfg.com_port;
      sel.appendChild(opt);
    }
    sel.value = cfg.com_port;
  }
  if (baudSel) baudSel.value = String(coerceBaud(cfg.baud));
  if (modeSel) modeSel.value = cfg.network_mode || "udp_listen";
  if (udpHost) udpHost.value = cfg.udp_listen_host || "0.0.0.0";
  if (udpPort) udpPort.value = cfg.udp_listen_port != null ? String(cfg.udp_listen_port) : "10110";
  if (remHost) remHost.value = cfg.remote_host || remHost.value || "192.168.1.100";
  if (remPort) remPort.value = cfg.remote_port != null ? String(cfg.remote_port) : remPort.value || "10110";
  if (nmeaRo) nmeaRo.textContent = cfg.nmea_mode || "—";
  updateConfigModeFields();
}

function updateConfigModeFields() {
  const modeSel = document.getElementById("cfg-netmode-select");
  const form = document.getElementById("config-form");
  if (!modeSel || !form) return;
  const mode = modeSel.value;
  form.className = "config-form mode-" + mode;
  const listenRows = form.querySelectorAll(".cfg-listen-only");
  const remoteRows = form.querySelectorAll(".cfg-remote-only");
  listenRows.forEach((el) => { el.hidden = mode !== "udp_listen"; });
  remoteRows.forEach((el) => { el.hidden = mode === "udp_listen"; });
  if (mode === "tcp_server") {
    const rh = document.getElementById("cfg-remote-host");
    if (rh) rh.hidden = true;
    const rhLabel = form.querySelector('label[for="cfg-remote-host"]');
    if (rhLabel) rhLabel.hidden = true;
  }
}

const CONFIG_FORM_CONTROL_IDS = [
  "cfg-com-select", "cfg-baud-select", "cfg-netmode-select",
  "cfg-udp-host", "cfg-udp-port", "cfg-remote-host", "cfg-remote-port",
  "btn-save-config", "com-quick-select", "btn-com-apply",
  "btn-refresh-quick", "btn-unlock-quick",
];

function setConfigFormDisabled(disabled) {
  CONFIG_FORM_CONTROL_IDS.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.disabled = disabled;
  });
}

function setConfigLocked(locked) {
  setConfigFormDisabled(locked);
  const banner = document.getElementById("config-lock-banner");
  if (banner) banner.hidden = !locked;
  const comBanner = document.getElementById("com-setup-lock-banner");
  if (comBanner) comBanner.hidden = !locked;
  syncSerialRowInteractivity();
  syncDiscoveryNetworkRowInteractivity();
}

function syncSerialRowInteractivity() {
  ["com-quick-serial-list", "serial-list"].forEach((listId) => {
    const list = document.getElementById(listId);
    if (!list) return;
    list.querySelectorAll(".device-row").forEach((row) => {
      row.style.pointerEvents = "";
      row.style.opacity = bridgeRunning ? "0.55" : "";
      row.classList.toggle("device-row-locked", bridgeRunning);
    });
  });
}

function syncDiscoveryNetworkRowInteractivity() {
  const nl = document.getElementById("network-list");
  if (!nl) return;
  nl.querySelectorAll(".device-row").forEach((row) => {
    row.style.pointerEvents = "";
    row.style.opacity = "";
    row.classList.toggle("device-row-net-live", bridgeRunning);
  });
}

async function applyComPort() {
  if (commandInFlight || bridgeRunning) {
    showAlert("com-setup-alert", "Stop the bridge before changing COM.", "warn");
    return;
  }
  if (!ensureCanMutate()) return;
  const port = document.getElementById("com-quick-select")?.value || "";
  if (!port) {
    showAlert("com-setup-alert", "Choose a COM port first.", "warn");
    return;
  }
  setCommandFlight(true);
  hideAlert("com-setup-alert");
  try {
    const { ok, body } = await apiFetch("/config", {
      method: "PATCH",
      body: JSON.stringify({ com_port: port }),
    });
    if (ok) {
      showAlert("com-setup-alert", `COM port set to ${port}.`, "ok");
      await loadConfig();
    } else {
      const detail = typeof body.detail === "object" ? body.detail : {};
      const cls = detail.error_code === "running_guard" ? "warn" : "error";
      showAlert("com-setup-alert", extractApiError(body, "COM update failed."), cls);
    }
  } catch (e) {
    showAlert("com-setup-alert", "Network error: " + e.message, "error");
  } finally {
    setCommandFlight(false);
  }
}

async function saveConfig() {
  if (commandInFlight || bridgeRunning) return;
  if (!ensureCanMutate()) return;
  setCommandFlight(true);
  hideAlert("config-alert");
  const patch = buildConfigPatch();
  try {
    const { ok, body } = await apiFetch("/config", {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
    if (ok) {
      showAlert("config-alert", "Configuration saved.", "ok");
      await loadConfig();
    } else {
      showAlert("config-alert", extractApiError(body, "Save failed."), "error");
    }
  } catch (e) {
    showAlert("config-alert", "Network error: " + e.message, "error");
  } finally {
    setCommandFlight(false);
  }
}

function buildConfigPatch() {
  const mode = document.getElementById("cfg-netmode-select")?.value || "udp_listen";
  const patch = {
    com_port: document.getElementById("cfg-com-select")?.value || "",
    baud: parseInt(document.getElementById("cfg-baud-input")?.value || "115200", 10),
    network_mode: mode,
    udp_listen_host: document.getElementById("cfg-udp-host")?.value || "0.0.0.0",
    udp_listen_port: parseInt(document.getElementById("cfg-udp-port")?.value || "10110", 10),
  };
  if (mode !== "udp_listen") {
    patch.remote_host = document.getElementById("cfg-remote-host")?.value || "";
    patch.remote_port = parseInt(document.getElementById("cfg-remote-port")?.value || "10110", 10);
  }
  return patch;
}

function populateComSelect(serials) {
  const ports = (serials || []).map((d) => d.port).filter(Boolean);
  ["cfg-com-select", "com-quick-select"].forEach((id) => {
    const comSel = document.getElementById(id);
    if (!comSel) return;
    const cur = comSel.value;
    comSel.innerHTML = "";
    if (!ports.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "(no ports — refresh)";
      comSel.appendChild(opt);
      return;
    }
    ports.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p;
      opt.textContent = p;
      comSel.appendChild(opt);
    });
    if (cur && ports.includes(cur)) comSel.value = cur;
  });
}

function renderSerialDeviceList(listId, devices) {
  const sl = document.getElementById(listId);
  if (!sl) return;
  if (!devices || devices.length === 0) {
    sl.innerHTML = '<div class="device-empty">No COM ports on the bridge PC. Plug in USB serial, then Refresh ports.</div>';
    return;
  }
  sl.innerHTML = devices.map(d => {
    const fromConfig = String(d.device_id || "").startsWith("config:");
    const desc = d.description || d.manufacturer || "";
    const extra = fromConfig ? " (saved setting)" : (d.match_keyword ? ` · ${d.match_keyword}` : "");
    return `
    <div class="device-row" data-device-id="${esc(d.device_id)}" data-com-port="${esc(d.port)}"
         title="${esc(desc)}">
      <span class="device-status-dot status-${esc(d.status)}"></span>
      <span class="device-info">
        <span class="device-port">${esc(d.port)}</span>
        <span class="device-desc">${esc(desc)}${esc(extra)}</span>
      </span>
      ${d.match_keyword && !fromConfig ? `<span class="device-keyword">${esc(d.match_keyword)}</span>` : ""}
      <button type="button" class="select-btn">Select</button>
    </div>`;
  }).join("");
  syncSerialRowInteractivity();
}

function onShowQrToggle(checked) {
  if (checked) localStorage.setItem(SHOW_QR_KEY, "1");
  else localStorage.removeItem(SHOW_QR_KEY);
  updateQrDisplay();
}

function updateQrDisplay() {
  const desktopOnly = document.getElementById("qr-desktop-only");
  const mobileQrHint = document.getElementById("token-mobile-qr-hint");
  const mobile = isCoarseMobile();
  if (mobile) {
    if (desktopOnly) desktopOnly.hidden = true;
    if (mobileQrHint) mobileQrHint.hidden = false;
    return;
  }
  if (mobileQrHint) mobileQrHint.hidden = true;
  if (desktopOnly) desktopOnly.hidden = false;
  const block = document.getElementById("qr-block");
  const img = document.getElementById("qr-image");
  const chk = document.getElementById("chk-show-qr");
  if (!block || !img || !chk) return;
  if (!chk.checked) {
    block.hidden = true;
    return;
  }
  block.hidden = false;
  const origin = encodeURIComponent(location.origin);
  img.src = `/token-qr?setup=1&base_url=${origin}&_=${Date.now()}`;
}

function ensureCanMutate(focusAlertId) {
  if ((tokenRequired || lanBind) && !token) {
    const msg =
      "Missing API token — on the PC use Tools → Phone → Copy phone setup link and open it on this device, or paste the token below.";
    showAlert("run-alert", msg, "warn");
    if (focusAlertId) showAlert(focusAlertId, msg, "warn");
    scrollAlertIntoView(focusAlertId || "run-alert");
    return false;
  }
  return true;
}

// ── Start / Stop ──────────────────────────────────────────────────────────────
async function startBridge() {
  if (commandInFlight) return;
  if (!ensureCanMutate()) return;
  setCommandFlight(true);
  hideAlert("run-alert");
  try {
    const { ok, body } = await apiFetch("/bridge/start", { method: "POST" });
    if (ok) {
      showAlert("run-alert", "Bridge started.", "ok");
    } else {
      showAlert("run-alert", extractApiError(body, "Start failed."), "error");
    }
    await loadConfig();
  } catch (e) {
    showAlert("run-alert", "Network error: " + e.message, "error");
  } finally {
    setCommandFlight(false);
  }
}

async function stopBridge() {
  if (commandInFlight) return;
  if (!ensureCanMutate()) return;
  setCommandFlight(true);
  hideAlert("run-alert");
  try {
    const { ok, body } = await apiFetch("/bridge/stop", { method: "POST" });
    if (ok) {
      showAlert("run-alert", "Bridge stopped.", "ok");
    } else {
      showAlert("run-alert", extractApiError(body, "Stop failed."), "error");
    }
  } catch (e) {
    showAlert("run-alert", "Network error: " + e.message, "error");
  } finally {
    setCommandFlight(false);
  }
}

// ── Unlock ports ──────────────────────────────────────────────────────────────
async function unlockPorts() {
  if (commandInFlight) return;
  if (!ensureCanMutate()) return;
  setCommandFlight(true);
  hideAlert("unlock-alert");
  hideComAlerts();
  try {
    const { ok, body } = await apiFetch("/ports/unlock", { method: "POST" });
    if (ok) {
      const msg = body.message || "Port check finished.";
      showAlert("unlock-alert", msg, "ok");
      showComAlerts(msg, "ok");
    } else {
      const err = extractApiError(body, "Unlock failed.");
      showAlert("unlock-alert", err, "error");
      showComAlerts(err, "error");
    }
  } catch (e) {
    const err = "Network error: " + e.message;
    showAlert("unlock-alert", err, "error");
    showComAlerts(err, "error");
  } finally {
    setCommandFlight(false);
  }
}

// ── Discovery: refresh + poll ─────────────────────────────────────────────────
async function refreshDiscovery() {
  if (commandInFlight) return;
  if (!ensureCanMutate()) return;
  setCommandFlight(true);
  hideAlert("discovery-alert");
  try {
    const { ok, body } = await apiFetch("/discovery/refresh", { method: "POST" });
    if (ok) {
      startDiscoveryPoll();
    } else {
      showAlert("discovery-alert", extractApiError(body, "Refresh failed."), "error");
    }
  } catch (e) {
    showAlert("discovery-alert", "Network error: " + e.message, "error");
  } finally {
    setCommandFlight(false);
  }
}

function startDiscoveryPoll() {
  stopDiscoveryPoll();
  discoveryScanning = true;
  discPollStart = Date.now();
  setScanBusy(true);
  discPollTimer = setInterval(pollDiscovery, DISC_POLL_MS);
}

function stopDiscoveryPoll() {
  if (discPollTimer) { clearInterval(discPollTimer); discPollTimer = null; }
  discoveryScanning = false;
  setScanBusy(false);
}

async function pollDiscovery() {
  if (Date.now() - discPollStart > DISC_TIMEOUT) {
    stopDiscoveryPoll();
    const facade = await apiFetch("/discovery");
    if (facade.ok) renderDiscovery(facade.body);
    showAlert(
      "discovery-alert",
      "Scan timed out (25 s). COM ports may still appear below; open Discovery again or use Refresh ports in COM & ports.",
      "warn"
    );
    return;
  }
  try {
    const { ok, body } = await apiFetch("/discovery");
    if (!ok) return;
    renderDiscovery(body);
    if (body.errors && body.errors.length) {
      showAlert("discovery-alert", body.errors.join(" · "), "warn");
    }
    if (!body.scan_busy) {
      stopDiscoveryPoll();
      if (body.serial_devices && body.serial_devices.length) {
        hideAlert("discovery-alert");
      }
    }
  } catch (_) { /* ignore transient errors during poll */ }
}

function serialDevicesForUi(payload) {
  const list = [...(payload.serial_devices || [])];
  const seen = new Set(list.map((d) => d.port));
  return list.filter((d) => d.port);
}

async function seedDiscoveryFromConfig() {
  try {
    const { ok, body } = await apiFetch("/config");
    if (!ok || !body.com_port) return [];
    const port = body.com_port.trim();
    if (!port) return [];
    return [{
      device_id: `config:${port}`,
      port,
      description: "Active on bridge (from config)",
      manufacturer: "",
      match_keyword: "",
      status: "available",
    }];
  } catch (_) {
    return [];
  }
}

async function renderDiscovery(payload) {
  lastDiscMono = payload.updated_mono;
  let serials = serialDevicesForUi(payload);
  if (!serials.length) {
    serials = await seedDiscoveryFromConfig();
  }
  populateComSelect(serials);
  renderSerialDeviceList("com-quick-serial-list", serials);
  renderSerialDeviceList("serial-list", serials);

  // Network cards
  const nl = document.getElementById("network-list");
  if (nl) {
    if (!payload.network_cards || payload.network_cards.length === 0) {
      nl.innerHTML = '<div class="device-empty">No network adapters found.</div>';
    } else {
      nl.innerHTML = payload.network_cards.map(c => `
        <div class="device-row" data-device-id="${esc(c.device_id)}" title="${c.host}:${c.port}">
          <span class="device-status-dot status-${esc(c.status)}"></span>
          <span class="device-info">
            <span class="device-port">${esc(c.label)}</span>
            <span class="device-desc">${esc(c.host)}:${c.port}
              ${c.peer_count ? ` · ${c.peer_count} peer(s)` : ""}
            </span>
          </span>
          <span class="device-keyword">${esc(c.mode_hint)}</span>
          <button type="button" class="select-btn">Select</button>
        </div>
      `).join("");
      syncDiscoveryNetworkRowInteractivity();
    }
  }
}

function initDeviceListClicks() {
  const root = document.getElementById("dashboard-panels");
  if (!root || root.dataset.deviceClickBound === "1") return;
  root.dataset.deviceClickBound = "1";
  root.addEventListener("click", (ev) => {
    const row = ev.target.closest(".device-row[data-device-id]");
    if (!row) return;

    const netList = document.getElementById("network-list");
    if (netList && netList.contains(row)) {
      selectNetwork(row.dataset.deviceId || "");
      return;
    }

    const comList = document.getElementById("com-quick-serial-list");
    const serialList = document.getElementById("serial-list");
    if ((comList && comList.contains(row)) || (serialList && serialList.contains(row))) {
      const port =
        row.dataset.comPort || row.querySelector(".device-port")?.textContent?.trim() || "";
      selectSerial(port, row.dataset.deviceId || "");
    }
  });
}

// ── Device selection → PATCH /config ─────────────────────────────────────────
function showComAlerts(message, type) {
  showAlert("com-setup-alert", message, type);
  showAlert("discovery-alert", message, type);
}

function hideComAlerts() {
  hideAlert("com-setup-alert");
  hideAlert("discovery-alert");
}

function previewComSelection(port, deviceId) {
  setEl("com-setup-current", port);
  const qSel = document.getElementById("com-quick-select");
  if (qSel) {
    if (!Array.from(qSel.options).some((o) => o.value === port)) {
      const opt = document.createElement("option");
      opt.value = port;
      opt.textContent = port;
      qSel.appendChild(opt);
    }
    qSel.value = port;
  }
  markActiveSerialDevice(deviceId || `config:${port}`);
}

async function selectSerial(port, deviceId) {
  if (commandInFlight) return;
  if (bridgeRunning) {
    showComAlerts("Stop the bridge before changing COM.", "warn");
    scrollAlertIntoView("com-setup-alert");
    return;
  }
  if (!ensureCanMutate("com-setup-alert")) return;
  setCommandFlight(true);
  hideComAlerts();
  const patch = { com_port: port };
  const id = String(deviceId || "");
  if (id && !id.startsWith("config:")) patch.hub_device_id = id;
  try {
    const { ok, body } = await apiFetch("/config", {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
    if (ok) {
      previewComSelection(port, id || `config:${port}`);
      showComAlerts(`COM port set to ${port}.`, "ok");
      await loadConfig();
      scrollAlertIntoView("com-setup-alert");
    } else {
      const detail = typeof body.detail === "object" ? body.detail : {};
      const cls = detail.error_code === "running_guard" ? "warn" : "error";
      showComAlerts(extractApiError(body, "Config update failed."), cls);
    }
  } catch (e) {
    showComAlerts("Network error: " + e.message, "error");
  } finally {
    setCommandFlight(false);
  }
}

function markActiveSerialDevice(deviceId) {
  ["com-quick-serial-list", "serial-list"].forEach((id) => markActiveDevice(id, deviceId));
}

async function selectNetwork(deviceId) {
  const id = String(deviceId || "").trim();
  if (!id) return;
  if (commandInFlight) return;
  if (!ensureCanMutate("discovery-alert")) return;
  setCommandFlight(true);
  hideAlert("discovery-alert");
  try {
    const { ok, body } = await apiFetch("/config", {
      method: "PATCH",
      body: JSON.stringify({ hub_device_id: id }),
    });
    if (ok) {
      const msg = bridgeRunning
        ? "Network bind updated (bridge still running)."
        : "Network bind updated on the bridge PC.";
      showAlert("discovery-alert", msg, "ok");
      scrollAlertIntoView("discovery-alert");
      await loadConfig();
      markActiveDevice("network-list", id);
    } else {
      const detail = typeof body.detail === "object" ? body.detail : {};
      const cls = detail.error_code === "running_guard" ? "warn" : "error";
      showAlert("discovery-alert", extractApiError(body, "Config update failed."), cls);
      scrollAlertIntoView("discovery-alert");
    }
  } catch (e) {
    showAlert("discovery-alert", "Network error: " + e.message, "error");
    scrollAlertIntoView("discovery-alert");
  } finally {
    setCommandFlight(false);
  }
}

window.selectNetwork = selectNetwork;
window.selectSerial = selectSerial;

function markActiveDevice(listId, deviceId) {
  const list = document.getElementById(listId);
  if (!list) return;
  list.querySelectorAll(".device-row").forEach(row => {
    row.classList.toggle("active", row.dataset.deviceId === deviceId);
  });
}

// ── Command in-flight helpers ─────────────────────────────────────────────────
function setCommandFlight(on) {
  commandInFlight = on;
  const ids = [
    "btn-start", "btn-stop", "btn-unlock", "btn-refresh",
    "btn-refresh-quick", "btn-unlock-quick", "btn-com-apply",
  ];
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = on;
  });
}

// ── Scan busy indicator ───────────────────────────────────────────────────────
function setScanBusy(busy) {
  ["scan-spinner", "scan-spinner-quick"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.hidden = !busy;
  });
  ["btn-refresh", "btn-refresh-quick"].forEach((id) => {
    const btn = document.getElementById(id);
    if (btn) btn.disabled = busy || commandInFlight;
  });
}

// ── Alert helpers ─────────────────────────────────────────────────────────────
function showAlert(id, message, type = "info") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.className = `inline-alert alert-${type}`;
  el.hidden = false;
}

function scrollAlertIntoView(id) {
  const el = document.getElementById(id);
  if (el && !el.hidden) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function hideAlert(id) {
  const el = document.getElementById(id);
  if (el) el.hidden = true;
}

// ── DOM helpers ───────────────────────────────────────────────────────────────
function setEl(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setBadgeClass(id, state) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `stat-value state-badge ${state}`;
}

function fmtHz(val) {
  if (val == null) return "—";
  return Number(val).toFixed(1) + " Hz";
}

function esc(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ── Live log (Terminal or Table layout) ───────────────────────────────────────
const LOG_VIEW_KEY = "nmea-bridge-log-view";
const LOG_FILTER_KEY = "nmea-bridge-log-filter";
const LOG_NMEA_TYPES_KEY = "nmea-bridge-log-nmea-types";
const LOG_SENTENCE_KEY = "nmea-bridge-log-sentence";
const LOG_TEXT_KEY = "nmea-bridge-log-text";
const LOG_EXPAND_KEY = "nmea-bridge-log-expand";
const NMEA_SENTENCE_TYPES = [
  "GGA", "RMC", "ZDA", "VTG", "GSA", "GSV", "GLL", "HDT", "HDG", "DPT", "DTM", "GBS", "GST",
];
const LOG_POLL_MS = 1000;
const LOG_MAX_LOCAL = 600;

let logSeq = 0;
let logLines = [];
let logBaseMono = null;
let logViewMode = localStorage.getItem(LOG_VIEW_KEY) || "stream";
let logFilter = localStorage.getItem(LOG_FILTER_KEY) || "all";
let logNmeaFilterAll = true;
let logNmeaSelectedTypes = new Set();
let logNmeaDialogDraft = new Set();
let logNmeaMenuOpen = false;
let logUiPaused = false;
let logAutoscroll = true;

function initWebLog() {
  document.querySelectorAll(".log-view-tab").forEach((btn) => {
    btn.addEventListener("click", () => setLogViewMode(btn.dataset.view || "stream"));
  });
  setLogViewMode(logViewMode, false);
  const filt = document.getElementById("log-filter");
  if (filt) filt.value = logFilter;
  loadLogNmeaFilterState();
  initLogNmeaFilterUi();
  initLogExpand();
  pollLogs();
  setInterval(pollLogs, LOG_POLL_MS);
}

function initLogExpand() {
  const chk = document.getElementById("log-expand");
  const restored = localStorage.getItem(LOG_EXPAND_KEY) === "1";
  if (chk) chk.checked = restored;
  if (restored) setLogExpanded(true, false);

  const logToggle = document.getElementById("panel-toggle-log");
  if (logToggle) {
    logToggle.addEventListener(
      "click",
      (e) => {
        if (!document.body.classList.contains("dashboard-log-expanded")) return;
        e.stopImmediatePropagation();
        setLogExpanded(false);
      },
      true
    );
  }
}

function setLogExpanded(expanded, persist = true) {
  document.body.classList.toggle("dashboard-log-expanded", expanded);
  const chk = document.getElementById("log-expand");
  if (chk) chk.checked = expanded;
  const logCard = document.getElementById("log-card");
  if (expanded && logCard) {
    setDashboardPanelOpen(logCard, true, false);
  }
  if (persist) {
    if (expanded) localStorage.setItem(LOG_EXPAND_KEY, "1");
    else localStorage.removeItem(LOG_EXPAND_KEY);
  }
  requestAnimationFrame(() => {
    renderWebLog(true);
    scrollLogToEnd();
  });
}

function onLogExpandChange(checked) {
  setLogExpanded(!!checked);
}

function loadLogNmeaFilterState() {
  try {
    const raw = JSON.parse(localStorage.getItem(LOG_NMEA_TYPES_KEY) || "null");
    if (raw && typeof raw === "object") {
      if (raw.all === true || !raw.types || !raw.types.length) {
        logNmeaFilterAll = true;
        logNmeaSelectedTypes = new Set();
        return;
      }
      logNmeaFilterAll = false;
      logNmeaSelectedTypes = new Set(
        raw.types.map((t) => String(t).trim().toUpperCase()).filter(Boolean)
      );
      return;
    }
  } catch (_) { /* ignore */ }
  const legacy = (localStorage.getItem(LOG_SENTENCE_KEY) || "all").trim();
  if (legacy === "all" || !legacy) {
    logNmeaFilterAll = true;
    logNmeaSelectedTypes = new Set();
    return;
  }
  if (legacy === "custom") {
    const text = (localStorage.getItem(LOG_TEXT_KEY) || "").trim();
    const parts = text.split(/[,\s+]+/).map((p) => p.toUpperCase()).filter((p) => NMEA_SENTENCE_TYPES.includes(p));
    if (parts.length) {
      logNmeaFilterAll = false;
      logNmeaSelectedTypes = new Set(parts);
      return;
    }
  }
  if (NMEA_SENTENCE_TYPES.includes(legacy.toUpperCase())) {
    logNmeaFilterAll = false;
    logNmeaSelectedTypes = new Set([legacy.toUpperCase()]);
    return;
  }
  logNmeaFilterAll = true;
  logNmeaSelectedTypes = new Set();
}

function saveLogNmeaFilterState() {
  if (logNmeaFilterAll || logNmeaSelectedTypes.size === 0) {
    localStorage.setItem(LOG_NMEA_TYPES_KEY, JSON.stringify({ all: true, types: [] }));
  } else {
    localStorage.setItem(
      LOG_NMEA_TYPES_KEY,
      JSON.stringify({ all: false, types: [...logNmeaSelectedTypes].sort() })
    );
  }
  updateLogNmeaFilterLabel();
}

function logNmeaFilterLabelText() {
  if (logNmeaFilterAll || logNmeaSelectedTypes.size === 0) return "All NMEA";
  const arr = [...logNmeaSelectedTypes].sort();
  if (arr.length <= 3) return arr.join(" + ");
  return `${arr.length} types`;
}

function updateLogNmeaFilterLabel() {
  const el = document.getElementById("log-nmea-filter-label");
  if (el) el.textContent = logNmeaFilterLabelText();
  syncLogNmeaMenuSelection();
}

function lineMatchesNmeaTypes(text) {
  if (!text) return false;
  for (const ty of logNmeaSelectedTypes) {
    if (new RegExp(`\\$[A-Z]{2}${ty}\\b`, "i").test(text)) return true;
  }
  return false;
}

function logMatchesNmeaFilter(entry) {
  if (logNmeaFilterAll || logNmeaSelectedTypes.size === 0) return true;
  return lineMatchesNmeaTypes(entry.text || "");
}

function persistLogNmeaFilterAndRender() {
  saveLogNmeaFilterState();
  renderWebLog(true);
}

function initLogNmeaFilterUi() {
  updateLogNmeaFilterLabel();
  buildLogNmeaMenu();
  buildLogNmeaDialogGrid();
  document.addEventListener("click", (e) => {
    if (!logNmeaMenuOpen) return;
    if (e.target.closest(".log-nmea-filter-wrap")) return;
    closeLogNmeaMenu();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeLogNmeaMenu();
      closeLogNmeaDialog(false);
    }
  });
  const backdrop = document.getElementById("log-nmea-dialog-backdrop");
  if (backdrop) {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) closeLogNmeaDialog(false);
    });
  }
}

function buildLogNmeaMenu() {
  const menu = document.getElementById("log-nmea-menu");
  if (!menu) return;
  const items = [
    { id: "all", label: "All NMEA" },
    ...NMEA_SENTENCE_TYPES.map((t) => ({ id: t, label: t })),
    { id: "__custom", label: "Custom…", divider: true },
  ];
  menu.innerHTML = "";
  items.forEach((item) => {
    if (item.divider) {
      const div = document.createElement("div");
      div.className = "log-nmea-menu-divider";
      menu.appendChild(div);
    }
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "log-nmea-menu-item";
    btn.role = "option";
    btn.dataset.type = item.id;
    btn.textContent = item.label;
    btn.addEventListener("click", (e) => onLogNmeaMenuPick(e, item.id));
    menu.appendChild(btn);
  });
  syncLogNmeaMenuSelection();
}

function syncLogNmeaMenuSelection() {
  const menu = document.getElementById("log-nmea-menu");
  if (!menu) return;
  menu.querySelectorAll(".log-nmea-menu-item").forEach((btn) => {
    const id = btn.dataset.type;
    let on = false;
    if (id === "all") on = logNmeaFilterAll;
    else if (id !== "__custom") on = !logNmeaFilterAll && logNmeaSelectedTypes.has(id);
    btn.classList.toggle("is-selected", on);
  });
}

function toggleLogNmeaMenu(e) {
  e.stopPropagation();
  if (logNmeaMenuOpen) closeLogNmeaMenu();
  else openLogNmeaMenu();
}

function openLogNmeaMenu() {
  const menu = document.getElementById("log-nmea-menu");
  const btn = document.getElementById("log-nmea-filter-btn");
  if (!menu || !btn) return;
  menu.hidden = false;
  btn.setAttribute("aria-expanded", "true");
  logNmeaMenuOpen = true;
  syncLogNmeaMenuSelection();
}

function closeLogNmeaMenu() {
  const menu = document.getElementById("log-nmea-menu");
  const btn = document.getElementById("log-nmea-filter-btn");
  if (menu) menu.hidden = true;
  if (btn) btn.setAttribute("aria-expanded", "false");
  logNmeaMenuOpen = false;
}

function onLogNmeaMenuPick(e, typeId) {
  e.stopPropagation();
  if (typeId === "__custom") {
    closeLogNmeaMenu();
    openLogNmeaDialog();
    return;
  }
  if (typeId === "all") {
    logNmeaFilterAll = true;
    logNmeaSelectedTypes = new Set();
    closeLogNmeaMenu();
    persistLogNmeaFilterAndRender();
    return;
  }
  if (e.shiftKey) {
    logNmeaFilterAll = false;
    if (logNmeaSelectedTypes.has(typeId)) {
      logNmeaSelectedTypes.delete(typeId);
      if (logNmeaSelectedTypes.size === 0) logNmeaFilterAll = true;
    } else {
      logNmeaSelectedTypes.add(typeId);
    }
  } else {
    logNmeaFilterAll = false;
    logNmeaSelectedTypes = new Set([typeId]);
    closeLogNmeaMenu();
  }
  persistLogNmeaFilterAndRender();
  if (e.shiftKey) syncLogNmeaMenuSelection();
}

function buildLogNmeaDialogGrid() {
  const grid = document.getElementById("log-nmea-dialog-grid");
  if (!grid) return;
  grid.innerHTML = "";
  NMEA_SENTENCE_TYPES.forEach((ty) => {
    const lbl = document.createElement("label");
    lbl.className = "log-nmea-type-chk";
    const inp = document.createElement("input");
    inp.type = "checkbox";
    inp.value = ty;
    inp.dataset.type = ty;
    inp.addEventListener("change", updateLogNmeaDialogSummary);
    lbl.append(inp, document.createTextNode(ty));
    grid.appendChild(lbl);
  });
}

function openLogNmeaDialog() {
  logNmeaDialogDraft = logNmeaFilterAll ? new Set() : new Set(logNmeaSelectedTypes);
  const grid = document.getElementById("log-nmea-dialog-grid");
  if (grid) {
    grid.querySelectorAll("input[type=checkbox]").forEach((inp) => {
      inp.checked = logNmeaDialogDraft.has(inp.dataset.type);
    });
  }
  updateLogNmeaDialogSummary();
  const backdrop = document.getElementById("log-nmea-dialog-backdrop");
  if (backdrop) backdrop.hidden = false;
}

function closeLogNmeaDialog(apply) {
  const backdrop = document.getElementById("log-nmea-dialog-backdrop");
  if (backdrop) backdrop.hidden = true;
  if (apply) {
    const grid = document.getElementById("log-nmea-dialog-grid");
    const picked = new Set();
    if (grid) {
      grid.querySelectorAll("input[type=checkbox]:checked").forEach((inp) => {
        picked.add(inp.dataset.type);
      });
    }
    if (!picked.size) {
      logNmeaFilterAll = true;
      logNmeaSelectedTypes = new Set();
    } else {
      logNmeaFilterAll = false;
      logNmeaSelectedTypes = picked;
    }
    persistLogNmeaFilterAndRender();
  }
}

function applyLogNmeaPreset(preset) {
  const grid = document.getElementById("log-nmea-dialog-grid");
  if (!grid) return;
  let types = new Set();
  if (preset === "survey") types = new Set(["GGA", "RMC"]);
  else if (preset === "all") types = new Set(NMEA_SENTENCE_TYPES);
  grid.querySelectorAll("input[type=checkbox]").forEach((inp) => {
    inp.checked = preset === "all" ? true : types.has(inp.dataset.type);
  });
  updateLogNmeaDialogSummary();
}

function applyLogNmeaDialogClear() {
  const grid = document.getElementById("log-nmea-dialog-grid");
  if (grid) {
    grid.querySelectorAll("input[type=checkbox]").forEach((inp) => {
      inp.checked = false;
    });
  }
  updateLogNmeaDialogSummary();
}

function updateLogNmeaDialogSummary() {
  const grid = document.getElementById("log-nmea-dialog-grid");
  const sum = document.getElementById("log-nmea-dialog-summary");
  if (!grid || !sum) return;
  const picked = [];
  grid.querySelectorAll("input[type=checkbox]:checked").forEach((inp) => {
    picked.push(inp.dataset.type);
  });
  picked.sort();
  if (!picked.length) sum.textContent = "No types selected — shows all lines when you click OK.";
  else if (picked.length === NMEA_SENTENCE_TYPES.length) sum.textContent = "All sentence types selected.";
  else sum.textContent = `Showing lines containing: ${picked.join(", ")}`;
}

function setLogViewMode(mode, persist = true) {
  logViewMode = mode === "table" ? "table" : "stream";
  if (persist) localStorage.setItem(LOG_VIEW_KEY, logViewMode);
  document.querySelectorAll(".log-view-tab").forEach((btn) => {
    const on = btn.dataset.view === logViewMode;
    btn.classList.toggle("is-active", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  });
  const panel = document.getElementById("log-panel");
  if (panel) {
    panel.dataset.view = logViewMode;
    panel.className = `log-panel log-view-${logViewMode}`;
    delete panel.dataset.built;
  }
  renderWebLog(true);
}

function logMatchesFilter(entry) {
  if (logFilter !== "all" && entry.kind !== logFilter) return false;
  return logMatchesNmeaFilter(entry);
}

function formatLogOffset(mono) {
  if (logBaseMono == null) return "0.000";
  const s = Math.max(0, mono - logBaseMono);
  const whole = Math.floor(s);
  const ms = Math.floor((s - whole) * 1000);
  return `${String(whole).padStart(4, " ")}.${String(ms).padStart(3, "0")}`;
}

function kindLabel(kind) {
  if (kind === "traffic") return "Traffic";
  if (kind === "warn") return "Warn";
  if (kind === "event") return "Event";
  return "Info";
}

function lineHtmlStream(e) {
  return `<div class="log-line log-kind-${e.kind}" data-seq="${e.seq}"><span class="log-line-text">${esc(e.text)}</span></div>`;
}

function lineHtmlTable(e) {
  return (
    `<tr data-seq="${e.seq}">` +
    `<td class="log-col-time mono">${formatLogOffset(e.mono)}</td>` +
    `<td class="log-col-kind kind-${e.kind}">${kindLabel(e.kind)}</td>` +
    `<td class="log-col-msg">${esc(e.text)}</td></tr>`
  );
}

function scrollLogToEnd() {
  if (!logAutoscroll || logUiPaused) return;
  const panel = document.getElementById("log-panel");
  if (panel) panel.scrollTop = panel.scrollHeight;
}

function updateLogMeta(serverPaused = false, serverDropped = 0) {
  const meta = document.getElementById("log-meta");
  const foot = document.getElementById("log-footnote");
  const n = logLines.length;
  const filt = logLines.filter(logMatchesFilter).length;
  if (meta) {
    let s = `${n} line${n === 1 ? "" : "s"}`;
    if (logFilter !== "all" || !logNmeaFilterAll) s += ` · ${filt} shown`;
    if (logUiPaused) s += " · view paused";
    if (serverPaused) s += " · app log paused";
    meta.textContent = s;
  }
  if (foot && serverPaused && serverDropped > 0) {
    foot.textContent = `Desktop log paused — ${serverDropped} line(s) skipped on the app.`;
  } else if (foot) {
    foot.textContent = "Mirrors the desktop live log; kind and NMEA filters apply in this browser only.";
  }
}

function renderWebLog(forceRebuild = false) {
  const panel = document.getElementById("log-panel");
  if (!panel) return;
  if (logUiPaused && !forceRebuild) {
    updateLogMeta();
    return;
  }
  const rows = logLines.filter(logMatchesFilter);
  panel.dataset.built = "1";
  if (!rows.length) {
    panel.innerHTML = '<div class="log-empty">No log lines yet — start the bridge or change the filter.</div>';
    updateLogMeta();
    return;
  }
  if (logViewMode === "stream") {
    panel.innerHTML = rows.map((e) => lineHtmlStream(e)).join("");
  } else {
    panel.innerHTML =
      `<table class="log-table"><thead><tr><th>Δt</th><th>Kind</th><th>Message</th></tr></thead><tbody>${rows.map((e) => lineHtmlTable(e)).join("")}</tbody></table>`;
  }
  scrollLogToEnd();
  updateLogMeta();
}

function appendWebLogLines(incoming, serverPaused, serverDropped) {
  if (!incoming.length) {
    updateLogMeta(serverPaused, serverDropped);
    return;
  }
  if (logBaseMono == null) logBaseMono = incoming[0].mono;
  logLines.push(...incoming);
  while (logLines.length > LOG_MAX_LOCAL) {
    logLines.shift();
    logBaseMono = logLines.length ? logLines[0].mono : null;
  }
  if (logUiPaused) {
    updateLogMeta(serverPaused, serverDropped);
    return;
  }
  const panel = document.getElementById("log-panel");
  if (!panel) return;
  const filtered = incoming.filter(logMatchesFilter);
  if (logViewMode === "stream") {
    const empty = panel.querySelector(".log-empty");
    if (empty) panel.innerHTML = "";
    filtered.forEach((e) => {
      const div = document.createElement("div");
      div.className = `log-line log-kind-${e.kind}`;
      div.dataset.seq = String(e.seq);
      const span = document.createElement("span");
      span.className = "log-line-text";
      span.textContent = e.text;
      div.appendChild(span);
      panel.appendChild(div);
    });
    scrollLogToEnd();
    updateLogMeta(serverPaused, serverDropped);
    return;
  }
  renderWebLog(true);
  updateLogMeta(serverPaused, serverDropped);
}

async function pollLogs() {
  try {
    const { ok, body } = await apiFetch(`/logs?after=${logSeq}&limit=200`);
    if (!ok || !body) return;
    const lines = body.lines || [];
    if (lines.length) {
      logSeq = Math.max(logSeq, ...lines.map((ln) => ln.seq || 0));
      appendWebLogLines(lines, !!body.paused, body.paused_dropped || 0);
    } else {
      updateLogMeta(!!body.paused, body.paused_dropped || 0);
    }
  } catch (_) { /* non-critical */ }
}

function onLogFilterChange(val) {
  logFilter = val || "all";
  localStorage.setItem(LOG_FILTER_KEY, logFilter);
  renderWebLog(true);
}

function onLogAutoscrollChange(checked) {
  logAutoscroll = !!checked;
  scrollLogToEnd();
}

function onLogUiPauseChange(checked) {
  logUiPaused = !!checked;
  if (!logUiPaused) renderWebLog(true);
  updateLogMeta();
}

function clearWebLogView() {
  logLines = [];
  logBaseMono = null;
  const panel = document.getElementById("log-panel");
  if (panel) {
    delete panel.dataset.built;
    panel.innerHTML = '<div class="log-empty">View cleared — new lines will appear on the next poll.</div>';
  }
  updateLogMeta();
}

// ── Position map (GGA/RMC via /status; Survey HUD may share bridge.navigation_position()) ──
let mapInstance = null;
let mapStreetLayer = null;
let mapSatelliteLayer = null;
let mapMarker = null;
let mapTrackLine = null;
let mapTrackPoints = [];
let mapTilesOk = true;

function loadMapBaseLayer() {
  try {
    const prefs = loadChromePrefs();
    if (prefs.mapBaseLayer === "satellite") return "satellite";
  } catch (_) {
    /* ignore */
  }
  const saved = localStorage.getItem(MAP_BASE_LAYER_KEY);
  return saved === "satellite" ? "satellite" : "street";
}

function saveMapBaseLayer(mode) {
  const clean = mode === "satellite" ? "satellite" : "street";
  localStorage.setItem(MAP_BASE_LAYER_KEY, clean);
  const prefs = loadChromePrefs();
  prefs.mapBaseLayer = clean;
  saveChromePrefs(prefs);
}

function syncMapAttributionText(mode) {
  const attr = document.getElementById("map-attribution");
  if (!attr) return;
  if (mode === "satellite") {
    attr.innerHTML =
      'Imagery © <a href="https://www.esri.com/" target="_blank" rel="noopener">Esri</a> · ' +
      "Labels © Esri";
  } else {
    attr.innerHTML =
      '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors';
  }
}

function _wireMapTileErrors(layer) {
  layer.on("tileerror", () => {
    mapTilesOk = false;
    const note = document.getElementById("map-offline-note");
    if (note) note.hidden = false;
  });
}

function setMapBaseLayer(mode) {
  ensureBridgeMap();
  if (!mapInstance || !mapStreetLayer || !mapSatelliteLayer) return;
  const wantSat = mode === "satellite";
  if (wantSat) {
    if (mapInstance.hasLayer(mapStreetLayer)) mapInstance.removeLayer(mapStreetLayer);
    if (!mapInstance.hasLayer(mapSatelliteLayer)) mapSatelliteLayer.addTo(mapInstance);
  } else {
    if (mapInstance.hasLayer(mapSatelliteLayer)) mapInstance.removeLayer(mapSatelliteLayer);
    if (!mapInstance.hasLayer(mapStreetLayer)) mapStreetLayer.addTo(mapInstance);
  }
  saveMapBaseLayer(wantSat ? "satellite" : "street");
  syncMapAttributionText(wantSat ? "satellite" : "street");
  invalidateDashboardMap();
}

function initPositionMap() {
  const chk = document.getElementById("map-enabled");
  if (!chk) return;
  const saved = localStorage.getItem(MAP_ENABLED_KEY);
  chk.checked = saved === "1";
  chk.addEventListener("change", () => {
    localStorage.setItem(MAP_ENABLED_KEY, chk.checked ? "1" : "0");
    syncMapVisibility();
    if (chk.checked) {
      ensureBridgeMap();
      setTimeout(() => mapInstance?.invalidateSize(), 120);
    }
  });
  syncMapVisibility();
}

function syncMapVisibility() {
  const chk = document.getElementById("map-enabled");
  const frame = document.getElementById("map-frame");
  const attr = document.getElementById("map-attribution");
  const on = !!(chk && chk.checked);
  if (frame) frame.hidden = !on;
  if (attr) attr.hidden = !on;
  const sum = document.getElementById("panel-sum-map");
  if (sum && !on) sum.textContent = "Off";
  if (on) {
    ensureBridgeMap();
    requestAnimationFrame(() => {
      mapInstance?.invalidateSize();
    });
  }
}

function ensureBridgeMap() {
  if (mapInstance || typeof L === "undefined") return;
  const host = document.getElementById("bridge-map");
  if (!host) return;
  L.Icon.Default.mergeOptions({
    iconUrl: "/static/vendor/leaflet/marker-icon.png",
    iconRetinaUrl: "/static/vendor/leaflet/marker-icon-2x.png",
    shadowUrl: "/static/vendor/leaflet/marker-shadow.png",
  });
  mapInstance = L.map(host, { zoomControl: true, attributionControl: true });

  mapStreetLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  });
  _wireMapTileErrors(mapStreetLayer);

  const satImagery = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19, attribution: "&copy; Esri" }
  );
  const satLabels = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19, attribution: "&copy; Esri" }
  );
  _wireMapTileErrors(satImagery);
  _wireMapTileErrors(satLabels);
  mapSatelliteLayer = L.layerGroup([satImagery, satLabels]);

  const base = loadMapBaseLayer();
  if (base === "satellite") mapSatelliteLayer.addTo(mapInstance);
  else mapStreetLayer.addTo(mapInstance);
  syncMapAttributionText(base);

  mapMarker = L.circleMarker([0, 0], {
    radius: 9,
    weight: 2,
    color: "#e2e8f0",
    fillColor: "#60a5fa",
    fillOpacity: 0.85,
  }).addTo(mapInstance);
  mapTrackLine = L.polyline([], {
    color: "#60a5fa",
    weight: 3,
    opacity: 0.65,
  });
  syncMapTrackVisibility(loadChromePrefs().mapShowTrack !== false);
  mapInstance.setView([20, 0], 2);
}

function invalidateDashboardMap() {
  mapInstance?.invalidateSize();
}

function positionFixColor(status) {
  if (!status || status.position_stale || status.gnss_stream_idle) return "#f87171";
  const q = status.gnss_quality;
  if (q === 4 || q === 5) return "#4ade80";
  if (q === 1 || q === 2) return "#60a5fa";
  return "#fbbf24";
}

function fmtPositionSummary(status) {
  const lat = status?.position_lat;
  const lon = status?.position_lon;
  if (lat == null || lon == null) return "No fix";
  const stale = status.position_stale || status.gnss_stream_idle;
  const src = (status.position_source || "").toUpperCase();
  const fix = (status.gnss_fix || status.gnss_summary || "").trim();
  const core = `${Number(lat).toFixed(5)}, ${Number(lon).toFixed(5)}`;
  const bits = [core];
  if (src) bits.push(src);
  if (fix && fix !== "No Data Stream") bits.push(fix);
  if (stale) bits.push("stale");
  return bits.join(" · ");
}

function updatePositionMap(status) {
  const coords = document.getElementById("map-coords");
  const chk = document.getElementById("map-enabled");
  const sum = document.getElementById("panel-sum-map");
  if (!status) {
    if (coords) coords.textContent = "Offline";
    if (sum) sum.textContent = "—";
    return;
  }
  const text = fmtPositionSummary(status);
  if (coords) coords.textContent = text;
  if (sum && chk?.checked) sum.textContent = text;

  if (!chk?.checked) return;
  ensureBridgeMap();
  if (!mapInstance || !mapMarker) return;

  const lat = status.position_lat;
  const lon = status.position_lon;
  const hasFix =
    lat != null &&
    lon != null &&
    !status.gnss_stream_idle &&
    Number.isFinite(Number(lat)) &&
    Number.isFinite(Number(lon));

  if (!hasFix) return;

  const ll = [Number(lat), Number(lon)];
  const stale = !!status.position_stale;
  const color = positionFixColor(status);
  mapMarker.setLatLng(ll);
  mapMarker.setStyle({
    fillColor: color,
    color: stale ? "#8b93a8" : "#e2e8f0",
    fillOpacity: stale ? 0.45 : 0.9,
  });

  const showTrack = loadChromePrefs().mapShowTrack !== false;
  if (showTrack && mapTrackLine) {
    const last = mapTrackPoints[mapTrackPoints.length - 1];
    if (
      !last ||
      Math.abs(last[0] - ll[0]) > 1e-7 ||
      Math.abs(last[1] - ll[1]) > 1e-7
    ) {
      mapTrackPoints.push(ll);
      if (mapTrackPoints.length > MAP_TRACK_MAX) {
        mapTrackPoints = mapTrackPoints.slice(-MAP_TRACK_MAX);
      }
      mapTrackLine.setLatLngs(mapTrackPoints);
    }
  }

  const zoom = stale ? Math.min(mapInstance.getZoom(), 14) : 16;
  if (mapTrackPoints.length < 2) {
    mapInstance.setView(ll, zoom, { animate: false });
  } else if (!stale) {
    mapInstance.panTo(ll, { animate: true, duration: 0.35 });
  }
}

window.invalidateDashboardMap = invalidateDashboardMap;
window.appendMapChromeMenuItems = appendMapChromeMenuItems;
window.nmeaGetDashboardStatus = () => lastDashboardStatus;
window.DASHBOARD_SCRIPT_REV = DASHBOARD_SCRIPT_REV;

// ── Kick-off ──────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", init);
