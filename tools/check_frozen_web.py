#!/usr/bin/env python3
"""Backward-compatible alias for check_frozen_bundle."""
from tools.check_frozen_bundle import main

if __name__ == "__main__":
    raise SystemExit(main())
