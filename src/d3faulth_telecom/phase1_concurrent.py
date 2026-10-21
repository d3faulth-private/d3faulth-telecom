"""Two concurrent, fixed-loopback ASP associations and synthetic DATA receipt test.

No process control; the operator starts the isolated candidate separately.
A successful receiver check is not PCAP corroboration.
"""
import select
import socket
import time
from .phase1_association import HOST, PORT, _await_ack, _read
from .protocol import encode_m3ua, ASPUP, ASPUP_ACK, ASPAC, ASPAC_ACK
from .sctp_m3ua import send_m3ua
from .m3ua_data import encode_data, decode_data, PC_A, PC_B, PAYLOAD
from .m3ua_error import decode_error

def _open_asp(address):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP)
    try:
        sock.settimeout(3.0)
        sock.bind((address, 0))
        sock.connect((HOST, PORT))
        record = {"source_ip": address, "sctp": "CONNECTED",
                  "asp_up": "UNVERIFIED", "asp_active": "UNVERIFIED",
                  "responses": [], "response_details": []}
        send_m3ua(sock, encode_m3ua(*ASPUP))
        if not _await_ack(sock, ASPUP_ACK, record):
            raise RuntimeError("ASPUP_ACK missing for " + address)
        record["asp_up"] = "ACK_VERIFIED"
        send_m3ua(sock, encode_m3ua(*ASPAC))
        if not _await_ack(sock, ASPAC_ACK, record):
            raise RuntimeError("ASPAC_ACK missing for " + address)
        record["asp_active"] = "ACK_VERIFIED"
        return sock, record
    except BaseException:
        sock.close()
        raise

def exercise(timeout=4.0):
    report = {"mode": "ISOLATED_CONCURRENT_ASPS", "gateway": f"{HOST}:{PORT}",
              "source": None, "destination": None, "concurrent_active": False,
              "data_sent": False, "destination_received": False,
              "payload_matches": False, "receiver_verified": False,
              "pcap_verified": False, "routing": "UNVERIFIED"}
    source = destination = None
    try:
        # Keep destination association open while activating source.
        destination, report["destination"] = _open_asp("127.0.0.3")
        source, report["source"] = _open_asp("127.0.0.2")
        report["concurrent_active"] = True
        send_m3ua(source, encode_data(PC_A, PC_B), stream=1)
        report["data_sent"] = True
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            ready, _, _ = select.select([source, destination], [], [], max(0, remaining))
            if not ready:
                break
            for sock in ready:
                packet = sock.recv(4096)
                if not packet:
                    report["error"] = "SCTP association closed"
                    return report
                if sock is destination:
                    try:
                        parsed = decode_data(packet)
                    except ValueError:
                        detail = decode_error(packet)
                        if detail:
                            report["destination_m3ua_error"] = detail
                        continue
                    report["destination_received"] = True
                    report["payload_matches"] = (
                        parsed["opc"] == PC_A and parsed["dpc"] == PC_B
                        and parsed["payload"] == PAYLOAD)
                    report["receiver_verified"] = report["payload_matches"]
                    if report["receiver_verified"]:
                        return report
                else:
                    detail = decode_error(packet)
                    if detail:
                        report["source_m3ua_error"] = detail
        report["error"] = "No matching destination DATA observed before timeout"
    except (OSError, RuntimeError, ValueError) as exc:
        report["error"] = str(exc)
    finally:
        for sock in (source, destination):
            if sock is not None:
                sock.close()
    return report
