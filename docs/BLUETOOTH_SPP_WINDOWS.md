# Bluetooth SPP on Windows (bookmark)

**Status:** Documented workaround — **not** implemented in Serial Link yet.  
**Observed:** Sonarmite over Bluetooth; incoming **COM5**, outgoing **COM3** (“SPP Dev”).

---

## Why two COM ports?

When Windows pairs a **Serial Port Profile (SPP)** device, it usually creates **two** virtual COM ports:

| Port | Windows role | What opening the port does |
|------|----------------|----------------------------|
| **Outgoing** (e.g. COM3 “SPP Dev”) | Client | Windows **dials** the paired device and opens RFCOMM — the radio link goes active (device LED solid). |
| **Incoming** (e.g. COM5) | Server | Windows **waits** for the remote device to connect to this PC. |

References:

- [Microsoft Technet — Bluetooth SPP two COM ports](https://learn.microsoft.com/en-us/archive/msdn-technet-forums/58f690e5-1939-43c2-a2d3-245a527c678b)
- [Andreas' Blog — Windows 10 Bluetooth SPP](https://blog.bachi.net/?p=9700)

**Who initiates the connection determines which leg is used** — not “one port for TX and one for RX” in the USB sense.

---

## Field symptom (Sonarmite)

1. Serial Link **Start** on **COM5** (incoming) — bridge opens the port, but sonar LED keeps **flashing** (BT session not fully up).
2. Open **Tera Term on COM3** (outgoing) — LED goes **solid**; sonar stream is live.
3. Only one app can own a given COM at a time — Tera Term and Serial Link cannot both hold COM3.

So today: **outgoing COM3 establishes the link**; **incoming COM5 may carry the data** once the sonar connects in — or data may appear on COM3 depending on stack/device.

---

## Current workaround (operators)

1. Confirm baud in Tera Term (often **4800** or **9600** for old Sonarmite ASCII).
2. Identify which port shows traffic when the LED is solid.
3. **Close Tera Term** before Serial Link **Start**.
4. Use Serial Link on the port that actually receives bytes (**COM→NET** in Activity).
5. If the LED drops when only COM5 is open, the device likely needs the **outgoing** leg dialed first — until we ship a fix, you may need to:
   - power-cycle the sonar after Serial Link Start, or
   - use a small helper that opens outgoing COM3 in the background (future feature), or
   - use a USB serial sonar path instead of BT SPP.

**NMEA mode:** **Passthrough** for old ASCII Sonarmite lines; **Raw** for binary SBT (`0x81…`).

**Network:** **UDP remote** to push sonar to a fixed listener, or **UDP listen** + fan-out if multiple consumers.

---

## Planned product work (backlog)

| ID | Idea | Effort |
|----|------|--------|
| BT-SPP-01 | **Companion outgoing open** — when user picks incoming COM, optionally open paired outgoing port (hold-open, no read loop) to trigger Windows RFCOMM dial | M |
| BT-SPP-02 | **Port-pair hint in UI** — detect “Standard Serial over Bluetooth link” + “SPP Dev” names in Device Manager / port list; tooltip explains incoming vs outgoing | S |
| BT-SPP-03 | **Bench doc + Diagnostics** — link from Connect / Guide to this page; optional checklist step “BT SPP: confirm LED solid” | S |

Do **not** merge incoming+outgoing into one bidirectional stream in software without testing each device — Microsoft stack treats them as separate connection modes.

---

## Related

- `docs/OPERATOR_GUIDE.md` §6.5 (sonar / depth row)
- `docs/NORBIT_DCT.md` (Bluetooth depth on separate COM)
- COM exclusivity: Start blocked if another app holds the port
