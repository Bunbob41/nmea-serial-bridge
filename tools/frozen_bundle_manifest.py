"""Files that must exist in PyInstaller ``_internal`` for portable parity with dev."""
from __future__ import annotations

# Keep in sync with nmea_serial_bridge.spec HELPER_SCRIPTS + HELPER_MODULES.
FROZEN_HELPER_FILES = (
    "verify_all.py",
    "com_free.py",
    "check_setup.py",
    "nmea_static_sample.py",
    "bench_tcp_stress.py",
    "bench_capacity_probe.py",
    "bench_gui_smoke.py",
    "bridge_headless.py",
    "bench_stress.py",
    "bench_network_automation.py",
    "bench_fanout_automation.py",
    "bench_config.py",
    "bench_udp_test.py",
    "bench_tcp_test.py",
    "nmea_codec.py",
    "bridge_core.py",
    "py_interpreter.py",
)

FROZEN_STATIC_FILES = (
    "assets/app-icon.ico",
    "assets/app-icon.png",
    "assets/app-icon-source.png",
    "web/static/index.html",
    "web/static/dashboard.js",
    "web/static/dashboard.css",
    "web/static/survey_map.html",
    "web/static/survey_map.css",
    "web/static/survey_map.js",
    "web/static/depth_ramp.js",
    "web/static/layouts/gridstack/index.html",
    "web/static/vendor/gridstack/gridstack-all.js",
)

FROZEN_PYTHON_PACKAGES = ("fastapi", "uvicorn")
