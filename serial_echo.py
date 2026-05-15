import argparse
import time

import serial


def main() -> None:
    p = argparse.ArgumentParser(description="Serial loop/echo tester for COM ports.")
    p.add_argument("--com", required=True, help="COM port, e.g. COM12")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--duration", type=float, default=20.0, help="Seconds to run")
    p.add_argument("--timeout", type=float, default=0.2, help="Read timeout (seconds)")
    args = p.parse_args()

    end = time.time() + args.duration
    ser = serial.Serial(args.com, baudrate=args.baud, timeout=args.timeout)
    print(f"[serial_echo] Opened {args.com} @ {args.baud}. Running for {args.duration}s...", flush=True)

    try:
        buf = bytearray()
        while time.time() < end:
            chunk = ser.read(1)
            if not chunk:
                continue
            buf += chunk
            if chunk == b"\n":
                # Echo back the exact received bytes
                ser.write(buf)
                line = buf.decode(errors="replace").rstrip("\r\n")
                print(f"[serial_echo] RX→TX: {line}", flush=True)
                buf.clear()

        print("[serial_echo] Done.", flush=True)
    finally:
        try:
            ser.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()