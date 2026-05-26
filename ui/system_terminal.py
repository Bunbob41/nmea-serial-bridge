"""Embedded local shell for Tools → Terminal (Windows: pywinpty)."""
from __future__ import annotations

import os
import queue
import re
import select
import sys
import time
from typing import Callable, Optional

from PySide6 import QtCore, QtGui, QtWidgets

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\].*?(?:\x07|\x1b\\)|\x1b[@-_]")
_READ_CHUNK = 16_384
_BULK_FLUSH_MS = 24
_SELECT_TIMEOUT_S = 0.012
_RESIZE_DEBOUNCE_MS = 120
_IMMEDIATE_FLUSH_MAX = 1024

_WINPTY_IMPORT_ERROR: Optional[Exception] = None
try:
    import winpty  # type: ignore[import-untyped]

    _HAS_WINPTY = True
except Exception as exc:  # pragma: no cover - platform / missing wheel
    winpty = None  # type: ignore[assignment]
    _HAS_WINPTY = False
    _WINPTY_IMPORT_ERROR = exc


def _backspace_byte() -> str:
    """Windows consoles expect BS (0x08); Unix TTYs usually expect DEL (0x7f)."""
    return "\x08" if sys.platform == "win32" else "\x7f"


def _default_shell() -> tuple[str, list[str]]:
    if sys.platform == "win32":
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        ps = os.path.join(
            system_root,
            "System32",
            "WindowsPowerShell",
            "v1.0",
            "powershell.exe",
        )
        if os.path.isfile(ps):
            return ps, ["-NoLogo", "-NoProfile"]
        return os.path.join(system_root, "System32", "cmd.exe"), ["/Q"]
    shell = os.environ.get("SHELL", "/bin/bash")
    return shell, ["-i"] if "bash" in os.path.basename(shell) else []


def _strip_ansi(text: str) -> str:
    if "\x1b" not in text:
        return text
    return _ANSI_ESCAPE.sub("", text)


class _PtyIoThread(QtCore.QThread):
    """Owns blocking PTY I/O: select-driven reads, queued writes (never blocks the GUI)."""

    output = QtCore.Signal(str)
    exited = QtCore.Signal(int)

    def __init__(self, pty: object, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._pty = pty
        self._stop = False
        self._write_q: queue.SimpleQueue[str] = queue.SimpleQueue()

    def submit_write(self, data: str) -> None:
        if data:
            self._write_q.put(data)

    def stop(self) -> None:
        self._stop = True

    def _drain_writes(self) -> None:
        pty = self._pty
        while True:
            try:
                data = self._write_q.get_nowait()
            except queue.Empty:
                break
            try:
                pty.write(data)  # type: ignore[union-attr]
            except Exception:
                pass

    def _read_ready(self) -> str:
        pty = self._pty
        chunk = pty.read(_READ_CHUNK)  # type: ignore[union-attr]
        if not chunk:
            return ""
        if isinstance(chunk, bytes):
            return chunk.decode("utf-8", errors="replace")
        return str(chunk)

    def run(self) -> None:
        pty = self._pty
        fd = getattr(pty, "fd", None)
        bulk: list[str] = []
        last_bulk = time.monotonic()
        while not self._stop:
            self._drain_writes()
            if not getattr(pty, "isalive", lambda: False)():
                break
            got_data = False
            if fd is not None:
                try:
                    ready, _, _ = select.select([fd], [], [], _SELECT_TIMEOUT_S)
                except Exception:
                    ready = []
                if ready:
                    try:
                        chunk = self._read_ready()
                    except EOFError:
                        break
                    except Exception:
                        chunk = ""
                    if chunk:
                        got_data = True
                        if len(chunk) < _IMMEDIATE_FLUSH_MAX:
                            self.output.emit(chunk)
                        else:
                            bulk.append(chunk)
            else:
                # Fallback when fd is unavailable (should not happen on Windows).
                try:
                    chunk = self._read_ready()
                except EOFError:
                    break
                except Exception:
                    chunk = ""
                if chunk:
                    got_data = True
                    if len(chunk) < _IMMEDIATE_FLUSH_MAX:
                        self.output.emit(chunk)
                    else:
                        bulk.append(chunk)
                else:
                    self.msleep(12)

            now = time.monotonic()
            if bulk and (
                not got_data
                or sum(len(x) for x in bulk) >= 48_000
                or (now - last_bulk) * 1000.0 >= _BULK_FLUSH_MS
            ):
                self.output.emit("".join(bulk))
                bulk.clear()
                last_bulk = now

        self._drain_writes()
        if bulk:
            self.output.emit("".join(bulk))
        code = 0
        try:
            code = int(getattr(pty, "exitstatus", lambda: 0)() or 0)
        except Exception:
            code = 0
        self.exited.emit(code)


class _TerminalScreen(QtWidgets.QPlainTextEdit):
    """Read-only screen; keystrokes go to the PTY."""

    def __init__(
        self,
        write_fn: Callable[[str], None],
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._write_fn = write_fn
        self._bs = _backspace_byte()
        self.setObjectName("systemTerminalScreen")
        self.setReadOnly(True)
        self.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByKeyboard
            | QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.setUndoRedoEnabled(False)
        self.setMaximumBlockCount(8000)
        self.setCenterOnScroll(False)
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(max(9, font.pointSize()))
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setToolTip("Local shell — click here, then type when the session is running.")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.matches(QtGui.QKeySequence.StandardKey.Copy):
            super().keyPressEvent(event)
            return
        if event.matches(QtGui.QKeySequence.StandardKey.SelectAll):
            super().keyPressEvent(event)
            return
        if event.matches(QtGui.QKeySequence.StandardKey.Paste):
            text = QtWidgets.QApplication.clipboard().text()
            if text:
                self._write_fn(text)
            event.accept()
            return

        mods = event.modifiers() & ~QtCore.Qt.KeyboardModifier.KeypadModifier
        if mods & QtCore.Qt.KeyboardModifier.ControlModifier:
            key = event.key()
            if key == QtCore.Qt.Key.Key_C:
                self._write_fn("\x03")
                event.accept()
                return
            if key == QtCore.Qt.Key.Key_D:
                self._write_fn("\x04")
                event.accept()
                return
            if key == QtCore.Qt.Key.Key_L:
                self.clear()
                event.accept()
                return
            if key == QtCore.Qt.Key.Key_V:
                text = QtWidgets.QApplication.clipboard().text()
                if text:
                    self._write_fn(text)
                event.accept()
                return
            if key == QtCore.Qt.Key.Key_H:
                self._write_fn("\x08")
                event.accept()
                return

        key = event.key()
        if key in (QtCore.Qt.Key.Key_Backspace, QtCore.Qt.Key.Key_Delete):
            self._write_fn(self._bs if key == QtCore.Qt.Key.Key_Backspace else "\x1b[3~")
            event.accept()
            return
        if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            self._write_fn("\r")
            event.accept()
            return
        if key == QtCore.Qt.Key.Key_Tab:
            self._write_fn("\t")
            event.accept()
            return

        text = event.text()
        if text and text not in ("\x7f", "\x08"):
            self._write_fn(text)
            event.accept()
            return

        seq = _key_to_escape(key, mods)
        if seq:
            self._write_fn(seq)
            event.accept()
            return
        event.ignore()


def _key_to_escape(key: int, mods: QtCore.Qt.KeyboardModifier) -> str:
    if key == QtCore.Qt.Key.Key_Up:
        return "\x1b[A"
    if key == QtCore.Qt.Key.Key_Down:
        return "\x1b[B"
    if key == QtCore.Qt.Key.Key_Right:
        return "\x1b[C"
    if key == QtCore.Qt.Key.Key_Left:
        return "\x1b[D"
    if key == QtCore.Qt.Key.Key_Home:
        return "\x1b[H"
    if key == QtCore.Qt.Key.Key_End:
        return "\x1b[F"
    if key == QtCore.Qt.Key.Key_PageUp:
        return "\x1b[5~"
    if key == QtCore.Qt.Key.Key_PageDown:
        return "\x1b[6~"
    if bool(mods & QtCore.Qt.KeyboardModifier.ShiftModifier) and key == QtCore.Qt.Key.Key_Tab:
        return "\x1b[Z"
    if bool(mods & QtCore.Qt.KeyboardModifier.AltModifier) and 0x20 <= key <= 0x7E:
        return chr(key)
    return ""


class SystemTerminalWidget(QtWidgets.QWidget):
    """PTY-backed shell panel; falls back to launch external terminal on Windows without pywinpty."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("systemTerminalHost")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self._pty: object | None = None
        self._io: _PtyIoThread | None = None
        self._pending_out: list[str] = []
        self._resize_timer = QtCore.QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(_RESIZE_DEBOUNCE_MS)
        self._resize_timer.timeout.connect(self._update_pty_size)
        self._flush_timer = QtCore.QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(_BULK_FLUSH_MS)
        self._flush_timer.timeout.connect(self._flush_pending_output)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)

        hint = QtWidgets.QLabel(
            "Local shell on this PC (PowerShell by default). "
            "Use for bench scripts, COM tools, and ping — not the bridge inject path."
        )
        hint.setWordWrap(True)
        hint.setObjectName("tabHint")
        root.addWidget(hint)

        bar = QtWidgets.QHBoxLayout()
        bar.setSpacing(8)
        self._shell_combo = QtWidgets.QComboBox()
        self._shell_combo.setObjectName("systemTerminalShell")
        if sys.platform == "win32":
            self._shell_combo.addItem("PowerShell", ("powershell",))
            self._shell_combo.addItem("Command Prompt", ("cmd",))
        else:
            self._shell_combo.addItem("Login shell", ("login",))
        self._shell_combo.setToolTip("Shell to spawn when you press New session.")
        bar.addWidget(QtWidgets.QLabel("Shell:"))
        bar.addWidget(self._shell_combo, 1)

        self._btn_new = QtWidgets.QPushButton("New session")
        self._btn_new.setToolTip("Start a fresh shell (stops any existing session).")
        self._btn_clear = QtWidgets.QPushButton("Clear screen")
        self._btn_external = QtWidgets.QPushButton("Open external…")
        self._btn_external.setToolTip(
            "Open PowerShell or cmd in a separate console window (always available)."
        )
        bar.addWidget(self._btn_new)
        bar.addWidget(self._btn_clear)
        bar.addWidget(self._btn_external)
        root.addLayout(bar)

        self._status = QtWidgets.QLabel()
        self._status.setObjectName("tabNote")
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        self._screen = _TerminalScreen(self._submit_pty_write)
        self._screen.setMinimumHeight(200)
        root.addWidget(self._screen, 1)

        note = QtWidgets.QLabel(
            "Bridge NMEA inject: Tools → Inject. "
            "Ctrl+C interrupt · Ctrl+L clear view · scroll up to pause auto-scroll."
        )
        note.setWordWrap(True)
        note.setObjectName("tabNote")
        root.addWidget(note)

        self._fallback = QtWidgets.QWidget()
        fl = QtWidgets.QVBoxLayout(self._fallback)
        fl.setContentsMargins(0, 8, 0, 0)
        self._fallback_msg = QtWidgets.QLabel()
        self._fallback_msg.setWordWrap(True)
        self._fallback_msg.setObjectName("tabNote")
        fl.addWidget(self._fallback_msg)
        fb_row = QtWidgets.QHBoxLayout()
        self._btn_install_hint = QtWidgets.QPushButton("Install pywinpty")
        self._btn_install_hint.setToolTip("Show pip install command in a dialog.")
        fb_row.addWidget(self._btn_install_hint)
        fb_row.addStretch(1)
        fl.addLayout(fb_row)
        root.addWidget(self._fallback)

        self._btn_new.clicked.connect(self._restart_session)
        self._btn_clear.clicked.connect(self._screen.clear)
        self._btn_external.clicked.connect(self._open_external_shell)
        self._btn_install_hint.clicked.connect(self._show_install_hint)

        self._refresh_availability()

    def _refresh_availability(self) -> None:
        if _HAS_WINPTY:
            self._fallback.setVisible(False)
            self._screen.setEnabled(True)
            self._btn_new.setEnabled(True)
            self._status.setText("Click New session, then type in the screen below.")
            return
        self._fallback.setVisible(True)
        self._screen.setEnabled(False)
        self._btn_new.setEnabled(False)
        err = _WINPTY_IMPORT_ERROR
        detail = f" ({err})" if err else ""
        self._fallback_msg.setText(
            "Embedded shell needs the optional pywinpty package on Windows. "
            f"Install with: pip install pywinpty{detail}"
        )
        self._status.setText(
            "Embedded shell unavailable — use Open external… or pip install pywinpty."
        )

    def _shell_command(self) -> tuple[str, list[str]]:
        key = self._shell_combo.currentData()
        if sys.platform == "win32":
            system_root = os.environ.get("SystemRoot", r"C:\Windows")
            if key == ("cmd",):
                return os.path.join(system_root, "System32", "cmd.exe"), ["/Q"]
            exe, args = _default_shell()
            return exe, list(args)
        return _default_shell()

    def _restart_session(self) -> None:
        if not _HAS_WINPTY:
            self._open_external_shell()
            return
        self._stop_session()
        self._pending_out.clear()
        self._flush_timer.stop()
        exe, args = self._shell_command()
        cwd = os.getcwd()
        try:
            cmd = [exe] + args if args else exe
            self._pty = winpty.PtyProcess.spawn(cmd, cwd=cwd)  # type: ignore[union-attr]
        except Exception as exc:
            self._append_output_immediate(f"\n[Could not start shell: {exc}]\n")
            self._status.setText(f"Start failed: {exc}")
            return
        self._status.setText(f"Running — {os.path.basename(exe)}  (cwd: {cwd})")
        self._io = _PtyIoThread(self._pty, self)
        self._io.output.connect(
            self._queue_output,
            QtCore.Qt.ConnectionType.QueuedConnection,
        )
        self._io.exited.connect(
            self._on_pty_exit,
            QtCore.Qt.ConnectionType.QueuedConnection,
        )
        self._io.start()
        self._schedule_resize()
        self._screen.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)

    def _stop_session(self) -> None:
        self._flush_timer.stop()
        self._flush_pending_output()
        io = self._io
        self._io = None
        pty = self._pty
        self._pty = None
        if pty is not None:
            try:
                if getattr(pty, "isalive", lambda: False)():
                    pty.close(force=True)  # type: ignore[attr-defined]
            except Exception:
                pass
        if io is not None:
            io.stop()
            if io.isRunning():
                io.wait(2000)

    def _submit_pty_write(self, data: str) -> None:
        io = self._io
        if io is None or not data:
            return
        io.submit_write(data)

    def _screen_at_bottom(self) -> bool:
        bar = self._screen.verticalScrollBar()
        return bar.value() >= bar.maximum() - 3

    def _queue_output(self, text: str) -> None:
        if not text:
            return
        self._pending_out.append(text)
        pending_len = sum(len(p) for p in self._pending_out)
        if pending_len < _IMMEDIATE_FLUSH_MAX:
            self._flush_pending_output()
        elif not self._flush_timer.isActive():
            self._flush_timer.start()

    def _flush_pending_output(self) -> None:
        if not self._pending_out:
            return
        blob = "".join(self._pending_out)
        self._pending_out.clear()
        clean = _strip_ansi(blob)
        if not clean:
            return
        follow = self._screen_at_bottom()
        self._screen.setUpdatesEnabled(False)
        try:
            cursor = self._screen.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            cursor.beginEditBlock()
            cursor.insertText(clean)
            cursor.endEditBlock()
            self._screen.setTextCursor(cursor)
        finally:
            self._screen.setUpdatesEnabled(True)
        if follow:
            bar = self._screen.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _append_output_immediate(self, text: str) -> None:
        self._queue_output(text)
        self._flush_pending_output()

    def _on_pty_exit(self, code: int) -> None:
        self._flush_pending_output()
        self._append_output_immediate(f"\n[Session ended — exit {code}]\n")
        self._status.setText(f"Session ended (exit {code}). Click New session to restart.")
        self._pty = None

    def _update_pty_size(self) -> None:
        pty = self._pty
        if pty is None:
            return
        fm = self._screen.fontMetrics()
        cell_w = max(1, fm.horizontalAdvance("M"))
        cell_h = max(1, fm.height())
        cols = max(20, self._screen.viewport().width() // cell_w)
        rows = max(8, self._screen.viewport().height() // cell_h)
        try:
            pty.setwinsize(rows, cols)  # type: ignore[attr-defined]
        except Exception:
            pass

    def _schedule_resize(self) -> None:
        self._resize_timer.start()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._pty is not None:
            self._schedule_resize()

    def _open_external_shell(self) -> None:
        if sys.platform == "win32":
            exe, args = self._shell_command()
            QtCore.QProcess.startDetached(exe, args, os.getcwd())
            return
        shell, args = _default_shell()
        QtCore.QProcess.startDetached(shell, args, os.getcwd())

    def _show_install_hint(self) -> None:
        QtWidgets.QMessageBox.information(
            self,
            "Embedded terminal",
            "From the same Python environment as the bridge:\n\n"
            "    pip install pywinpty\n\n"
            "Restart the app, then open Tools → Terminal again.",
        )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._stop_session()
        super().closeEvent(event)


def build_system_terminal_tab(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Tools → Terminal page (fills stack/drawer; no outer scroll wrapper)."""
    _ = parent
    tab = SystemTerminalWidget()
    tab.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Expanding,
    )
    return tab
