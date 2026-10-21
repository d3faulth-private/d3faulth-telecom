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
    sub.add_parser("core-start", help="Start persistent isolated SCTP laboratory")
    sub.add_parser("core-status", help="Read persistent route measurements")
    sub.add_parser("core-stop", help="Stop persistent lab services")
    sub.add_parser("stp-start", help="Start isolated OsmoSTP server")
    sub.add_parser("stp-status", help="Check OsmoSTP and M3UA acknowledgement")
    sub.add_parser("signaling-state", help="Show verified transport/ASP states without inferring routing")
    sub.add_parser("asp-activate-test", help="Test ASPAC_ACK on managed local OsmoSTP")
    sub.add_parser("verify-lab", help="Consolidated read-only OsmoSTP readiness and transport test")
    sub.add_parser("verify-stp-capture", help="Capture M3UA management traffic and correlate with ASP activation")
    sub.add_parser("local-data-route", help="Attempt synthetic point-code DATA delivery between two localhost ASPs")
    sub.add_parser("delivery-demo", help="Verify receipt from a separate localhost destination (not SS7 routing)")
    evidence = sub.add_parser("route-audit", help="Correlate isolated lab checkpoint events without claiming SS7 route health")
    evidence.add_argument("file", help="JSONL checkpoint file")
    proof = sub.add_parser("route-proof", help="Audit four lab M3UA DATA checkpoints and STP capture references")
    proof.add_argument("file", help="JSON array of observations")
    capproof = sub.add_parser("pcap-proof", help="Verify referenced lab M3UA DATA frames in local PCAPs")
    capproof.add_argument("evidence", help="Four-stage evidence JSON file")
    capproof.add_argument("captures", help="Directory of local PCAP files")
    sub.add_parser("stp-stop", help="Stop the managed OsmoSTP server")
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
    elif args.cmd in ("core-start", "core-status", "core-stop"):
        from . import persistent
        operation = {"core-start": persistent.start, "core-status": persistent.state, "core-stop": persistent.stop}[args.cmd]
        try: print(json.dumps(operation(), indent=2))
        except RuntimeError as exc: parser.exit(2, f"ERROR: {exc}\\n")
    elif args.cmd in ("stp-start", "stp-status", "stp-stop"):
        from . import osmostp
        operation = {"stp-start": osmostp.start, "stp-status": osmostp.status, "stp-stop": osmostp.stop}[args.cmd]
        try: print(json.dumps(operation(), indent=2))
        except RuntimeError as exc: parser.exit(2, f"ERROR: {exc}\\n")
    elif args.cmd == "pcap-proof":
        from .pcap_proof import audit_verified_captures
        try: print(json.dumps(audit_verified_captures(args.evidence, args.captures), indent=2))
        except (OSError, ValueError) as exc: parser.exit(2, f"Capture proof error: {exc}\\n")
    elif args.cmd == "route-proof":
        from .route_proof import audit_route_file
        try: print(json.dumps(audit_route_file(args.file), indent=2))
        except (OSError, ValueError) as exc: parser.exit(2, f"Evidence error: {exc}\\n")
    elif args.cmd == "route-audit":
        from .route_evidence import audit_file
        try: print(json.dumps(audit_file(args.file), indent=2))
        except (OSError, ValueError) as exc: parser.exit(2, f"Evidence error: {exc}\\n")
    elif args.cmd == "delivery-demo":
        from .delivery_demo import run_delivery_demo
        print(json.dumps(run_delivery_demo(), indent=2))
    elif args.cmd == "local-data-route":
        from .route_verification import verify_route
        print(json.dumps(verify_route(), indent=2))
    elif args.cmd == "verify-stp-capture":
        from .integration import verify_capture_session
        print(json.dumps(verify_capture_session(), indent=2))
    elif args.cmd == "verify-lab":
        from .readiness import verify_lab
        print(json.dumps(verify_lab(), indent=2))
    elif args.cmd == "asp-activate-test":
        from .activation import activation_probe
        print(json.dumps(activation_probe(), indent=2))
    elif args.cmd == "signaling-state":
        from . import osmostp
        from .signaling_state import State
        stp = osmostp.status()
        model = State()
        if stp["running"]:
            model.transport(stp["m3ua_ack"])
            if stp["m3ua_ack"]:
                model.observe(3, 4)
            elif not model.error:
                model.error = "Process running; M3UA handshake unverified"
        result = {"osmostp": stp, "signaling": model.snapshot(),
                  "note": "ASP ACTIVE, routing, SCCP and MAP have not been verified"}
        print(json.dumps(result, indent=2))
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
