"""Named connection presets tab (replaces Desk/Boat path buttons)."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from bench_config import validate_preset_name
from ui.tool_tabs import _scrollable

_PRESET_IP_FIELD_MAX_W = 248


def _preset_ip_field(edit: QtWidgets.QLineEdit) -> QtWidgets.QLineEdit:
    edit.setMaximumWidth(_PRESET_IP_FIELD_MAX_W)
    edit.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Fixed,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    return edit


def create_presets_tab(
    parent: QtWidgets.QWidget,
    *,
    include_advanced_net: bool = True,
    embedded: bool = False,
) -> QtWidgets.QWidget:
    host = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(host)
    margins = 0 if embedded else 14
    lay.setContentsMargins(margins, margins, margins, margins)
    lay.setSpacing(10)

    if not embedded:
        hint = QtWidgets.QLabel(
            "Save COM, UDP listen, NMEA mode (Tools → NMEA: passthrough / strict / raw), "
            "and optional survey Ethernet targets under names you choose. "
            "Click a preset to edit its survey fields below; use Load (or double-click) to apply "
            "connection + NMEA to Connect, then Start."
        )
        hint.setWordWrap(True)
        hint.setObjectName("tabHint")
        lay.addWidget(hint)

    split = QtWidgets.QHBoxLayout()
    split.setSpacing(12)

    list_card = QtWidgets.QFrame()
    list_card.setObjectName("modernPresetListCard")
    list_lay = QtWidgets.QVBoxLayout(list_card)
    list_lay.setContentsMargins(10, 10, 10, 10)
    list_lay.setSpacing(0)
    parent.preset_list = QtWidgets.QListWidget()
    parent.preset_list.setObjectName("presetList")
    parent.preset_list.setMinimumWidth(160)
    min_h = 180 if embedded else 220
    parent.preset_list.setMinimumHeight(min_h)
    parent.preset_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
    parent.preset_list.setDragEnabled(True)
    parent.preset_list.setAcceptDrops(True)
    parent.preset_list.setDropIndicatorShown(True)
    parent.preset_list.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
    parent.preset_list.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
    parent.preset_list.setVerticalScrollBarPolicy(
        QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    parent.preset_list.setHorizontalScrollBarPolicy(
        QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    parent.preset_list.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
    parent.preset_list.setToolTip(
        "Click to select and edit survey fields (PC IP, subnet, notes). "
        "Load or double-click applies COM/UDP/NMEA to Connect. "
        "Saved on this PC (%USERPROFILE%\\.cursor-udp-com-bridge\\path_presets.json)."
    )
    list_lay.addWidget(parent.preset_list, 1)
    split.addWidget(list_card, 4)

    right_panel = QtWidgets.QWidget()
    right_panel.setObjectName("modernPresetRightPanel")
    right_lay = QtWidgets.QVBoxLayout(right_panel)
    right_lay.setContentsMargins(0, 0, 0, 0)
    right_lay.setSpacing(10)

    btn_row = QtWidgets.QHBoxLayout()
    btn_row.setSpacing(6)
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
    ):
        b.setMinimumWidth(72)
        btn_row.addWidget(b, 0)
    btn_row.addStretch(1)
    parent.btn_preset_delete.setMinimumWidth(72)
    btn_row.addWidget(parent.btn_preset_delete, 0)
    right_lay.addLayout(btn_row)

    net_box = QtWidgets.QGroupBox("Survey network (optional — boat / LAN)")
    net_box.setObjectName("modernToolsFormGroup")
    nf = QtWidgets.QFormLayout(net_box)
    nf.setFieldGrowthPolicy(
        QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
    )
    nf.setLabelAlignment(
        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    nf.setFormAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
    )
    nf.setHorizontalSpacing(12)
    nf.setVerticalSpacing(8)
    parent.preset_pc_ip = _preset_ip_field(QtWidgets.QLineEdit())
    parent.preset_subnet = _preset_ip_field(QtWidgets.QLineEdit())
    parent.preset_ins_ip = _preset_ip_field(QtWidgets.QLineEdit())
    parent.preset_notes = QtWidgets.QPlainTextEdit()
    parent.preset_notes.setMinimumHeight(96)
    parent.preset_notes.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Expanding,
    )
    nf.addRow("Survey PC IP:", parent.preset_pc_ip)
    nf.addRow("Subnet mask:", parent.preset_subnet)
    nf.addRow("INS IP (reference):", parent.preset_ins_ip)
    if embedded:
        notes_lbl = QtWidgets.QLabel("Notes")
        notes_lbl.setObjectName("modernControlFormLabel")
        nf.addRow(notes_lbl)
        nf.addRow(parent.preset_notes)
    else:
        nf.addRow("Notes:", parent.preset_notes)
    right_lay.addWidget(net_box, 1)

    if include_advanced_net:
        adv = QtWidgets.QGroupBox("Advanced network (TCP / UDP remote)")
        av = QtWidgets.QVBoxLayout(adv)
        av.addWidget(parent.chk_advanced_net)
        av.addWidget(parent._advanced_net)
        av.addWidget(parent.chk_serial_auto_reconnect)
        right_lay.addWidget(adv)
    else:
        note = QtWidgets.QLabel(
            "TCP / UDP remote modes: Control tab → Network → Advanced network."
        )
        note.setWordWrap(True)
        note.setObjectName("tabNote")
        right_lay.addWidget(note)

    right_lay.addStretch(1)
    split.addWidget(right_panel, 6)
    lay.addLayout(split, 1)

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

    if embedded:
        return host
    return _scrollable(host)
