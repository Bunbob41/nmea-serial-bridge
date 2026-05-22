/**
 * NMEA Bridge Dashboard — vanilla ES6
 * No frameworks. No NMEA/socket logic. REST only.
 * Covers: US1 telemetry, US2 start/stop, US3 unlock, US4 discovery + COM picker.
 */

// ── Constants ─────────────────────────────────────────────────────────────────
const TOKEN_KEY     = "nmea-bridge-web-token";
const SHOW_QR_KEY   = "nmea-bridge-show-qr";
const POLL_INTERVAL = 1000;           // status poll ms
const DISC_POLL_MS  = 500;            // discovery poll after refresh
const DISC_TIMEOUT  = 15_000;         // stop discovery poll after 15 s

// ── Session state ─────────────────────────────────────────────────────────────
let connected         = false;
let commandInFlight   = false;
let discoveryScanning = false;
let discPollTimer     = null;
let discPollStart     = 0;
let lastDiscMono      = 0;
let token             = localStorage.getItem(TOKEN_KEY) || "";
let tokenRequired     = false;
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

function parseTokenFromText(text) {
  const s = (text || "").trim();
  if (!s) return null;
  if (s.includes("bridge-token=")) {
    const frag = s.includes("#") ? s.split("#", 1)[1] : s;
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

async function copyToClipboard(text) {
  if (!text) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (_) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (_) { /* ignore */ }
    document.body.removeChild(ta);
    return ok;
  }
}

async function copyTokenToClipboard() {
  const t = (document.getElementById("token-input")?.value || token || "").trim();
  if (!t) {
    showAlert("run-alert", "No token to copy.", "warn");
    return;
  }
  if (await copyToClipboard(t)) showAlert("run-alert", "Token copied.", "ok");
}

async function copySetupLink() {
  const t = (document.getElementById("token-input")?.value || token || "").trim();
  if (!t) {
    showAlert("run-alert", "Paste or save a token first.", "warn");
    return;
  }
  const url = buildSetupUrl(location.origin, t);
  if (await copyToClipboard(url)) {
    showAlert(
      "run-alert",
      "Setup link copied — paste on the other device (Paste setup link) or open once in a browser.",
      "ok"
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
        title: "NMEA Bridge dashboard",
        text: "Open to save API token",
        url,
      });
      showAlert("run-alert", "Share the link to your PC (email, Teams, etc.), then Paste setup link in Tools → Guide.", "ok");
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
      "<strong>To PC:</strong> Copy setup link or Share link → on the survey PC open Tools → Guide → <strong>Paste setup link</strong>. " +
      "<strong>From PC:</strong> open the link the PC copied, or Paste setup link here.";
  } else {
    body.innerHTML =
      "<strong>To phone:</strong> Copy setup link here → open on the phone once (or Paste setup link in phone Tools). " +
      "<strong>From phone:</strong> Copy/Share setup link on the phone → <strong>Paste setup link</strong> here and in Tools → Guide on the PC app.";
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
  initWebLog();
  startStatusPoll();
}

// ── Meta / version ────────────────────────────────────────────────────────────
async function loadMeta() {
  try {
    const { ok, body } = await apiFetch("/meta");
    if (!ok) return;
    // version tag
    const vt = document.getElementById("ver-tag");
    if (vt) vt.textContent = body.version || "";
    // token settings visibility
    tokenRequired = !!body.token_required;
    const ts = document.getElementById("token-section");
    if (ts) ts.hidden = !tokenRequired;
    if (tokenRequired) {
      const inp = document.getElementById("token-input");
      if (inp) inp.value = token;
      if (!token) {
        const msg = isCoarseMobile()
          ? "LAN mode: get a setup link from the PC (Tools → Guide → Copy phone setup link) and open it here, or Paste setup link below."
          : "LAN mode: use Copy setup link / Paste setup link below, or Tools → Guide on the PC app.";
        showAlert("run-alert", msg, "warn");
      }
    }
    if (body.commands_ready === false) {
      showAlert(
        "run-alert",
        "Desktop bridge window not linked to the web API — fully quit and restart the NMEA Bridge app (need v1.8.2+), then hard-refresh this page (Ctrl+F5).",
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

  // state badge
  setEl("stat-state",   status.running ? "running" : "stopped");
  setBadgeClass("stat-state", status.running ? "running" : "stopped");
  // fields
  setEl("stat-com",     status.com_port   || "—");
  setEl("stat-baud",    status.baud       != null ? String(status.baud) : "—");
  setEl("stat-udp",     `${status.udp_listen_host || ""}:${status.udp_listen_port || ""}`);
  setEl("stat-nmea",    status.nmea_mode  || "—");
  setEl("stat-hz-down", fmtHz(status.hz_net_to_com));
  setEl("stat-hz-up",   fmtHz(status.hz_com_to_net));

  const drops   = Number(status.drops   ?? 0);
  const rejects = Number(status.rejects ?? 0);
  setEl("stat-drops",   String(drops));
  setEl("stat-rejects", String(rejects));
  const dEl = document.getElementById("stat-drops");
  const rEl = document.getElementById("stat-rejects");
  if (dEl) dEl.dataset.nonzero = drops   > 0 ? "true" : "false";
  if (rEl) rEl.dataset.nonzero = rejects > 0 ? "true" : "false";
}

function setOffline() {
  connected = false;
  bridgeRunning = false;
  setConfigLocked(true);
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
  const baudIn = document.getElementById("cfg-baud-input");
  const modeSel = document.getElementById("cfg-netmode-select");
  const udpHost = document.getElementById("cfg-udp-host");
  const udpPort = document.getElementById("cfg-udp-port");
  const remHost = document.getElementById("cfg-remote-host");
  const remPort = document.getElementById("cfg-remote-port");
  const nmeaRo = document.getElementById("cfg-nmea-readonly");
  if (comSel && cfg.com_port) {
    if (!Array.from(comSel.options).some((o) => o.value === cfg.com_port)) {
      const opt = document.createElement("option");
      opt.value = cfg.com_port;
      opt.textContent = cfg.com_port;
      comSel.appendChild(opt);
    }
    comSel.value = cfg.com_port;
  }
  if (baudIn) baudIn.value = cfg.baud != null ? String(cfg.baud) : "115200";
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

function setConfigLocked(locked) {
  const banner = document.getElementById("config-lock-banner");
  const ids = [
    "cfg-com-select", "cfg-baud-input", "cfg-netmode-select",
    "cfg-udp-host", "cfg-udp-port", "cfg-remote-host", "cfg-remote-port",
    "btn-save-config",
  ];
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.disabled = locked;
  });
  if (banner) banner.hidden = !locked;
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
  const comSel = document.getElementById("cfg-com-select");
  if (!comSel) return;
  const cur = comSel.value;
  comSel.innerHTML = "";
  const ports = (serials || []).map((d) => d.port).filter(Boolean);
  if (!ports.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(no ports — refresh discovery)";
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

function ensureCanMutate() {
  if (tokenRequired && !token) {
    showAlert(
      "run-alert",
      "Missing API token — on the PC use Tools → Guide → Copy phone setup link and open it on this device, or paste the token in Tools below.",
      "warn"
    );
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
  try {
    const { ok, body } = await apiFetch("/ports/unlock", { method: "POST" });
    if (ok) {
      showAlert("unlock-alert", body.message || "Ports unlocked.", "ok");
    } else {
      showAlert("unlock-alert", extractApiError(body, "Unlock failed."), "error");
    }
  } catch (e) {
    showAlert("unlock-alert", "Network error: " + e.message, "error");
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
    showAlert("discovery-alert", "Scan timed out (15 s). Check hardware connections.", "warn");
    return;
  }
  try {
    const { ok, body } = await apiFetch("/discovery");
    if (!ok) return;
    renderDiscovery(body);
    if (!body.scan_busy) {
      stopDiscoveryPoll();
    }
  } catch (_) { /* ignore transient errors during poll */ }
}

function renderDiscovery(payload) {
  lastDiscMono = payload.updated_mono;
  populateComSelect(payload.serial_devices);

  // Serial devices
  const sl = document.getElementById("serial-list");
  if (sl) {
    if (!payload.serial_devices || payload.serial_devices.length === 0) {
      sl.innerHTML = '<div class="device-empty">No serial ports found.</div>';
    } else {
      sl.innerHTML = payload.serial_devices.map(d => `
        <div class="device-row" onclick="selectSerial(${JSON.stringify(d.port)}, ${JSON.stringify(d.device_id)})"
             data-device-id="${esc(d.device_id)}" title="${esc(d.description)}">
          <span class="device-status-dot status-${esc(d.status)}"></span>
          <span class="device-info">
            <span class="device-port">${esc(d.port)}</span>
            <span class="device-desc">${esc(d.description || d.manufacturer || "")}</span>
          </span>
          ${d.match_keyword ? `<span class="device-keyword">${esc(d.match_keyword)}</span>` : ""}
          <button class="select-btn" onclick="event.stopPropagation(); selectSerial(${JSON.stringify(d.port)}, ${JSON.stringify(d.device_id)})">Select</button>
        </div>
      `).join("");
    }
  }

  // Network cards
  const nl = document.getElementById("network-list");
  if (nl) {
    if (!payload.network_cards || payload.network_cards.length === 0) {
      nl.innerHTML = '<div class="device-empty">No network adapters found.</div>';
    } else {
      nl.innerHTML = payload.network_cards.map(c => `
        <div class="device-row" onclick="selectNetwork(${JSON.stringify(c.device_id)})"
             data-device-id="${esc(c.device_id)}" title="${c.host}:${c.port}">
          <span class="device-status-dot status-${esc(c.status)}"></span>
          <span class="device-info">
            <span class="device-port">${esc(c.label)}</span>
            <span class="device-desc">${esc(c.host)}:${c.port}
              ${c.peer_count ? ` · ${c.peer_count} peer(s)` : ""}
            </span>
          </span>
          <span class="device-keyword">${esc(c.mode_hint)}</span>
          <button class="select-btn" onclick="event.stopPropagation(); selectNetwork(${JSON.stringify(c.device_id)})">Select</button>
        </div>
      `).join("");
    }
  }
}

// ── Device selection → PATCH /config ─────────────────────────────────────────
async function selectSerial(port, deviceId) {
  if (commandInFlight) return;
  setCommandFlight(true);
  hideAlert("discovery-alert");
  try {
    const { ok, body } = await apiFetch("/config", {
      method: "PATCH",
      body: JSON.stringify({ com_port: port, hub_device_id: deviceId }),
    });
    if (ok) {
      showAlert("discovery-alert", `COM port set to ${port}.`, "ok");
      await loadConfig();
      markActiveDevice("serial-list", deviceId);
    } else {
      const detail = typeof body.detail === "object" ? body.detail : {};
      const cls = detail.error_code === "running_guard" ? "warn" : "error";
      showAlert("discovery-alert", extractApiError(body, "Config update failed."), cls);
    }
  } catch (e) {
    showAlert("discovery-alert", "Network error: " + e.message, "error");
  } finally {
    setCommandFlight(false);
  }
}

async function selectNetwork(deviceId) {
  if (commandInFlight) return;
  setCommandFlight(true);
  hideAlert("discovery-alert");
  try {
    const { ok, body } = await apiFetch("/config", {
      method: "PATCH",
      body: JSON.stringify({ hub_device_id: deviceId }),
    });
    if (ok) {
      showAlert("discovery-alert", "Network adapter selected.", "ok");
      await loadConfig();
      markActiveDevice("network-list", deviceId);
    } else {
      const detail = typeof body.detail === "object" ? body.detail : {};
      const cls = detail.error_code === "running_guard" ? "warn" : "error";
      showAlert("discovery-alert", extractApiError(body, "Config update failed."), cls);
    }
  } catch (e) {
    showAlert("discovery-alert", "Network error: " + e.message, "error");
  } finally {
    setCommandFlight(false);
  }
}

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
  const ids = ["btn-start", "btn-stop", "btn-unlock", "btn-refresh"];
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = on;
  });
}

// ── Scan busy indicator ───────────────────────────────────────────────────────
function setScanBusy(busy) {
  const spinner = document.getElementById("scan-spinner");
  if (spinner) spinner.hidden = !busy;
  const btn = document.getElementById("btn-refresh");
  if (btn) btn.disabled = busy || commandInFlight;
}

// ── Alert helpers ─────────────────────────────────────────────────────────────
function showAlert(id, message, type = "info") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.className = `inline-alert alert-${type}`;
  el.hidden = false;
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

// ── Live log (trial layouts: stream / feed / table) ───────────────────────────
const LOG_VIEW_KEY = "nmea-bridge-log-view";
const LOG_FILTER_KEY = "nmea-bridge-log-filter";
const LOG_POLL_MS = 1000;
const LOG_MAX_LOCAL = 600;

let logSeq = 0;
let logLines = [];
let logBaseMono = null;
let logViewMode = localStorage.getItem(LOG_VIEW_KEY) || "stream";
let logFilter = localStorage.getItem(LOG_FILTER_KEY) || "all";
let logUiPaused = false;
let logAutoscroll = true;

function initWebLog() {
  document.querySelectorAll(".log-view-tab").forEach((btn) => {
    btn.addEventListener("click", () => setLogViewMode(btn.dataset.view || "stream"));
  });
  setLogViewMode(logViewMode, false);
  const filt = document.getElementById("log-filter");
  if (filt) filt.value = logFilter;
  pollLogs();
  setInterval(pollLogs, LOG_POLL_MS);
}

function setLogViewMode(mode, persist = true) {
  logViewMode = mode || "stream";
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
  if (logFilter === "all") return true;
  return entry.kind === logFilter;
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

function lineHtmlFeed(e) {
  return (
    `<article class="log-feed-item log-kind-${e.kind}" data-seq="${e.seq}">` +
    `<span class="log-feed-accent" aria-hidden="true"></span>` +
    `<div class="log-feed-body"><span class="log-feed-kind">${kindLabel(e.kind)}</span>` +
    `<pre class="log-feed-text">${esc(e.text)}</pre></div></article>`
  );
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
    if (logFilter !== "all") s += ` · ${filt} shown`;
    if (logUiPaused) s += " · view paused";
    if (serverPaused) s += " · app log paused";
    meta.textContent = s;
  }
  if (foot && serverPaused && serverDropped > 0) {
    foot.textContent = `Desktop log paused — ${serverDropped} line(s) skipped on the app.`;
  } else if (foot) {
    foot.textContent = "Mirrors the desktop live log (same filters as the app).";
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
  } else if (logViewMode === "feed") {
    panel.innerHTML = rows.map((e) => lineHtmlFeed(e)).join("");
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

// ── Kick-off ──────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", init);
