import tempfile, unittest
from pathlib import Path
from ui.mission_export import export_session_survey_csv
from ui.mission_session import MissionSessionRecord
class T(unittest.TestCase):
    def test_csv(self):
        r=MissionSessionRecord(0,10,10,"",0,0,1.0,soundings=[{"depth_m":5.2,"lat":44,"lon":-120,"fix_stale":False}])
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"o.csv"; export_session_survey_csv(r,p)
            self.assertIn("depth_m", p.read_text(encoding="utf-8"))
if __name__ == "__main__": unittest.main()