"""Unit tests for Serial Link (nmea-serial-bridge).

Run from repo root::

    python -m unittest discover -s tests -p "test_*.py"
    python tools/run_unittests.py
    python verify_all.py
"""

from pathlib import Path

# Repo root (parent of this package directory).
REPO_ROOT = Path(__file__).resolve().parent.parent
