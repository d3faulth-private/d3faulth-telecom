import argparse
import json
import shutil
import subprocess
from . import __version__
from .lab import run_exchange, recent_events, STATE

def main():
    parser = argparse.ArgumentParser(prog="telecom", description="D3FAULTH Telecom Lab • localhost-only SCTP/M3UA")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("dashboard", help="Interactive terminal topology (optional Textual dependency)")
    sub.add_parser("test", help="Run real localhost SCTP/M3UA ASPUP exchange")
    sub.add_parser("network-test", help="Run three-process two-hop local SCTP/M3UA test")
    sub.add_parser("network-fail", help="Run two-hop test with destination ACK failure")
    sub.add_parser("fail", help="Inject a local ASPUP_ACK failure")
    sub.add_parser("events", help="Show captured lab event log")
    sub.add_parser("doctor", help="Check dependencies and local setup")
    sub.add_parser("wireshark", help="Open Wireshark GUI directly")
    sub.add_parser("capture", help="Start loopback capture until Ctrl+C")
    args = parser.parse_args()
    if args.cmd in (None, "dashboard"):
        try:
            from .tui import TelecomApp
        except ImportError:
            parser.error("Dashboard needs Textual: pip install -e '.[tui]'")
        TelecomApp().run()
    elif args.cmd in ("test", "fail"):
        try:
            print(json.dumps(run_exchange(fail=args.cmd == "fail"), indent=2))
        except RuntimeError as exc:
            parser.exit(2, f"ERROR: {exc}\n")
    elif args.cmd in ("network-test", "network-fail"):
        from .network import run_path
        print(json.dumps(run_path(fail=args.cmd == "network-fail"), indent=2))
    elif args.cmd == "events":
        for entry in recent_events(30):
            print(json.dumps(entry))
    elif args.cmd == "doctor":
        import socket
        info = {"version": __version__, "state": str(STATE), "tshark": shutil.which("tshark"),
                "wireshark": shutil.which("wireshark"), "x-terminal-emulator": shutil.which("x-terminal-emulator")}
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP):
                info["sctp"] = "available"
        except OSError as exc:
            info["sctp"] = f"unavailable: {exc}"
        print(json.dumps(info, indent=2))
    elif args.cmd == "wireshark":
        from .capture import open_wireshark
        try: print(open_wireshark())
        except RuntimeError as exc: parser.exit(2, f"ERROR: {exc}\\n")
    elif args.cmd == "capture":
        import time
        from . import capture
        try:
            info = capture.start()
            print(f"Recording loopback to {info['file']}; press Ctrl+C to stop")
            while True: time.sleep(0.4)
        except KeyboardInterrupt:
            pass
        except RuntimeError as exc:
            parser.exit(2, f"ERROR: {exc}\\n")
        finally:
            capture.stop()

if __name__ == "__main__":
    main()
