#!/usr/bin/env python3
"""Measure no-drop capacity by ramping UDP NMEA load against headless bridge."""
from __future__ import annotations

import argparse
import asyncio
import socket
from datetime import datetime, timezone

from bench_config import load_bench_defaults
from bench_udp_test import port_has_listener
from bridge_core import NetMode, SerialNetBridge, configure_windows_event_loop_policy
from nmea_codec import NmeaMode
from nmea_static_edh import build_gga, build_rmc


def _with_checksum(payload: str) -> str:
    cs = 0
    for ch in payload:
        cs ^= ord(ch)
    return f"${payload}*{cs:02X}"


def _sentence_batch(when: datetime, count: int) -> list[str]:
    hhmmss = when.strftime("%H%M%S")
    day = when.strftime("%d")
    month = when.strftime("%m")
    year = when.strftime("%Y")
    base = [
        build_gga(when, 38.685746, -121.082524, 255.0),
        build_rmc(when, 38.685746, -121.082524),
        _with_checksum("GPVTG,0.0,T,352.9,M,0.0,N,0.0,K"),
        _with_checksum(f"GPZDA,{hhmmss}.00,{day},{month},{year},00,00"),
        _with_checksum("SDDPT,5.0,0.0"),
        _with_checksum("GPGLL,3841.1448,N,12104.9514,W,225444,A"),
    ]
    out: list[str] = []
    i = 0
    while len(out) < count:
        out.append(base[i % len(base)])
        i += 1
    return out


async def _run_stage(
    *,
    hz: float,
    seconds: float,
    sentences_per_tick: int,
    dest_host: str,
    dest_port: int,
) -> tuple[int, int, float]:
    sent_lines = 0
    sent_bytes = 0
    stage_elapsed = 0.0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        interval = 1.0 / hz if hz > 0 else 0.2
        loop = asyncio.get_running_loop()
        stage_start = loop.time()
        end = stage_start + seconds
        while loop.time() < end:
            now = datetime.now(timezone.utc)
            batch = _sentence_batch(now, sentences_per_tick)
            for line in batch:
                wire = (line + "\r\n").encode("ascii")
                sock.sendto(wire, (dest_host, dest_port))
                sent_lines += 1
                sent_bytes += len(wire)
            await asyncio.sleep(interval)
        stage_elapsed = max(0.0, loop.time() - stage_start)
    finally:
        sock.close()
    return sent_lines, sent_bytes, stage_elapsed


async def _probe(args: argparse.Namespace) -> int:
    loop = asyncio.get_running_loop()
    logs: list[str] = []
    stats_last: dict = {}
    bridge = SerialNetBridge(
        args.com,
        args.baud,
        NetMode.UDP_LISTEN,
        udp_listen=(args.udp_host, args.udp_port),
        loop=loop,
        ui_log=logs.append,
        ui_log_verbose=lambda: False,
        stats_cb=lambda s: stats_last.update(s),
        nmea_mode=NmeaMode.STRICT if args.strict else NmeaMode.PASSTHROUGH,
    )

    if port_has_listener(args.udp_port) and args.udp_host in ("0.0.0.0", "", "127.0.0.1"):
        print(f"[capacity_probe] UDP :{args.udp_port} already in use. Stop GUI bridge first.")
        return 2

    ok = await bridge.start()
    if not ok:
        print("[capacity_probe] Bridge failed to start:")
        for line in logs[-10:]:
            print(f"  {line}")
        return 1

    print(
        f"[capacity_probe] running {args.com} @ {args.baud}, UDP {args.udp_host}:{args.udp_port}, "
        f"mode={'STRICT' if args.strict else 'PASSTHROUGH'}"
    )
    print(
        f"[capacity_probe] ramp: hz {args.hz_start}..{args.hz_stop} step {args.hz_step}, "
        f"{args.sentences} lines/tick, {args.stage_seconds:.1f}s/stage"
    )

    best_ok_hz = 0.0
    saw_backlog = False
    saw_clog = False
    timed_out = False
    stage_count = 0
    if args.hz_step > 0 and args.hz_stop >= args.hz_start:
        stage_count = int((args.hz_stop - args.hz_start) / args.hz_step) + 1
    auto_cap = max(20.0, stage_count * (args.stage_seconds + 0.5) + 8.0)
    max_runtime = float(args.max_runtime) if args.max_runtime and args.max_runtime > 0 else auto_cap
    probe_start = loop.time()
    print(f"[capacity_probe] runtime cap: {max_runtime:.1f}s")
    try:
        hz = args.hz_start
        while hz <= args.hz_stop + 1e-9:
            if loop.time() - probe_start > max_runtime:
                timed_out = True
                print("[capacity_probe] max-runtime reached; stopping probe safely.")
                break
            drops0 = bridge.drops_net_to_serial + bridge.drops_serial_to_net
            rej0 = bridge.rejected_net_to_serial + bridge.rejected_serial_to_net
            lines0 = bridge.lines_remote_to_serial
            qn0 = bridge.net_to_serial.qsize()
            qs0 = bridge.serial_to_net.qsize()
            sent_lines, sent_bytes, stage_seconds = await _run_stage(
                hz=hz,
                seconds=args.stage_seconds,
                sentences_per_tick=args.sentences,
                dest_host=args.dest_host,
                dest_port=args.udp_port,
            )
            await asyncio.sleep(0.25)
            drops1 = bridge.drops_net_to_serial + bridge.drops_serial_to_net
            rej1 = bridge.rejected_net_to_serial + bridge.rejected_serial_to_net
            lines1 = bridge.lines_remote_to_serial
            dd = drops1 - drops0
            rr = rej1 - rej0
            accepted = lines1 - lines0
            offered_lps = sent_lines / max(0.001, stage_seconds)
            accepted_lps = accepted / max(0.001, stage_seconds)
            mbps = (sent_bytes * 8) / max(0.001, stage_seconds) / 1_000_000.0
            qn = bridge.net_to_serial.qsize()
            qs = bridge.serial_to_net.qsize()
            qgrow_n2s = qn - qn0
            qgrow_s2n = qs - qs0
            backlog = qgrow_n2s > 12 or qgrow_s2n > 12
            if dd > 0 or rr > 0:
                tag = "CLG"
                saw_clog = True
            elif backlog:
                tag = "BKL"
                saw_backlog = True
            else:
                tag = "OK "
            print(
                f"[{tag}] hz={hz:5.1f} offer={offered_lps:6.1f} lps accept={accepted_lps:6.1f} lps "
                f"wire={mbps:0.3f} Mbps drops={dd} rej={rr} q=({qn},{qs}) dq=({qgrow_n2s},{qgrow_s2n})"
            )
            if tag == "OK ":
                best_ok_hz = hz
            elif args.stop_on_clog:
                break
            hz += args.hz_step
    finally:
        bridge.abort_now()
        pending = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
        for t in pending:
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        await asyncio.sleep(0.15)

    if best_ok_hz > 0:
        print(
            f"[capacity_probe] no-drop ceiling so far: {best_ok_hz:.1f} Hz * {args.sentences} lines/tick "
            f"= {best_ok_hz * args.sentences:.1f} lines/s"
        )
    elif saw_backlog and not saw_clog:
        print("[capacity_probe] no hard drops yet, but queues grew (backlog). Check serial consumer/path.")
    else:
        print("[capacity_probe] no clean stage found (drops/rejects started immediately).")
    if timed_out:
        return 3
    if saw_clog:
        return 2
    if saw_backlog and args.fail_on_backlog:
        return 4
    return 0


def main() -> None:
    configure_windows_event_loop_policy()
    d = load_bench_defaults()
    p = argparse.ArgumentParser(description="Ramp load and find no-drop NMEA throughput")
    p.add_argument("--com", default=str(d["com"]))
    p.add_argument("--baud", type=int, default=int(d["baud"]))
    p.add_argument("--udp-host", default=str(d["udp_host"]))
    p.add_argument("--udp-port", type=int, default=int(d["udp_port"]))
    p.add_argument("--dest-host", default="127.0.0.1", help="Destination host to send test load")
    p.add_argument("--strict", action="store_true", help="Use STRICT parser mode")
    p.add_argument("--sentences", type=int, default=8, help="NMEA lines sent each tick")
    p.add_argument("--hz-start", type=float, default=5.0, help="Starting tick rate")
    p.add_argument("--hz-stop", type=float, default=40.0, help="Final tick rate")
    p.add_argument("--hz-step", type=float, default=5.0, help="Tick-rate increment")
    p.add_argument("--stage-seconds", type=float, default=6.0, help="Duration per stage")
    p.add_argument(
        "--max-runtime",
        type=float,
        default=0.0,
        help="Hard safety cap in seconds (0 = auto from profile).",
    )
    p.add_argument(
        "--fail-on-backlog",
        action="store_true",
        help="Return non-zero when backlog is detected (even without drops).",
    )
    p.add_argument("--stop-on-clog", action="store_true", help="Stop after first clogged stage")
    args = p.parse_args()
    raise SystemExit(asyncio.run(_probe(args)))


if __name__ == "__main__":
    main()
