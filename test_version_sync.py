"""Release metadata alignment: version.py vs version_info.txt."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _read_version_py() -> str:
    text = (ROOT / "version.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    assert m, "version.py missing __version__"
    return m.group(1).strip()


def _read_version_info_semver() -> str:
    text = (ROOT / "version_info.txt").read_text(encoding="utf-8")
    m = re.search(r'StringStruct\("FileVersion",\s*"([^"]+)"\)', text)
    assert m, "version_info.txt missing FileVersion"
    file_ver = m.group(1).strip()
    m2 = re.search(r'StringStruct\("ProductVersion",\s*"([^"]+)"\)', text)
    assert m2, "version_info.txt missing ProductVersion"
    prod_ver = m2.group(1).strip()
    self_msg = f"FileVersion={file_ver!r} ProductVersion={prod_ver!r}"
    if file_ver != prod_ver:
        raise AssertionError(f"version_info mismatch: {self_msg}")
    return file_ver


class TestVersionSync(unittest.TestCase):
    def test_version_info_matches_version_py(self) -> None:
        py_ver = _read_version_py()
        info_ver = _read_version_info_semver()
        self.assertEqual(info_ver, py_ver)

    def test_version_info_tuple_matches_semver(self) -> None:
        py_ver = _read_version_py()
        text = (ROOT / "version_info.txt").read_text(encoding="utf-8")
        parts = [int(x) for x in py_ver.split(".")[:3]]
        tuple_str = f"({parts[0]}, {parts[1]}, {parts[2]}, 0)"
        self.assertIn(f"filevers={tuple_str}", text)
        self.assertIn(f"prodvers={tuple_str}", text)


if __name__ == "__main__":
    unittest.main()
