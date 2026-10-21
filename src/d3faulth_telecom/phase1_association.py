"""Bounded M3UA management-only probe for two isolated loopback ASPs."""
import socket
import struct
import time
from .protocol import encode_m3ua, decode_m3ua, ASPUP, ASPUP_ACK, ASPAC, ASPAC_ACK
from .sctp_m3ua import send_m3ua, SCTPSendError
from .m3ua_error import decode_error

HOST, PORT = "127.0.0.1", 29165
PEERS = (("source-asp", "127.0.0.2"), ("destination-asp", "127.0.0.3"))
TIMEOUT_SECONDS = 3.0
MAX_MESSAGES = 12

def _parameters(raw):
    params = []
    offset = 8
    while offset + 4 <= len(raw):
        tag, length = struct.unpack("!HH", raw[offset:offset + 4])
        if length < 4 or offset + length > len(raw):
            break
        params.append((tag, raw[offset + 4:offset + length]))
        offset += (length + 3) & ~3
    return params

def _read(sock):
    raw = sock.recv(4096)
    if not raw:
        raise ConnectionError("Peer closed SCTP association")
    msg = decode_m3ua(raw)
    code = (msg["class"], msg["type"])
    detail = {"name": "NOTIFY" if code == (0, 1) else ("ERROR" if code == (0, 0) else msg["name"]),
              "class": msg["class"], "type": msg["type"], "length": msg["length"],
              "raw_hex": raw.hex()}
    if code == (0, 0):
        detail["m3ua_error"] = decode_error(raw)
    if code == (0, 1):
        statuses, contexts = [], []
        for tag, payload in _parameters(raw):
            if tag == 0x000d and len(payload) == 4:
                status_type, status_info = struct.unpack("!HH", payload)
                statuses.append({"type": status_type, "info": status_info,
                                 "description": "AS_INACTIVE" if (status_type, status_info) == (1, 2) else "OTHER"})
            elif tag == 0x0006 and len(payload) % 4 == 0:
                contexts.extend(struct.unpack("!" + "I" * (len(payload) // 4), payload))
        detail["notify"] = {"statuses": statuses, "routing_contexts": contexts}
    return detail

def _exchange(sock, sent, expected):
    send_m3ua(sock, encode_m3ua(*sent))
    detail = _read(sock)
    return (detail["class"], detail["type"]) == expected, detail

def _await_ack(sock, expected, record):
    deadline = time.monotonic() + TIMEOUT_SECONDS
    for _ in range(MAX_MESSAGES):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sock.settimeout(remaining)
        try:
            detail = _read(sock)
        except socket.timeout:
            break
        record["responses"].append(detail["name"])
        record["response_details"].append(detail)
        observed = (detail["class"], detail["type"])
        if observed == expected:
            return True
        if observed == (0, 0):
            record["unexpected_response"] = detail
            return False
        if observed != (0, 1):
            record["unexpected_response"] = detail
    return False

def probe_peer(name, address, *, socket_factory=socket.socket):
    if (name, address) not in PEERS:
        raise ValueError("Peer must be a fixed isolated test ASP")
    record = {"peer": name, "source_ip": address, "endpoint": f"{HOST}:{PORT}",
              "sctp": "UNVERIFIED", "asp_up": "UNVERIFIED",
              "asp_active": "UNVERIFIED", "routing": "UNVERIFIED",
              "responses": [], "response_details": []}
    try:
        with socket_factory(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP) as sock:
            sock.settimeout(TIMEOUT_SECONDS)
            sock.bind((address, 0))
            sock.connect((HOST, PORT))
            record["sctp"] = "CONNECTED"
            send_m3ua(sock, encode_m3ua(*ASPUP))
            if not _await_ack(sock, ASPUP_ACK, record):
                record["error"] = "ASPUP_ACK not observed"
                return record
            record["asp_up"] = "ACK_VERIFIED"
            send_m3ua(sock, encode_m3ua(*ASPAC))
            if _await_ack(sock, ASPAC_ACK, record):
                record["asp_active"] = "ACK_VERIFIED"
            else:
                record["error"] = "ASPAC_ACK not observed"
    except (OSError, ValueError, SCTPSendError, ConnectionError) as exc:
        record["error"] = str(exc)
    return record

def probe_candidate():
    peers = [probe_peer(name, address) for name, address in PEERS]
    return {"mode": "ISOLATED_MANAGEMENT_ONLY",
            "candidate_endpoint": f"{HOST}:{PORT}", "peers": peers,
            "routing": "UNVERIFIED",
            "note": "Management acknowledgments do not prove DATA delivery"}
