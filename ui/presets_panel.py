"""Named connection presets tab (replaces Desk/Boat path buttons)."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from bench_config import validate_preset_name
from ui.tool_tabs import _scrollable


def create_presets_tab(
    parent: QtWidgets.QWidget,
    *,
    include_advanced_net: bool = True,
) -> QtWidgets.QWidget:
    host = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(host)
    lay.setContentsMargins(14, 14, 14, 14)
    lay.setSpacing(10)

    hint = QtWidgets.QLabel(
        "Save COM, UDP listen, NMEA mode (Tools → NMEA: passthrough / strict / raw), "
        "and optional survey Ethernet targets under names you choose. "
        "Load a preset to fill connection + NMEA fields, then Start on Connect (or the field strip)."
    )
    hint.setWordWrap(True)
    hint.setObjectName("tabHint")
    lay.addWidget(hint)

    row = QtWidgets.QHBoxLayout()
    parent.preset_list = QtWidgets.QListWidget()
    parent.preset_list.setObjectName("presetList")
    parent.preset_list.setMinimumWidth(160)
    parent.preset_list.setMinimumHeight(96)
    parent.preset_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
    parent.preset_list.setDragEnabled(True)
    parent.preset_list.setAcceptDrops(True)
    parent.preset_list.setDropIndicatorShown(True)
    parent.preset_list.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
    parent.preset_list.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
    parent.preset_list.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
    parent.preset_list.setToolTip(
        "Click a preset to select and load it (when the bridge is stopped). "
        "Double-click or use Load. Saved on this PC (%USERPROFILE%\\.cursor-udp-com-bridge\\path_presets.json)."
    )
    row.addWidget(parent.preset_list, 1)

    btn_col = QtWidgets.QVBoxLayout()
    parent.btn_preset_load = QtWidgets.QPushButton("Load")
    parent.btn_preset_load.setObjectName("btnPresetLoad")
    parent.btn_preset_save = QtWidgets.QPushButton("Save")
    parent.btn_preset_save.setObjectName("btnPresetSave")
    parent.btn_preset_save_as = QtWidgets.QPushButton("Save as…")
    parent.btn_preset_save_as.setObjectName("btnPresetSaveAs")
    parent.btn_preset_new = QtWidgets.QPushButton("New…")
    parent.btn_preset_new.setObjectName("btnPresetNew")
    parent.btn_preset_delete = QtWidgets.QPushButton("Delete")
    parent.btn_preset_delete.setObjectName("btnPresetDelete")
    for b in (
        parent.btn_preset_load,
        parent.btn_preset_save,
        parent.btn_preset_save_as,
        parent.btn_preset_new,
        parent.btn_preset_delete,
    ):
        b.setMinimumWidth(96)
        btn_col.addWidget(b)
    btn_col.addStretch(1)
    row.addLayout(btn_col)
    lay.addLayout(row, 1)

    net_box = QtWidgets.QGroupBox("Survey network (optional — boat / LAN)")
    nf = QtWidgets.QFormLayout(net_box)
    parent.preset_pc_ip = QtWidgets.QLineEdit()
    parent.preset_subnet = QtWidgets.QLineEdit()
    parent.preset_ins_ip = QtWidgets.QLineEdit()
    parent.preset_notes = QtWidgets.QPlainTextEdit()
    parent.preset_notes.setMaximumHeight(56)
    nf.addRow("Survey PC IP:", parent.preset_pc_ip)
    nf.addRow("Subnet mask:", parent.preset_subnet)
    nf.addRow("INS IP (reference):", parent.preset_ins_ip)
    nf.addRow("Notes:", parent.preset_notes)
    lay.addWidget(net_box)

    if include_advanced_net:
        adv = QtWidgets.QGroupBox("Advanced network (TCP / UDP remote)")
        av = QtWidgets.QVBoxLayout(adv)
        av.addWidget(parent.chk_advanced_net)
        av.addWidget(parent._advanced_net)
        av.addWidget(parent.chk_serial_auto_reconnect)
        lay.addWidget(adv)
    else:
        note = QtWidgets.QLabel(
            "TCP server/client and UDP remote are on the Connect tab under "
            "Network → Advanced network."
        )
        note.setWordWrap(True)
        note.setObjectName("tabHint")
        lay.addWidget(note)

    parent.btn_preset_load.clicked.connect(parent._preset_load_selected)
    parent.btn_preset_save.clicked.connect(parent._preset_save_selected)
    parent.btn_preset_save_as.clicked.connect(parent._preset_save_as)
    parent.btn_preset_new.clicked.connect(parent._preset_new)
    parent.btn_preset_delete.clicked.connect(parent._preset_delete_selected)
    parent.preset_list.itemClicked.connect(parent._on_preset_list_item_clicked)
    parent.preset_list.itemSelectionChanged.connect(parent._on_preset_list_selection_changed)
    parent.preset_list.itemDoubleClicked.connect(parent._preset_load_selected)
    model = parent.preset_list.model()
    if model is not None and hasattr(model, "rowsMoved"):
        model.rowsMoved.connect(parent._on_preset_rows_moved)

    return _scrollable(host)
