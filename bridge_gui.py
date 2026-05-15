# bridge_gui.py — UDP ↔ COM bridge (Windows PySide6 prototype)
# Python 3.10+  |  pip install pyserial pyserial-asyncio PySide6
import asyncio
import sys

import serial_asyncio
import serial.tools.list_ports
from PySide6 import QtCore, QtWidgets


# --- Bridge core using asyncio ---
class SerialUDPBridge:
    def __init__(self, com, baud, udp_listen=None, udp_remote=None, loop=None, log_cb=None):
        self.com = com
        self.baud = baud
        self.udp_listen = udp_listen  # (host, port) or None
        self.udp_remote = udp_remote  # (host, port) or None
        self.loop = loop or asyncio.get_event_loop()
        self.log = log_cb or (lambda *a, **k: None)
        self.serial_reader = None
        self.serial_writer = None
        self.udp_transport = None
        self.last_udp_addr = None
        self.running = False

    async def start(self):
        self.log(f"Opening serial {self.com} @ {self.baud}")
        try:
            self.serial_reader, self.serial_writer = await serial_asyncio.open_serial_connection(
                url=self.com, baudrate=self.baud
            )
        except Exception as e:
            self.log(f"Serial open error: {e}")
            return
        if self.udp_listen:
            self.udp_transport, _ = await self.loop.create_datagram_endpoint(
                lambda: UDPProtocol(self), local_addr=self.udp_listen
            )
            self.log(f"Listening UDP on {self.udp_listen}")
        elif self.udp_remote:
            self.udp_transport, _ = await self.loop.create_datagram_endpoint(
                lambda: UDPProtocol(self), remote_addr=self.udp_remote
            )
            self.log(f"UDP remote set to {self.udp_remote}")
        self.running = True
        self.loop.create_task(self._serial_reader())

    async def stop(self):
        self.running = False
        if self.udp_transport:
            try:
                self.udp_transport.close()
            except Exception:
                pass
            self.udp_transport = None
        if self.serial_writer:
            try:
                self.serial_writer.close()
                await self.serial_writer.wait_closed()
            except Exception:
                pass
            self.serial_writer = None
            self.serial_reader = None
        self.log("Bridge stopped")

    async def _drain_serial(self):
        if self.serial_writer:
            try:
                await self.serial_writer.drain()
            except Exception:
                pass

    async def _serial_reader(self):
        while self.running and self.serial_reader:
            try:
                data = await self.serial_reader.read(4096)
            except Exception as e:
                self.log(f"Serial read error: {e}")
                break
            if data:
                s = data.decode(errors="replace").rstrip()
                self.log(f"SER→UDP: {s}")
                if self.udp_transport:
                    if self.udp_listen and self.last_udp_addr:
                        self.udp_transport.sendto(data, self.last_udp_addr)
                    else:
                        self.udp_transport.sendto(data)
            else:
                await asyncio.sleep(0.01)


class UDPProtocol:
    def __init__(self, bridge):
        self.bridge = bridge

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.bridge.last_udp_addr = addr
        try:
            s = data.decode(errors="replace").rstrip()
        except Exception:
            s = repr(data)
        self.bridge.log(f"UDP←{addr}: {s}")
        writer = self.bridge.serial_writer
        if writer:
            try:
                writer.write(data)
                self.bridge.loop.create_task(self.bridge._drain_serial())
            except Exception as e:
                self.bridge.log(f"Serial write error: {e}")


# --- Qt GUI ---
class BridgeWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UDP ↔ COM Bridge (Windows prototype)")
        self.resize(800, 420)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        left = QtWidgets.QFormLayout()

        self.com_cb = QtWidgets.QComboBox()
        left.addRow("COM Port:", self.com_cb)

        self.refresh_btn = QtWidgets.QPushButton("Refresh ports")
        left.addRow(self.refresh_btn)

        self.baud_edit = QtWidgets.QLineEdit("115200")
        left.addRow("Baud:", self.baud_edit)

        self.mode_group = QtWidgets.QButtonGroup(self)
        self.listen_radio = QtWidgets.QRadioButton("UDP listen (local)")
        self.remote_radio = QtWidgets.QRadioButton("UDP remote (fixed)")
        self.listen_radio.setChecked(True)
        self.mode_group.addButton(self.listen_radio)
        self.mode_group.addButton(self.remote_radio)
        left.addRow(self.listen_radio)
        left.addRow(self.remote_radio)

        self.udp_host = QtWidgets.QLineEdit("0.0.0.0")
        self.udp_port = QtWidgets.QLineEdit("10110")
        left.addRow("UDP host:", self.udp_host)
        left.addRow("UDP port:", self.udp_port)

        self.remote_host = QtWidgets.QLineEdit("192.168.1.100")
        self.remote_port = QtWidgets.QLineEdit("10110")
        self.remote_host.setEnabled(False)
        self.remote_port.setEnabled(False)
        left.addRow("Remote host:", self.remote_host)
        left.addRow("Remote port:", self.remote_port)

        self.start_btn = QtWidgets.QPushButton("Start Bridge")
        self.stop_btn = QtWidgets.QPushButton("Stop Bridge")
        self.stop_btn.setEnabled(False)
        left.addRow(self.start_btn, self.stop_btn)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)

        h = QtWidgets.QHBoxLayout()
        ctrl_widget = QtWidgets.QWidget()
        ctrl_widget.setLayout(left)
        h.addWidget(ctrl_widget, 0)
        h.addWidget(self.log_view, 1)
        self.setLayout(h)

        self.bridge = None

        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.start_btn.clicked.connect(self.start_bridge)
        self.stop_btn.clicked.connect(self.stop_bridge)
        self.listen_radio.toggled.connect(self._mode_toggle)

        self.refresh_ports()

        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._pump_asyncio)
        self._timer.start(50)

    def _log(self, txt):
        self.log_view.appendPlainText(txt)

    def refresh_ports(self):
        self.com_cb.clear()
        for p in serial.tools.list_ports.comports():
            self.com_cb.addItem(p.device)

    def _mode_toggle(self, checked):
        is_listen = self.listen_radio.isChecked()
        self.udp_host.setEnabled(is_listen)
        self.udp_port.setEnabled(is_listen)
        self.remote_host.setEnabled(not is_listen)
        self.remote_port.setEnabled(not is_listen)

    def start_bridge(self):
        com = self.com_cb.currentText()
        if not com:
            self._log("No COM selected")
            return
        try:
            baud = int(self.baud_edit.text())
        except ValueError:
            self._log("Invalid baud")
            return
        if self.listen_radio.isChecked():
            try:
                host = self.udp_host.text()
                port = int(self.udp_port.text())
            except ValueError:
                self._log("Invalid UDP listen")
                return
            udp_listen = (host, port)
            udp_remote = None
        else:
            try:
                rh = self.remote_host.text()
                rp = int(self.remote_port.text())
            except ValueError:
                self._log("Invalid UDP remote")
                return
            udp_listen = None
            udp_remote = (rh, rp)

        self.bridge = SerialUDPBridge(
            com, baud, udp_listen=udp_listen, udp_remote=udp_remote, loop=self.loop, log_cb=self._log
        )
        self.loop.create_task(self.bridge.start())
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_bridge(self):
        if self.bridge:
            b = self.bridge
            self.bridge = None

            async def _stop():
                await b.stop()
                # asyncio pump runs on the same thread as Qt here; safe to touch widgets.
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)

            self.loop.create_task(_stop())
        else:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _pump_asyncio(self):
        try:
            self.loop.call_soon(self.loop.stop)
            self.loop.run_forever()
        except Exception as e:
            self._log(f"Asyncio pump error: {e}")


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = BridgeWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
