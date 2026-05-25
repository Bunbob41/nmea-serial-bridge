# NORBIT DCT + iWBMSe — bridge workflow (Applanix stack)

This app does **not** run DCT or the iWBMSe. On the **boat PC** it **listens UDP port 40810** and forwards Applanix NMEA to the **COM** DCT uses when serial positioning is enabled.

**Port is always 40810** for this stack (not bench default 10110).

**Where DCT runs** decides **which IP** it uses to reach the boat PC stream.

---

## DCT positioning target (pick one row)

The **bridge stays on the boat PC** (`UDP listen 0.0.0.0:40810`). Only the **IP DCT (or Applanix, when remote)** uses changes.

| Where DCT runs | Set DCT network position to | Notes |
| -------------- | --------------------------- | ----- |
| **On the boat PC** (same machine as bridge + DCT) | **`127.0.0.1:40810`** | Loopback to the bridge on that PC. (Spoken as “127.0.0.0” in the field — use **127.0.0.1**, not `127.0.0.0`.) |
| **On the operator laptop** (MikroTik PTP / offline wireless Ethernet to the boat) | **`192.168.1.8:40810`** | **Boat IP** on the MikroTik point-to-point link — not the laptop’s IP. Bridge must be **Running** on the boat PC. |
| **Over Tailscale or ZeroTier** | **`<boat StaticIp>:40810`** | Use the overlay **static** IPv4 assigned to the **boat PC** in that VPN (e.g. `100.x.x.x`). Same port **40810**. |

Applanix UDP output must reach the **boat PC** on **40810** as well. On the boat LAN that is often the boat’s survey IP (e.g. **192.168.1.4**); over VPN use the same **StaticIp** as DCT.

---

## Typical hardware (reference)

| Device | Role | Address / link |
|--------|------|----------------|
| **Boat PC** | Bridge + (usually) DCT + GUI | Survey LAN e.g. **192.168.1.4**; MikroTik wireless leg **192.168.1.8**; VPN **StaticIp** |
| **Operator laptop** | Optional — DCT/GUI only | Sees boat as **192.168.1.8** on MikroTik PTP |
| **Applanix** (POS MV / WebUI) | INS — RTK inside Applanix | Often **192.168.1.150** on survey LAN |
| **Trimble GNSS** | Usually into **Applanix** | Often **192.168.142.1** |
| **iWBMSe** | Multibeam in **DCT/GUI** | Separate from bridge |
| **Bluetooth `$SDDBT`** | Depth | Usually **another COM** in DCT |

```text
Applanix 192.168.1.150 ──UDP──► boat PC :40810 ◄── bridge listens (0.0.0.0:40810)
                                      │
                    ┌─────────────────┼─────────────────┐
                    │ DCT on boat PC: 127.0.0.1:40810   │
                    │ DCT on laptop:  192.168.1.8:40810 │  (MikroTik wireless)
                    │ DCT over VPN:   StaticIp:40810    │  (Tailscale / ZeroTier)
                    └─────────────────┬─────────────────┘
                                      │ serial (if configured)
                                      ▼
                               COM? → DCT position leg
```

---

## Bridge on the boat PC (each session)

| Step | Action |
|------|--------|
| 1 | **Tools → Presets → NORBIT DCT** → **Load** → set **COM** / baud for DCT serial leg if used. |
| 2 | **Connect** — **Listen port 40810**, **UDP listen** `0.0.0.0`. |
| 3 | **NMEA → Passthrough**. |
| 4 | Configure **DCT** per table above (127.0.0.1 vs 192.168.1.8 vs VPN StaticIp). |
| 5 | **Applanix** — send NMEA UDP to the **boat PC** on **40810** (LAN or VPN IP matching your link). |
| 6 | **Start bridge** → log shows Applanix traffic; Hz stable. |
| 7 | DCT + iWBMSe survey as usual; **Stop** when done. |

RTK stays in **Applanix** — bridge **NTRIP** off.

---

## Applanix (WebUI)

- Destination = **boat PC** address on the path you use (survey LAN IP, or VPN **StaticIp**), port **40810**.
- Confirm **GGA/RMC** in the bridge log, not only `$SDDBT` on a depth COM.

---

## COM exclusivity (serial path)

One app per positioning **COM**. **Unlock ports** if a crash left the port busy.

---

## Bench test

com0com on the boat PC; UDP test to **`127.0.0.1:40810`** before trusting the boat COM.

---

## Web dashboard (operator phone/laptop)

**8765** on the boat PC — use **Tailscale/ZeroTier StaticIp** or LAN IP, not `127.0.0.1` from another device. See **Tools → Phone**.

---

## Preflight

```text
python check_setup.py --production --port 40810
python com_free.py --com COMx
```

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| DCT no fix on boat PC | DCT must be **127.0.0.1:40810**, bridge **Running** on **40810** |
| DCT no fix on laptop | Boat bridge **Running**; ping **192.168.1.8**; firewall on boat PC for UDP **40810** |
| DCT no fix on VPN | DCT **StaticIp** = boat’s VPN IP; Applanix also sending to that IP (or routed) |
| No UDP in log | Wrong port (**10110** vs **40810**); Applanix aimed at wrong boat IP |
| Only `$SDDBT` | Depth COM — not Applanix positioning |

---

## Save a vessel preset

**Presets → Save as** with your real **COM**, MikroTik boat IP (**192.168.1.8**), and VPN **StaticIp** in **notes** so the next operator picks the right DCT row in the table above.
