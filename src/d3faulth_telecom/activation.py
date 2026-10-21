"""One-shot, localhost-only M3UA ASP UP -> ACTIVE verification.

A single SCTP association carries both messages. No DATA, SCCP, MAP,
subscriber information, routing manipulation, or external endpoints.
"""
import socket
from . import osmostp
from .protocol import encode_m3ua, decode_m3ua
from .sctp_m3ua import send_m3ua, SCTPSendError
from .signaling_state import State

ASPAC = (4, 1)
ASPAC_ACK = (4, 3)

def activation_probe():
    state = State()
    result = {"endpoint": "127.0.0.1:29065", "sctp": "UNVERIFIED",
              "asp_up": "UNVERIFIED", "asp_active": "UNVERIFIED",
              "routing": "UNVERIFIED", "last_response": None}
    if not osmostp.status()["running"]:
        result["error"] = "Managed OsmoSTP is not running"
        return result
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP) as sock:
            sock.settimeout(2)
            sock.connect((osmostp.HOST, osmostp.PORT))
            state.transport(True)
            result["sctp"] = state.sctp
            send_m3ua(sock, encode_m3ua(3, 1))
            reply = decode_m3ua(sock.recv(4096))
            result["last_response"] = reply["name"]
            if (reply["class"], reply["type"]) != (3, 4):
                result["error"] = "Expected ASPUP_ACK, got " + reply["name"]
                return result
            state.observe(3, 4)
            result["asp_up"] = state.asp
            send_m3ua(sock, encode_m3ua(*ASPAC))
            reply = decode_m3ua(sock.recv(4096))
            result["last_response"] = reply["name"]
            if (reply["class"], reply["type"]) == ASPAC_ACK:
                state.observe(*ASPAC_ACK)
                result["asp_active"] = state.asp
            else:
                result["error"] = "ASPAC_ACK not received (response: " + reply["name"] + ")"
    except (OSError, ValueError, SCTPSendError) as exc:
        result["error"] = str(exc)
    return result
