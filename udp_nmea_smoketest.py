import argparse
import socket
import time


TEST_SENTENCES = [
    # Valid examples (with checksums)
    "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47",
    "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A",
]


def main() -> None:
    p = argparse.ArgumentParser(description="Send NMEA sentences to the bridge over UDP, and print UDP replies.")
    p.add_argument("--dest-host", required=True, help="Bridge UDP destination host/IP")
    p.add_argument("--dest-port", type=int, required=True, help="Bridge UDP destination port")
    p.add_argument("--listen-port", type=int, default=0, help="Local UDP bind port (0=random)")
    p.add_argument("--duration", type=float, default=20.0, help="Test duration in seconds")
    p.add_argument("--rate-hz", type=float, default=2.0, help="Loop rate (sentences sent per second per sentence set)")
    p.add_argument("--rx-window", type=float, default=0.3, help="Seconds to listen for replies after each sentence set")
    p.add_argument("--net-mode", default="udp_listen", choices=["udp_listen", "udp_remote"], help="For your own tracking; bridge config still matters")
    args = p.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.listen_port))
    sock.settimeout(0.2)

    local_host, local_port = sock.getsockname()
    print(f"[udp_nmea_smoketest] Bound UDP {local_host}:{local_port}")
    print(f"[udp_nmea_smoketest] Sending to {args.dest_host}:{args.dest_port}")

    end = time.time() + args.duration
    i = 0
    try:
        while time.time() < end:
            for s in TEST_SENTENCES:
                wire = (s + "\r\n").encode("ascii", errors="replace")
                sock.sendto(wire, (args.dest_host, args.dest_port))
                print(f"[udp_nmea_smoketest] TX: {s}")

                # Read any reply datagrams quickly
                t0 = time.time()
                while time.time() - t0 < args.rx_window:
                    try:
                        data, addr = sock.recvfrom(65535)
                    except socket.timeout:
                        break
                    try:
                        txt = data.decode(errors="replace").replace("\r", "\\r").rstrip("\n")
                    except Exception:
                        txt = repr(data)
                    print(f"[udp_nmea_smoketest] RX←{addr}: {txt}")

            i += 1
            if args.rate_hz > 0:
                time.sleep(1.0 / args.rate_hz)

    finally:
        sock.close()
        print("[udp_nmea_smoketest] Done.")


if __name__ == "__main__":
    main()