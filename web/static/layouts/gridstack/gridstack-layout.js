/** GridStack beta — drag/resize, ▲▼ reorder (swap tiles), collapse shrink. */
const GRIDSTACK_LAYOUT_KEY = "nmea-gridstack-layout-v2";
const GRIDSTACK_LAYOUT_LOCK_KEY = "nmea-dashboard-layout-locked";
const GRIDSTACK_COLLAPSED_ROWS = 1;

const GRIDSTACK_DEFAULT_LAYOUT = [
  { id: "com-setup", x: 0, y: 0, w: 6, h: 4 },
  { id: "status", x: 6, y: 0, w: 6, h: 5 },
  { id: "map", x: 0, y: 5, w: 6, h: 4 },
  { id: "configuration", x: 6, y: 5, w: 6, h: 4 },
  { id: "tools", x: 0, y: 9, w: 4, h: 4 },
  { id: "discovery", x: 4, y: 9, w: 8, h: 4 },
  { id: "log", x: 0, y: 13, w: 12, h: 6 },
];

/** @type {Record<string, number>} */
const gridstackExpandedHeights = Object.fromEntries(
  GRIDSTACK_DEFAULT_LAYOUT.map((n) => [n.id, n.h])
);

let gridstackGrid = null;
const GRIDSTACK_CELL_HEIGHT = 80;
const GRIDSTACK_MARGIN = 10;

function gridstackRowStepPx() {
  if (gridstackGrid && typeof gridstackGrid.getCellHeight === "function") {
    const ch = gridstackGrid.getCellHeight();
    const m =
      typeof gridstackGrid.getMargin === "function"
        ? gridstackGrid.getMargin()
        : GRIDSTACK_MARGIN;
    if (typeof ch === "number" && ch > 0) {
      return ch + (typeof m === "number" ? m : GRIDSTACK_MARGIN);
    }
  }
  return GRIDSTACK_CELL_HEIGHT + GRIDSTACK_MARGIN;
}

function gridstackColStepPx(root) {
  if (!root) return 80;
  const w = root.getBoundingClientRect().width;
  const cols = gridstackGrid?.getColumn?.() || 12;
  return w / cols;
}

function defaultLayoutEntry(id) {
  return GRIDSTACK_DEFAULT_LAYOUT.find((n) => n.id === id);
}

function rememberExpandedHeight(id, h) {
  if (h > GRIDSTACK_COLLAPSED_ROWS) {
    gridstackExpandedHeights[id] = h;
  }
}

function layoutForStorage() {
  if (!gridstackGrid) return [];
  return gridstackGrid.save(false).map((node) => {
    const id = node.id || node.el?.getAttribute?.("gs-id");
    const panel = node.el?.querySelector?.(".dashboard-panel");
    const collapsed =
      panel && !panel.classList.contains("dashboard-panel-open");
    const h =
      collapsed && id && gridstackExpandedHeights[id]
        ? gridstackExpandedHeights[id]
        : node.h;
    if (id && h > GRIDSTACK_COLLAPSED_ROWS) {
      gridstackExpandedHeights[id] = h;
    }
    return { id, x: node.x, y: node.y, w: node.w, h };
  });
}

function persistGridstackLayout() {
  try {
    localStorage.setItem(GRIDSTACK_LAYOUT_KEY, JSON.stringify(layoutForStorage()));
  } catch (_) {
    /* ignore quota */
  }
}

function gridstackNodeForId(id) {
  if (!gridstackGrid) return { item: null, node: null };
  const root = document.querySelector(".grid-stack#dashboard-panels");
  const item = root?.querySelector(`.grid-stack-item[gs-id="${id}"]`);
  if (!item) return { item: null, node: null };
  const nodes = gridstackGrid.engine.nodes || [];
  const node = nodes.find((n) => n.el === item || n.id === id);
  return { item, node };
}

/** Exchange tile position/size (▲▼ nudge on grid layout). */
function swapGridstackTiles(idA, idB) {
  if (!gridstackGrid || !idA || !idB || idA === idB) return;
  const a = gridstackNodeForId(idA);
  const b = gridstackNodeForId(idB);
  if (!a.item || !b.item || !a.node || !b.node) return;
  const posA = { x: a.node.x, y: a.node.y, w: a.node.w, h: a.node.h };
  const posB = { x: b.node.x, y: b.node.y, w: b.node.w, h: b.node.h };
  gridstackGrid.update(a.item, posB);
  gridstackGrid.update(b.item, posA);
  persistGridstackLayout();
  window.setTimeout(() => {
    if (
      (idA === "map" || idB === "map") &&
      typeof window.invalidateDashboardMap === "function"
    ) {
      window.invalidateDashboardMap();
    }
  }, 120);
}

function syncGridstackPanelCollapse(panel, open) {
  if (!gridstackGrid || !panel) return;
  const item = panel.closest(".grid-stack-item");
  if (!item) return;
  const id = item.getAttribute("gs-id") || panel.dataset.panel;
  if (!id) return;

  const nodes = gridstackGrid.engine.nodes || [];
  const node = nodes.find((n) => n.el === item || n.id === id);
  if (!node) return;

  if (open) {
    const h =
      gridstackExpandedHeights[id] ||
      (node.h > GRIDSTACK_COLLAPSED_ROWS ? node.h : null) ||
      defaultLayoutEntry(id)?.h ||
      3;
    gridstackGrid.update(item, { h });
    rememberExpandedHeight(id, h);
  } else {
    if (node.h > GRIDSTACK_COLLAPSED_ROWS) {
      rememberExpandedHeight(id, node.h);
    }
    gridstackGrid.update(item, { h: GRIDSTACK_COLLAPSED_ROWS });
  }
  window.setTimeout(() => {
    if (id === "map" && typeof window.invalidateDashboardMap === "function") {
      window.invalidateDashboardMap();
    }
  }, 120);
}

function applyGridstackCollapseFromSavedPanels() {
  document.querySelectorAll(".dashboard-panel[data-panel]").forEach((panel) => {
    if (!panel.classList.contains("dashboard-panel-open")) {
      syncGridstackPanelCollapse(panel, false);
    }
  });
}

function bindGridstackResizeGrip(item, grip, mode, root) {
  let startX = 0;
  let startY = 0;
  let startH = 0;
  let startW = 0;
  let startXGrid = 0;
  let pointerId = null;

  const endDrag = () => {
    grip.removeEventListener("pointermove", onPointerMove);
    grip.removeEventListener("pointerup", endDrag);
    grip.removeEventListener("pointercancel", endDrag);
    pointerId = null;
    item.classList.remove("grid-tile-resizing");
    if (gridstackGrid.setAnimation) gridstackGrid.setAnimation(true);
    persistGridstackLayout();
    const id = item.getAttribute("gs-id");
    if (id === "map" && typeof window.invalidateDashboardMap === "function") {
      window.invalidateDashboardMap();
    }
  };

  const onPointerMove = (e) => {
    if (pointerId == null || e.pointerId !== pointerId) return;
    e.preventDefault();
    const node = gridstackGrid.engine.nodes.find((n) => n.el === item);
    if (!node) return;
    const id = item.getAttribute("gs-id");
    const colStep = gridstackColStepPx(root);

    if (mode === "h") {
      const deltaRows = Math.round((e.clientY - startY) / gridstackRowStepPx());
      const newH = Math.max(
        GRIDSTACK_COLLAPSED_ROWS,
        Math.min(24, startH + deltaRows)
      );
      if (id) rememberExpandedHeight(id, newH);
      gridstackGrid.update(item, { h: newH });
    } else if (mode === "e") {
      const deltaCols = Math.round((e.clientX - startX) / colStep);
      const newW = Math.max(2, Math.min(12, startW + deltaCols));
      gridstackGrid.update(item, { w: newW });
    } else if (mode === "w") {
      const deltaCols = Math.round((startX - e.clientX) / colStep);
      const newW = Math.max(2, Math.min(12, startW + deltaCols));
      let newX = startXGrid + (startW - newW);
      newX = Math.max(0, Math.min(12 - newW, newX));
      gridstackGrid.update(item, { x: newX, w: newW });
    }
  };

  const onPointerDown = (e) => {
    if (isGridstackLayoutLocked()) return;
    if (pointerId != null) return;
    const node = gridstackGrid.engine.nodes.find((n) => n.el === item);
    if (!node) return;
    e.preventDefault();
    e.stopPropagation();
    pointerId = e.pointerId;
    if (grip.setPointerCapture) grip.setPointerCapture(pointerId);
    startX = e.clientX;
    startY = e.clientY;
    startH = node.h;
    startW = node.w;
    startXGrid = node.x;
    item.classList.add("grid-tile-resizing");
    if (gridstackGrid.setAnimation) gridstackGrid.setAnimation(false);
    grip.addEventListener("pointermove", onPointerMove);
    grip.addEventListener("pointerup", endDrag);
    grip.addEventListener("pointercancel", endDrag);
  };

  grip.addEventListener("pointerdown", onPointerDown);
}

function appendGridstackResizeGrip(item, className, mode, label, title, root) {
  if (item.querySelector(`.${className}`)) return;
  const grip = document.createElement("div");
  grip.className = `grid-tile-resize-grip ${className}`;
  grip.setAttribute("role", "separator");
  grip.setAttribute("aria-label", label);
  grip.title = title;
  bindGridstackResizeGrip(item, grip, mode, root);
  item.appendChild(grip);
}

/** Touch resize bars (bottom + left/right edges). */
function installGridstackTouchResizeGrips(root) {
  if (!root || !gridstackGrid) return;

  root.querySelectorAll(".grid-stack-item").forEach((item) => {
    appendGridstackResizeGrip(
      item,
      "grid-tile-resize-grip-h",
      "h",
      "Drag to resize height",
      "Drag up/down to resize",
      root
    );
    appendGridstackResizeGrip(
      item,
      "grid-tile-resize-grip-e",
      "e",
      "Drag to resize width from right",
      "Drag to resize width (right edge)",
      root
    );
    appendGridstackResizeGrip(
      item,
      "grid-tile-resize-grip-w",
      "w",
      "Drag to resize width from left",
      "Drag to resize width (left edge)",
      root
    );
  });
}

function isGridstackLayoutLocked() {
  return localStorage.getItem(GRIDSTACK_LAYOUT_LOCK_KEY) === "1";
}

function applyGridstackLayoutLock(locked) {
  document.body.classList.toggle("layout-gridstack-locked", !!locked);
  const chk = document.getElementById("layout-lock");
  if (chk && chk.checked !== locked) chk.checked = locked;
  if (!gridstackGrid) return;
  if (locked) {
    persistGridstackLayout();
    gridstackGrid.disable();
  } else {
    gridstackGrid.enable();
  }
}

/** Drop legacy top banner (cached HTML may still include it after CSS was updated). */
function removeLegacyLayoutBanner() {
  document.querySelectorAll(".layout-beta-banner").forEach((el) => el.remove());
}

function initGridstackDashboard() {
  removeLegacyLayoutBanner();
  const root = document.querySelector(".grid-stack#dashboard-panels");
  if (!root || typeof GridStack === "undefined") {
    console.warn("[gridstack] GridStack not available");
    return;
  }

  gridstackGrid = GridStack.init(
    {
      column: 12,
      cellHeight: 80,
      margin: 10,
      float: false,
      animate: true,
      /* iPhone has no hover — must show handles always (default "mobile" autohide breaks resize) */
      alwaysShowResizeHandle: true,
      draggable: {
        handle:
          ".dashboard-panel-toggle, .dashboard-panel.chrome-header-hidden",
        cancel:
          ".panel-nudge-btn, .panel-nudge-group, .panel-chrome-menu-btn, .panel-chrome-fab, .grid-tile-resize-grip, .dashboard-chrome-menu, .dashboard-chrome-menu-item",
      },
      resizable: {
        handles: "se, s, e",
        autoHide: false,
      },
    },
    root
  );

  const applyDefaultLayout = () => {
    GRIDSTACK_DEFAULT_LAYOUT.forEach((n) => {
      gridstackExpandedHeights[n.id] = n.h;
    });
    gridstackGrid.load(GRIDSTACK_DEFAULT_LAYOUT, true);
    applyGridstackCollapseFromSavedPanels();
    persistGridstackLayout();
  };

  let usedSaved = false;
  try {
    const raw = localStorage.getItem(GRIDSTACK_LAYOUT_KEY);
    if (raw) {
      const layout = JSON.parse(raw);
      if (Array.isArray(layout) && layout.length) {
        layout.forEach((n) => {
          if (n.id && n.h > GRIDSTACK_COLLAPSED_ROWS) {
            gridstackExpandedHeights[n.id] = n.h;
          }
        });
        gridstackGrid.load(layout, true);
        usedSaved = true;
      }
    }
  } catch (_) {
    /* ignore corrupt layout */
  }
  if (!usedSaved) {
    applyDefaultLayout();
  } else {
    applyGridstackCollapseFromSavedPanels();
  }

  installGridstackTouchResizeGrips(root);
  applyGridstackLayoutLock(isGridstackLayoutLocked());

  gridstackGrid.on("change", () => {
    persistGridstackLayout();
  });

  gridstackGrid.on("resizestop", (_e, el) => {
    const id = el.getAttribute("gs-id");
    const nodes = gridstackGrid.engine.nodes || [];
    const node = nodes.find((n) => n.el === el);
    if (id && node) rememberExpandedHeight(id, node.h);
  });

  const resetBtn = document.getElementById("btn-gridstack-reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      localStorage.removeItem(GRIDSTACK_LAYOUT_KEY);
      localStorage.removeItem("nmea-gridstack-layout-v1");
      applyDefaultLayout();
      installGridstackTouchResizeGrips(root);
    });
  }
}

window.initGridstackDashboard = initGridstackDashboard;
window.syncGridstackPanelCollapse = syncGridstackPanelCollapse;
window.swapGridstackTiles = swapGridstackTiles;
window.applyGridstackLayoutLock = applyGridstackLayoutLock;

/** Inject map ⋯ items when an older cached dashboard.js is still loaded (frozen zip / browser cache). */
function patchGridstackMapChromeMenu() {
  if (typeof buildChromeMenuItems !== "function") return;
  if (buildChromeMenuItems.__gridMapChromePatch) return;
  const orig = buildChromeMenuItems;
  window.buildChromeMenuItems = function (panelId) {
    const items = orig(panelId);
    if (panelId !== "map") return items;
    if (items.some((it) => it && it.label === "Center on fix")) return items;
    const head = [];
    if (typeof window.appendMapChromeMenuItems === "function" && typeof loadChromePrefs === "function") {
      window.appendMapChromeMenuItems(head, loadChromePrefs());
    } else {
      gridstackMapChromeMenuFallback(head);
    }
    return head.concat([{ separator: true }], items);
  };
  window.buildChromeMenuItems.__gridMapChromePatch = true;
}

function gridstackMapChromeMenuFallback(items) {
  const prefs =
    typeof loadChromePrefs === "function"
      ? loadChromePrefs()
      : { mapShowTrack: true, mapPrioritized: false };
  const mapOn = !!document.getElementById("map-enabled")?.checked;
  const status =
    typeof window.nmeaGetDashboardStatus === "function"
      ? window.nmeaGetDashboardStatus()
      : null;
  const hasFix =
    status &&
    !status.gnss_stream_idle &&
    status.position_lat != null &&
    status.position_lon != null;
  const trackLen =
    typeof mapTrackPoints !== "undefined" && Array.isArray(mapTrackPoints)
      ? mapTrackPoints.length
      : 0;

  items.push({
    label: mapOn ? "✓ Show map" : "Show map",
    action: () => {
      const chk = document.getElementById("map-enabled");
      if (!chk) return;
      chk.checked = !chk.checked;
      chk.dispatchEvent(new Event("change", { bubbles: true }));
    },
  });
  items.push({
    label: "Center on fix",
    disabled: !hasFix,
    action: () => {
      if (typeof centerMapOnFix === "function") centerMapOnFix();
      else if (typeof updatePositionMap === "function" && status) {
        const chk = document.getElementById("map-enabled");
        if (chk && !chk.checked) {
          chk.checked = true;
          chk.dispatchEvent(new Event("change", { bubbles: true }));
        }
        updatePositionMap(status);
        if (typeof invalidateDashboardMap === "function") invalidateDashboardMap();
      }
    },
  });
  items.push({
    label: "Fit track in view",
    disabled: trackLen < 2 && !hasFix,
    action: () => {
      if (typeof fitMapToTrack === "function") fitMapToTrack();
      else if (typeof centerMapOnFix === "function") centerMapOnFix();
    },
  });
  items.push({
    label: trackLen ? `Clear track (${trackLen} pts)` : "Clear track",
    disabled: trackLen === 0,
    action: () => {
      if (typeof clearMapTrack === "function") clearMapTrack();
      else if (typeof mapTrackPoints !== "undefined" && typeof mapTrackLine !== "undefined") {
        mapTrackPoints.length = 0;
        if (mapTrackLine && mapTrackLine.setLatLngs) mapTrackLine.setLatLngs([]);
      }
    },
  });
  items.push({
    label: prefs.mapShowTrack !== false ? "✓ Show position track" : "Show position track",
    action: () => {
      if (typeof setMapShowTrack === "function") setMapShowTrack(!prefs.mapShowTrack);
    },
  });
  items.push({
    label: prefs.mapPrioritized ? "Show map controls" : "Prioritize map",
    action: () => {
      if (typeof setMapPrioritized === "function") setMapPrioritized(!prefs.mapPrioritized);
    },
  });
  items.push({
    label: "Refresh map size",
    disabled: !mapOn,
    action: () => {
      if (typeof ensureBridgeMap === "function") ensureBridgeMap();
      if (typeof invalidateDashboardMap === "function") invalidateDashboardMap();
    },
  });
}

document.addEventListener("DOMContentLoaded", () => {
  removeLegacyLayoutBanner();
  patchGridstackMapChromeMenu();
});
