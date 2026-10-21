"""Loopback-only SCTP/M3UA management exchange and file-based events."""
import json
import os
import socket
import threading
from datetime import datetime, timezone
from pathlib import Path
from .protocol import encode_m3ua, decode_m3ua, ASPUP, ASPUP_ACK

HOST = "127.0.0.1"
PORT = 29055
STATE = Path(os.environ.get("D3FAULTH_STATE", str(Path.home() / ".local/state/d3faulth-telecom")))

def event(kind, message, **fields):
    STATE.mkdir(parents=True, exist_ok=True)
    record = {"at": datetime.now(timezone.utc).isoformat(), "kind": kind, "message": message, **fields}
    with (STATE / "events.jsonl").open("a", encoding="utf8") as out:
        out.write(json.dumps(record) + "\n")
    return record

def sctp_socket():
    try:
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP)
    except OSError as exc:
        raise RuntimeError("SCTP unavailable: enable/load Linux SCTP kernel support (sudo modprobe sctp)") from exc

def run_exchange(port: int = PORT, *, fail: bool = False, timeout: float = 3.0) -> dict:
    """Run one actual SCTP connection carrying M3UA ASPUP / ACK on loopback.

    Failure injection is local only. The test service never binds externally.
    """
    ready = threading.Event()
    errors = []
    result = {"mode": "ISOLATED LAB", "host": HOST, "port": port,
              "transport": "SCTP", "protocol": "M3UA", "connected": False, "m3ua_ack": False}

    def serve():
        try:
            with sctp_socket() as srv:
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind((HOST, port))
                srv.listen(1)
                srv.settimeout(timeout)
                ready.set()
                with srv.accept()[0] as peer:
                    peer.settimeout(timeout)
                    data = peer.recv(4096)
                    incoming = decode_m3ua(data)
                    event("recv", "Received M3UA management message", message_name=incoming["name"])
                    if (incoming["class"], incoming["type"]) != ASPUP:
                        raise ValueError("Unexpected message")
                    if not fail:
                        peer.sendall(encode_m3ua(*ASPUP_ACK))
                        event("send", "Sent ASPUP_ACK")
                    else:
                        event("fault", "Injected local M3UA ACK failure")
        except Exception as exc:
            errors.append(str(exc))
            ready.set()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    if not ready.wait(timeout):
        raise RuntimeError("Lab node startup timed out")
    if errors:
        raise RuntimeError(errors[0])
    try:
        with sctp_socket() as sock:
            sock.settimeout(timeout)
            sock.connect((HOST, port))
            result["connected"] = True
            event("link", "SCTP association established", endpoint=f"{HOST}:{port}")
            sock.sendall(encode_m3ua(*ASPUP))
            reply = sock.recv(4096)
            if reply:
                decoded = decode_m3ua(reply)
                result["m3ua_ack"] = (decoded["class"], decoded["type"]) == ASPUP_ACK
            result["status"] = "HEALTHY" if result["m3ua_ack"] else "FAILED"
            event("route", "M3UA ASPUP/ACK validation", status=result["status"])
    except Exception as exc:
        result["status"] = "FAILED"
        result["error"] = str(exc)
        event("error", "Signaling test failed", detail=str(exc))
    thread.join(timeout + 1)
    return result

def recent_events(limit=12):
    path = STATE / "events.jsonl"
    if not path.exists():
        return []
    from collections import deque
    with path.open(encoding="utf8") as f:
        return [json.loads(x) for x in deque(f, maxlen=limit) if x.strip()]
