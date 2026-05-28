"""Embedded local shell for Tools → Terminal (Windows: pywinpty)."""
from __future__ import annotations

import os
import queue
import re
import select
import subprocess
import sys
import time
from functools import partial
from pathlib import Path
from typing import Callable, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui import ui_prefs
from ui.fonts import monospace_ui_font
from ui.terminal_ping import (
    ping_pty_command,
    ping_subprocess_args,
    sanitize_ping_host,
    suggested_ping_preset_name,
)

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


def _powershell_embedded_args() -> list[str]:
    """Drop PSReadLine — it fights ConPTY/winpty (double echo, broken backspace)."""
    return [
        "-NoLogo",
        "-NoProfile",
        "-NoExit",
        "-Command",
        "Remove-Module PSReadLine -ErrorAction SilentlyContinue",
    ]


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
            return ps, _powershell_embedded_args()
        return os.path.join(system_root, "System32", "cmd.exe"), ["/Q"]
    shell = os.environ.get("SHELL", "/bin/bash")
    return shell, ["-i"] if "bash" in os.path.basename(shell) else []


def _consume_duplicate_key_text(pending: str, text: str) -> str:
    """
    When Qt delivers the same printable char via inputMethodEvent and keyPressEvent
    (common on Windows), only write once.
    """
    if not pending or not text:
        return pending
    if pending.startswith(text):
        return pending[len(text) :]
    return pending


def _external_shell_working_directory() -> str:
    """Prefer the app folder when frozen so bench scripts beside the exe are in cwd."""
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve().parent)
    try:
        return os.getcwd()
    except OSError:
        return str(Path.home())


def launch_external_shell(exe: str, args: list[str], cwd: str | None = None) -> tuple[bool, str]:
    """
    Open a visible shell window. GUI-subsystem apps on Windows cannot rely on
    QProcess.startDetached for console hosts — use CREATE_NEW_CONSOLE / cmd start.
    """
    work = cwd or _external_shell_working_directory()
    if sys.platform == "win32":
        return _launch_external_shell_windows(exe, list(args), work)
    try:
        QtCore.QProcess.startDetached(exe, args, work)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _launch_external_shell_windows(exe: str, args: list[str], cwd: str) -> tuple[bool, str]:
    if not os.path.isfile(exe):
        return False, f"Shell not found: {exe}"
    create_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    try:
        subprocess.Popen(
            [exe, *args],
            cwd=cwd,
            creationflags=create_flags,
        )
        return True, ""
    except OSError:
        pass
    # Fallback: `start` opens a new console even when the parent is windowed (PyInstaller).
    try:
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "Serial Link shell", exe, *args],
            cwd=cwd,
        )
        return True, ""
    except OSError as exc:
        return False, str(exc)


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
        self._pending_ime_text = ""
        self.setObjectName("systemTerminalScreen")
        self.setReadOnly(True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_InputMethodEnabled, False)
        self.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByKeyboard
            | QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.setUndoRedoEnabled(False)
        self.setMaximumBlockCount(8000)
        self.setCenterOnScroll(False)
        self.setFont(monospace_ui_font())
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setToolTip("Local shell — click here, then type when the session is running.")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

    def inputMethodEvent(self, event: QtGui.QInputMethodEvent) -> None:
        commit = event.commitString()
        if commit:
            self._pending_ime_text += commit
            self._write_fn(commit)
        event.accept()

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
            self._pending_ime_text = ""
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
            pending = self._pending_ime_text
            if pending and pending.startswith(text):
                self._pending_ime_text = _consume_duplicate_key_text(pending, text)
                event.accept()
                return
            self._pending_ime_text = ""
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

        shell_row = QtWidgets.QHBoxLayout()
        shell_row.setSpacing(8)
        self._shell_combo = QtWidgets.QComboBox()
        self._shell_combo.setObjectName("systemTerminalShell")
        if sys.platform == "win32":
            self._shell_combo.addItem("PowerShell", ("powershell",))
            self._shell_combo.addItem("Command Prompt", ("cmd",))
        else:
            self._shell_combo.addItem("Login shell", ("login",))
        self._shell_combo.setToolTip("Shell to spawn when you press New session.")
        self._shell_combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self._shell_combo.setMaximumWidth(168)
        shell_row.addWidget(QtWidgets.QLabel("Shell:"))
        shell_row.addWidget(self._shell_combo)
        self._btn_new = QtWidgets.QPushButton("New session")
        self._btn_new.setToolTip("Start a fresh shell (stops any existing session).")
        self._btn_clear = QtWidgets.QPushButton("Clear screen")
        self._btn_external = QtWidgets.QPushButton("Open external…")
        self._btn_external.setToolTip(
            "Open PowerShell or cmd in a separate console window (always available)."
        )
        shell_row.addWidget(self._btn_new)
        shell_row.addWidget(self._btn_clear)
        shell_row.addWidget(self._btn_external)
        shell_row.addStretch(1)
        root.addLayout(shell_row)

        ping_row = QtWidgets.QHBoxLayout()
        ping_row.setSpacing(8)
        ping_row.addWidget(QtWidgets.QLabel("Ping:"))
        self._ping_host = QtWidgets.QLineEdit()
        self._ping_host.setObjectName("terminalPingHost")
        self._ping_host.setPlaceholderText("IP or hostname")
        self._ping_host.setClearButtonEnabled(True)
        self._ping_host.setMinimumWidth(100)
        self._ping_host.setMaximumWidth(240)
        self._ping_host.setToolTip("IPv4, hostname, or MagicDNS name (e.g. boat.tail-xx.ts.net)")
        ping_row.addWidget(self._ping_host)
        self._btn_ping = QtWidgets.QPushButton("Ping")
        self._btn_ping.setToolTip("Run ping in the shell below (starts a session if needed).")
        self._btn_ping_save = QtWidgets.QPushButton("Save…")
        self._btn_ping_save.setToolTip(
            "Save the host above as a named preset (name prefilled from the current ping target)."
        )
        self._btn_ping_delete = QtWidgets.QPushButton("Delete")
        self._btn_ping_delete.setToolTip("Remove the selected preset from the list.")
        self._btn_ping_delete.setEnabled(False)
        self._ping_preset_combo = QtWidgets.QComboBox()
        self._ping_preset_combo.setObjectName("terminalPingPresets")
        self._ping_preset_combo.setMinimumWidth(88)
        self._ping_preset_combo.setMaximumWidth(160)
        self._ping_preset_combo.setToolTip("Load a saved ping target.")
        ping_row.addWidget(self._btn_ping)
        ping_row.addWidget(self._btn_ping_save)
        ping_row.addWidget(self._btn_ping_delete)
        ping_row.addWidget(self._ping_preset_combo)
        ping_row.addStretch(1)
        root.addLayout(ping_row)

        self._ping_bubble_row = QtWidgets.QHBoxLayout()
        self._ping_bubble_row.setSpacing(6)
        self._ping_bubble_label = QtWidgets.QLabel("Quick:")
        self._ping_bubble_row.addWidget(self._ping_bubble_label)
        self._ping_bubble_host = QtWidgets.QWidget()
        self._ping_bubble_inner = QtWidgets.QHBoxLayout(self._ping_bubble_host)
        self._ping_bubble_inner.setContentsMargins(0, 0, 0, 0)
        self._ping_bubble_inner.setSpacing(6)
        self._ping_bubble_row.addWidget(self._ping_bubble_host, 1)
        root.addLayout(self._ping_bubble_row)

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
        self._btn_ping.clicked.connect(self._on_ping_clicked)
        self._btn_ping_save.clicked.connect(self._on_ping_save_preset)
        self._btn_ping_delete.clicked.connect(self._on_ping_delete_preset)
        self._ping_preset_combo.currentIndexChanged.connect(self._on_ping_preset_combo_changed)
        self._ping_host.returnPressed.connect(self._on_ping_clicked)

        self._ping_process: QtCore.QProcess | None = None
        self._ping_save_default_name: str = ""
        self._refresh_ping_presets_ui()
        self._refresh_availability()

    def _refresh_availability(self) -> None:
        if _HAS_WINPTY:
            self._fallback.setVisible(False)
            self._screen.setEnabled(True)
            self._btn_new.setEnabled(True)
            self._status.setText("Click New session, then type in the screen below.")
            return
        self._fallback.setVisible(True)
        self._screen.setEnabled(True)
        self._btn_new.setEnabled(False)
        self._btn_ping.setEnabled(True)
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
            if key == ("powershell",):
                ps = os.path.join(
                    system_root,
                    "System32",
                    "WindowsPowerShell",
                    "v1.0",
                    "powershell.exe",
                )
                if os.path.isfile(ps):
                    return ps, _powershell_embedded_args()
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

    def _refresh_ping_presets_ui(self) -> None:
        host = self._ping_host.text()
        self._ping_preset_combo.blockSignals(True)
        self._ping_preset_combo.clear()
        self._ping_preset_combo.addItem("Presets…", "")
        for name in ui_prefs.list_terminal_ping_preset_names():
            h = ui_prefs.terminal_ping_host(name) or ""
            self._ping_preset_combo.addItem(name, h)
        self._ping_preset_combo.setCurrentIndex(0)
        self._ping_preset_combo.blockSignals(False)
        self._sync_ping_delete_button()
        self._ping_host.setText(host)
        while self._ping_bubble_inner.count():
            item = self._ping_bubble_inner.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for name in ui_prefs.terminal_ping_bubble_names():
            target = ui_prefs.terminal_ping_host(name) or ""
            btn = QtWidgets.QPushButton(name)
            btn.setObjectName("terminalPingBubble")
            btn.setFlat(True)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            btn.setToolTip(f"Ping {target} — right-click to delete preset")
            btn.clicked.connect(partial(self._run_ping, target))
            btn.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                partial(self._on_ping_bubble_context_menu, name)
            )
            self._ping_bubble_inner.addWidget(btn)
        self._ping_bubble_inner.addStretch(1)
        has_bubbles = bool(ui_prefs.terminal_ping_bubble_names())
        self._ping_bubble_label.setVisible(has_bubbles)
        self._ping_bubble_host.setVisible(has_bubbles)

    def _selected_ping_preset_name(self) -> Optional[str]:
        index = self._ping_preset_combo.currentIndex()
        if index <= 0:
            return None
        name = self._ping_preset_combo.currentText().strip()
        return name or None

    def _sync_ping_delete_button(self) -> None:
        self._btn_ping_delete.setEnabled(self._selected_ping_preset_name() is not None)

    def _on_ping_preset_combo_changed(self, index: int) -> None:
        self._sync_ping_delete_button()
        if index <= 0:
            return
        host = self._ping_preset_combo.currentData()
        if host:
            self._ping_host.setText(str(host))

    def _confirm_delete_ping_preset(self, name: str) -> bool:
        clean = name.strip()
        if not clean:
            return False
        host = ui_prefs.terminal_ping_host(clean) or ""
        detail = f" ({host})" if host else ""
        answer = QtWidgets.QMessageBox.question(
            self,
            "Delete ping preset",
            f"Remove preset «{clean}»{detail}?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        return answer == QtWidgets.QMessageBox.StandardButton.Yes

    def _delete_ping_preset_named(self, name: str) -> None:
        clean = name.strip()
        if not clean:
            return
        if not ui_prefs.delete_terminal_ping_preset(clean):
            QtWidgets.QMessageBox.information(
                self,
                "Delete ping preset",
                f"Preset «{clean}» was not found.",
            )
            return
        self._refresh_ping_presets_ui()

    def _on_ping_delete_preset(self) -> None:
        name = self._selected_ping_preset_name()
        if not name:
            QtWidgets.QMessageBox.information(
                self,
                "Delete ping preset",
                "Choose a preset in the list, then click Delete.",
            )
            return
        if not self._confirm_delete_ping_preset(name):
            return
        self._delete_ping_preset_named(name)

    def _on_ping_bubble_context_menu(self, name: str, pos: QtCore.QPoint) -> None:
        btn = self.sender()
        if not isinstance(btn, QtWidgets.QWidget):
            return
        menu = QtWidgets.QMenu(self)
        act_delete = menu.addAction(f"Delete «{name}»…")
        chosen = menu.exec(btn.mapToGlobal(pos))
        if chosen is not act_delete:
            return
        if not self._confirm_delete_ping_preset(name):
            return
        self._delete_ping_preset_named(name)

    def _on_ping_save_preset(self) -> None:
        host = sanitize_ping_host(self._ping_host.text())
        if not host:
            QtWidgets.QMessageBox.warning(
                self,
                "Ping preset",
                "Enter a valid IP address or hostname first.",
            )
            return
        default_name = self._ping_save_default_name or suggested_ping_preset_name(host)
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Save ping preset",
            "Preset name:",
            QtWidgets.QLineEdit.EchoMode.Normal,
            default_name,
        )
        if not ok:
            return
        err = ui_prefs.save_terminal_ping_preset(name, host)
        if err:
            QtWidgets.QMessageBox.warning(self, "Ping preset", err)
            return
        self._refresh_ping_presets_ui()
        for i in range(self._ping_preset_combo.count()):
            if self._ping_preset_combo.itemText(i) == name.strip():
                self._ping_preset_combo.setCurrentIndex(i)
                break

    def _on_ping_clicked(self) -> None:
        self._run_ping(self._ping_host.text())

    def _run_ping(self, host: str) -> None:
        clean = sanitize_ping_host(host)
        if not clean:
            QtWidgets.QMessageBox.warning(
                self,
                "Ping",
                "Enter a valid IP address or hostname.",
            )
            return
        self._ping_host.setText(clean)
        self._ping_save_default_name = suggested_ping_preset_name(clean)
        self._ping_preset_combo.blockSignals(True)
        self._ping_preset_combo.setCurrentIndex(0)
        self._ping_preset_combo.blockSignals(False)
        self._sync_ping_delete_button()
        if _HAS_WINPTY:
            cmd = ping_pty_command(clean)
            if not cmd:
                return
            self._append_output_immediate(f"\n--- ping {clean} ---\n")

            def _send() -> None:
                self._submit_pty_write(cmd)
                self._screen.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)

            self._with_session(_send)
            return
        self._run_ping_subprocess(clean)

    def _with_session(self, action: Callable[[], None]) -> None:
        if self._io is not None and self._pty is not None:
            try:
                alive = bool(getattr(self._pty, "isalive", lambda: False)())
            except Exception:
                alive = False
            if alive:
                action()
                return
        self._restart_session()
        if self._io is not None:
            QtCore.QTimer.singleShot(450, action)

    def _run_ping_subprocess(self, host: str) -> None:
        args = ping_subprocess_args(host)
        if not args:
            return
        proc = self._ping_process
        if proc is not None and proc.state() != QtCore.QProcess.ProcessState.NotRunning:
            proc.kill()
            proc.waitForFinished(500)
        proc = QtCore.QProcess(self)
        self._ping_process = proc
        proc.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)

        def _append_chunk() -> None:
            data = proc.readAllStandardOutput()
            if data:
                self._append_output_immediate(bytes(data).decode("utf-8", errors="replace"))

        proc.readyReadStandardOutput.connect(_append_chunk)
        proc.finished.connect(
            lambda _code, _status: self._append_output_immediate("\n[ping finished]\n")
        )
        self._append_output_immediate(f"\n--- ping {host} (subprocess) ---\n")
        self._screen.setEnabled(True)
        proc.start(args[0], args[1:])

    def _open_external_shell(self) -> None:
        exe, args = self._shell_command()
        cwd = _external_shell_working_directory()
        ok, err = launch_external_shell(exe, args, cwd)
        if ok:
            self._status.setText(
                f"Opened external {os.path.basename(exe)} (cwd: {cwd})."
            )
            return
        QtWidgets.QMessageBox.warning(
            self,
            "Open external shell",
            f"Could not start {exe}:\n{err or 'unknown error'}",
        )

    def _show_install_hint(self) -> None:
        QtWidgets.QMessageBox.information(
            self,
            "Embedded terminal",
            "From the same Python environment as the bridge:\n\n"
            "    pip install pywinpty\n\n"
            "Restart the app, then open Tools → Terminal again.",
        )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        proc = self._ping_process
        if proc is not None and proc.state() != QtCore.QProcess.ProcessState.NotRunning:
            proc.kill()
            proc.waitForFinished(500)
        self._ping_process = None
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
