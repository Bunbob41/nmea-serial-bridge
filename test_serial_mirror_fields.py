"""Serial mirror port picker widget."""
from __future__ import annotations

import unittest

from PySide6 import QtWidgets

from ui.serial_mirror_fields import NONE_LABEL, SerialMirrorPortPicker


class TestSerialMirrorPortPicker(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QtWidgets.QApplication.instance() is None:
            cls._app = QtWidgets.QApplication([])
        else:
            cls._app = QtWidgets.QApplication.instance()

    def test_text_round_trip(self) -> None:
        picker = SerialMirrorPortPicker()
        picker.refresh(devices=["COM7", "COM8", "COM9"], primary_com="COM7")
        picker.set_ports("COM8, COM9")
        self.assertEqual(picker.text(), "COM8, COM9")

    def test_excludes_primary_from_refresh(self) -> None:
        picker = SerialMirrorPortPicker()
        picker.refresh(devices=["COM7", "COM8"], primary_com="COM7")
        items = [picker._cb1.itemText(i) for i in range(picker._cb1.count())]
        self.assertIn(NONE_LABEL, items)
        self.assertIn("COM8", items)
        self.assertNotIn("COM7", items)

    def test_dedupes_duplicate_selection(self) -> None:
        picker = SerialMirrorPortPicker()
        picker.refresh(devices=["COM7", "COM8", "COM9"], primary_com="COM7")
        picker.set_ports(["COM8", "COM8"])
        picker._cb2.setCurrentIndex(picker._cb2.findText("COM8"))
        self.assertEqual(picker.text(), "COM8")


if __name__ == "__main__":
    unittest.main()