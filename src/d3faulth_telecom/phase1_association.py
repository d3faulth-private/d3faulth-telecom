"""Read-only evidence probe for two explicitly scoped laboratory ASPs.

Only contacts a separately started candidate on 127.0.0.1:29165.
No DATA, routing configuration, subscriber identifiers, or service control.
"""
import socket
from .protocol import encode_m3ua, decode_m3ua, ASPUP, ASPUP_ACK, ASPAC, ASPAC_ACK
from .sctp_m3ua import send_m3ua, SCTPSendError
from .m3ua_error import decode_error

HOST = "127.0.0.1"
PORT = 29165
PEERS = (("source-asp", "127.0.0.2"), ("destination-asp", "127.0.0.3"))

def _exchange(sock, sent, expected):
    send_m3ua(sock, encode_m3ua(*sent))
    raw = sock.recv(4096)
    message = decode_m3ua(raw)
    detail = {"name": message["name"], "class": message["class"],
              "type": message["type"], "length": message["length"],
              "raw_hex": raw.hex()}
    if (message["class"], message["type"]) == (0, 0):
        detail["m3ua_error"] = decode_error(raw)
    return (message["class"], message["type"]) == expected, detail

def probe_peer(name, address, *, socket_factory=socket.socket):
    if (name, address) not in PEERS:
        raise ValueError("Peer must be a fixed isolated test ASP")
    record = {"peer":name, "source_ip":address, "endpoint":f"{HOST}:{PORT}",
              "sctp":"UNVERIFIED", "asp_up":"UNVERIFIED",
              "asp_active":"UNVERIFIED", "routing":"UNVERIFIED",
              "responses":[], "response_details":[]}
    try:
        with socket_factory(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP) as sock:
            sock.settimeout(2.5)
            sock.bind((address, 0))
            sock.connect((HOST, PORT))
            record["sctp"] = "CONNECTED"
            ok, response = _exchange(sock, ASPUP, ASPUP_ACK)
            record["responses"].append(response["name"])
            record["response_details"].append(response)
            if not ok:
                record["error"] = "ASPUP_ACK not observed"
                record["unexpected_response"] = response
                return record
            record["asp_up"] = "ACK_VERIFIED"
            ok, response = _exchange(sock, ASPAC, ASPAC_ACK)
            record["responses"].append(response)
            if ok:
                record["asp_active"] = "ACK_VERIFIED"
            else:
                record["error"] = "ASPAC_ACK not observed"
                record["unexpected_response"] = response
    except (OSError, ValueError, SCTPSendError) as exc:
        record["error"] = str(exc)
    return record

def probe_candidate():
    results = [probe_peer(name, address) for name,address in PEERS]
    return {"mode":"ISOLATED_MANAGEMENT_ONLY","candidate_endpoint":f"{HOST}:{PORT}",
            "peers":results, "routing":"UNVERIFIED",
            "note":"ACK evidence is not DATA routing or receiver-side proof"}
