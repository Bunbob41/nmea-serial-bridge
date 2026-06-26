import asyncio, unittest
from bridge_core import NetMode, SerialNetBridge
from nmea_codec import NmeaMode
_GGA = b"$GPGGA,032358.34,3600.42235,N,11846.36546,W,5,09,1.9,0.0,M,15.5,M,2.0,0000*51\r\n"
class T(unittest.TestCase):
    def test_ingest(self):
        loop = asyncio.new_event_loop()
        b = SerialNetBridge("COM99",115200,NetMode.UDP_LISTEN,loop=loop,udp_listen=("127.0.0.1",10110),nmea_mode=NmeaMode.PASSTHROUGH,depth_com_enabled=True,depth_com_port="COM8")
        b.running=True; b._ingest_net(_GGA,"UDP")
        cs=0
        body="SDDPT,5.0,0.0"
        for ch in body: cs^=ord(ch)
        b._ingest_depth_line(f"${body}*{cs:02X}")
        self.assertEqual(b.sounding_stats()["sounding_count"],1)
        b.abort_now(); loop.close()
if __name__ == "__main__": unittest.main()