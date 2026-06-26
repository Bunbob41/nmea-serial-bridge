import time, unittest
from depth_codec import DepthSample
from sounding_mux import DISPLAY_CAP, FixSnapshot, SoundingBuffer, mux_depth

class T(unittest.TestCase):
    def test_stale(self):
        fix = FixSnapshot(44.0,-120.0,1,1.2,"gga", time.monotonic()-4)
        d = DepthSample(5.0,"sddpt","x", time.monotonic())
        self.assertTrue(mux_depth(d, fix, stale_ms=3000).stale)
    def test_cap(self):
        buf = SoundingBuffer(cap=DISPLAY_CAP)
        fix = FixSnapshot(44.0,-120.0,1,1.2,"gga", time.monotonic())
        d = DepthSample(5.0,"sddpt","x", time.monotonic())
        for _ in range(DISPLAY_CAP+5): buf.append(mux_depth(d, fix))
        self.assertEqual(len(buf), DISPLAY_CAP)
if __name__ == "__main__": unittest.main()