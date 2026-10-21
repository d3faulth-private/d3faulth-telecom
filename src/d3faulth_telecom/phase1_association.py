"""Read-only evidence probe for two explicitly scoped laboratory ASPs.

Only contacts a separately started candidate on 127.0.0.1:29165.
No DATA, routing configuration, subscriber identifiers, or service control.
"""
import socket
from .protocol import encode_m3ua, decode_m3ua, ASPUP, ASPUP_ACK, ASPAC, ASPAC_ACK
from .sctp_m3ua import send_m3ua, SCTPSendError

HOST = "127.0.0.1"
PORT = 29165
PEERS = (("source-asp", "127.0.0.2"), ("destination-asp", "127.0.0.3"))

def _exchange(sock, sent, expected):
    send_m3ua(sock, encode_m3ua(*sent))
    message = decode_m3ua(sock.recv(4096))
    return (message["class"], message["type"]) == expected, message["name"]

def probe_peer(name, address, *, socket_factory=socket.socket):
    if (name, address) not in PEERS:
        raise ValueError("Peer must be a fixed isolated test ASP")
    record = {"peer":name, "source_ip":address, "endpoint":f"{HOST}:{PORT}",
              "sctp":"UNVERIFIED", "asp_up":"UNVERIFIED",
              "asp_active":"UNVERIFIED", "routing":"UNVERIFIED",
              "responses":[]}
    try:
        with socket_factory(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP) as sock:
            sock.settimeout(2.5)
            sock.bind((address, 0))
            sock.connect((HOST, PORT))
            record["sctp"] = "CONNECTED"
            ok, response = _exchange(sock, ASPUP, ASPUP_ACK)
            record["responses"].append(response)
            if not ok:
                record["error"] = "ASPUP_ACK not observed"
                return record
            record["asp_up"] = "ACK_VERIFIED"
            ok, response = _exchange(sock, ASPAC, ASPAC_ACK)
            record["responses"].append(response)
            if ok:
                record["asp_active"] = "ACK_VERIFIED"
            else:
                record["error"] = "ASPAC_ACK not observed"
    except (OSError, ValueError, SCTPSendError) as exc:
        record["error"] = str(exc)
    return record

def probe_candidate():
    results = [probe_peer(name, address) for name,address in PEERS]
    return {"mode":"ISOLATED_MANAGEMENT_ONLY","candidate_endpoint":f"{HOST}:{PORT}",
            "peers":results, "routing":"UNVERIFIED",
            "note":"ACK evidence is not DATA routing or receiver-side proof"}
