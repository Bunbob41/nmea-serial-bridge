import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ui import ui_prefs


class TestBudgetSurveyStack(unittest.TestCase):
    def test_default_depth_com_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                prefs = ui_prefs.load_budget_survey_prefs()
        self.assertFalse(prefs.get("depth_com_enabled"))


if __name__ == "__main__":
    unittest.main()
