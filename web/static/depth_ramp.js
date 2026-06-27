/* Shared depth color ramp + legend color editor (Survey Map + web dashboard). */
(function (global) {
  const STORAGE_KEY = "serialLink.depthRamp.v1";
  const DEFAULT_RAMP = [
    { t: 0, r: 8, g: 48, b: 107 },
    { t: 0.2, r: 33, g: 158, b: 188 },
    { t: 0.4, r: 42, g: 157, b: 143 },
    { t: 0.6, r: 233, g: 196, b: 106 },
    { t: 0.8, r: 244, g: 162, b: 97 },
    { t: 1, r: 231, g: 111, b: 81 },
  ];

  function cloneDefault() {
    return DEFAULT_RAMP.map(function (s) {
      return { t: s.t, r: s.r, g: s.g, b: s.b };
    });
  }

  function isValidRamp(arr) {
    if (!Array.isArray(arr) || arr.length < 2) return false;
    return arr.every(function (s) {
      return (
        s &&
        Number.isFinite(+s.t) &&
        Number.isFinite(+s.r) &&
        Number.isFinite(+s.g) &&
        Number.isFinite(+s.b)
      );
    });
  }

  function loadDepthRamp() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (isValidRamp(parsed)) return parsed;
      }
    } catch (_e) {
      /* ignore */
    }
    return cloneDefault();
  }

  function saveDepthRamp(ramp) {
    if (!isValidRamp(ramp)) return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ramp));
  }

  function depthRampColor(t, ramp) {
    const stops = ramp || DEFAULT_RAMP;
    t = Math.max(0, Math.min(1, t));
    for (let i = 1; i < stops.length; i++) {
      const a = stops[i - 1];
      const b = stops[i];
      if (t <= b.t) {
        const f = (t - a.t) / ((b.t - a.t) || 1);
        return (
          "rgb(" +
          Math.round(a.r + (b.r - a.r) * f) +
          "," +
          Math.round(a.g + (b.g - a.g) * f) +
          "," +
          Math.round(a.b + (b.b - a.b) * f) +
          ")"
        );
      }
    }
    const z = stops[stops.length - 1];
    return "rgb(" + z.r + "," + z.g + "," + z.b + ")";
  }

  function hexToRgb(hex) {
    const h = String(hex || "").replace("#", "").trim();
    if (h.length === 3) {
      return {
        r: parseInt(h[0] + h[0], 16),
        g: parseInt(h[1] + h[1], 16),
        b: parseInt(h[2] + h[2], 16),
      };
    }
    if (h.length !== 6) return null;
    const n = parseInt(h, 16);
    if (!Number.isFinite(n)) return null;
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
  }

  function rgbToHex(r, g, b) {
    function h(v) {
      const s = Math.max(0, Math.min(255, Math.round(v))).toString(16);
      return s.length === 1 ? "0" + s : s;
    }
    return "#" + h(r) + h(g) + h(b);
  }

  function sampleRamp(ramp, t) {
    const c = depthRampColor(t, ramp);
    const m = c.match(/rgb\((\d+),(\d+),(\d+)\)/);
    if (!m) return { r: 0, g: 0, b: 0 };
    return { r: +m[1], g: +m[2], b: +m[3] };
  }

  function lerpRgb(a, b, f) {
    return {
      r: Math.round(a.r + (b.r - a.r) * f),
      g: Math.round(a.g + (b.g - a.g) * f),
      b: Math.round(a.b + (b.b - a.b) * f),
    };
  }

  function rampFromTriad(shallowHex, midHex, deepHex) {
    const shallow = hexToRgb(shallowHex) || { r: 8, g: 48, b: 107 };
    const mid = hexToRgb(midHex) || { r: 42, g: 157, b: 143 };
    const deep = hexToRgb(deepHex) || { r: 231, g: 111, b: 81 };
    const stops = [
      { t: 0, ...shallow },
      { t: 0.2, ...lerpRgb(shallow, mid, 0.33) },
      { t: 0.4, ...lerpRgb(shallow, mid, 0.66) },
      { t: 0.6, ...lerpRgb(mid, deep, 0.33) },
      { t: 0.8, ...lerpRgb(mid, deep, 0.66) },
      { t: 1, ...deep },
    ];
    return stops;
  }

  function triadFromRamp(ramp) {
    const shallow = sampleRamp(ramp, 0);
    const mid = sampleRamp(ramp, 0.5);
    const deep = sampleRamp(ramp, 1);
    return {
      shallow: rgbToHex(shallow.r, shallow.g, shallow.b),
      mid: rgbToHex(mid.r, mid.g, mid.b),
      deep: rgbToHex(deep.r, deep.g, deep.b),
    };
  }

  function bindLegendColorMenu(opts) {
    const legend = document.getElementById(opts.legendId);
    const menu = document.getElementById(opts.menuId);
    if (!legend || !menu) return;
    const shallowIn = document.getElementById(opts.shallowId || "depth-ramp-shallow");
    const midIn = document.getElementById(opts.midId || "depth-ramp-mid");
    const deepIn = document.getElementById(opts.deepId || "depth-ramp-deep");
    const resetBtn = document.getElementById(opts.resetId || "depth-ramp-reset");
    let ramp = loadDepthRamp();

    function hideMenu() {
      menu.hidden = true;
    }

    function syncInputs() {
      const tri = triadFromRamp(ramp);
      if (shallowIn) shallowIn.value = tri.shallow;
      if (midIn) midIn.value = tri.mid;
      if (deepIn) deepIn.value = tri.deep;
    }

    function applyFromInputs() {
      ramp = rampFromTriad(
        shallowIn ? shallowIn.value : "#084830",
        midIn ? midIn.value : "#2a9d8f",
        deepIn ? deepIn.value : "#e76f51"
      );
      saveDepthRamp(ramp);
      if (typeof opts.onChange === "function") opts.onChange(ramp);
    }

    legend.addEventListener("contextmenu", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      ramp = loadDepthRamp();
      syncInputs();
      menu.hidden = false;
      const pad = 8;
      const r = menu.getBoundingClientRect();
      let px = ev.clientX;
      let py = ev.clientY;
      if (px + r.width > window.innerWidth - pad) px = window.innerWidth - r.width - pad;
      if (py + r.height > window.innerHeight - pad) py = window.innerHeight - r.height - pad;
      menu.style.left = px + "px";
      menu.style.top = py + "px";
    });

    [shallowIn, midIn, deepIn].forEach(function (el) {
      if (!el) return;
      el.addEventListener("input", applyFromInputs);
      el.addEventListener("change", applyFromInputs);
    });

    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        ramp = cloneDefault();
        saveDepthRamp(ramp);
        syncInputs();
        if (typeof opts.onChange === "function") opts.onChange(ramp);
      });
    }

    menu.addEventListener("click", function (ev) {
      ev.stopPropagation();
    });
    document.addEventListener("click", hideMenu);
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") hideMenu();
    });
  }

  global.DepthRamp = {
    STORAGE_KEY: STORAGE_KEY,
    defaultRamp: cloneDefault,
    load: loadDepthRamp,
    save: saveDepthRamp,
    color: depthRampColor,
    fromTriad: rampFromTriad,
    triadFrom: triadFromRamp,
    bindLegendColorMenu: bindLegendColorMenu,
  };
})(window);
