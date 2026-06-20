"""Black-box backup taps NET→COM enqueue (primary survey path)."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from bridge_core import NetMode, SerialNetBridge
from core.local_logger import LocalSerialBackup


class TestBridgeLocalBackup(unittest.IsolatedAsyncioTestCase):
    async def test_enqueue_net_to_serial_records_net_to_com(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = LocalSerialBackup(base)
            path = backup.start_session()
            self.assertIsNotNone(path)

            bridge = SerialNetBridge(
                "COM7",
                115200,
                NetMode.UDP_LISTEN,
                udp_listen=("0.0.0.0", 10110),
                loop=asyncio.get_running_loop(),
            )
            bridge.running = True
            bridge._local_backup = backup

            payload = b"$GPGGA,123,456*00\r\n"
            bridge._enqueue_net_to_serial(payload, "UDP")
            await asyncio.sleep(0.05)
            snap = backup.close()
            self.assertGreaterEqual(int(snap["bytes"]), len(payload))
            assert path is not None
            self.assertIn(payload, path.read_bytes())

    async def test_enqueue_net_to_serial_records_without_serial_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = LocalSerialBackup(base)
            path = backup.start_session()
            self.assertIsNotNone(path)

            bridge = SerialNetBridge(
                "COM7",
                115200,
                NetMode.UDP_LISTEN,
                udp_listen=("0.0.0.0", 10110),
                loop=asyncio.get_running_loop(),
            )
            bridge.running = True
            bridge._local_backup = backup
            bridge.serial_writer = None

            payload = b"$GPGGA,789,012*00\r\n"
            bridge._enqueue_net_to_serial(payload, "UDP")
            await asyncio.sleep(0.05)
            snap = backup.close()
            self.assertGreaterEqual(int(snap["bytes"]), len(payload))
            assert path is not None
            self.assertIn(payload, path.read_bytes())

    async def test_write_serial_bytes_does_not_double_count_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = LocalSerialBackup(base)
            path = backup.start_session()
            self.assertIsNotNone(path)

            bridge = SerialNetBridge(
                "COM7",
                115200,
                NetMode.UDP_LISTEN,
                udp_listen=("0.0.0.0", 10110),
                loop=asyncio.get_running_loop(),
            )
            bridge.running = True
            bridge._local_backup = backup
            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = AsyncMock(return_value=None)
            bridge.serial_writer = writer

            payload = b"$GPGGA,123,456*00\r\n"
            bridge._enqueue_net_to_serial(payload, "UDP")
            await bridge._write_serial_bytes(payload)
            await asyncio.sleep(0.05)
            snap = backup.close()
            self.assertEqual(int(snap["bytes"]), len(payload))
            assert path is not None
            self.assertEqual(path.read_bytes().count(payload), 1)


if __name__ == "__main__":
    unittest.main()
