"""Single-run localhost M3UA DATA delivery experiment against OsmoSTP.

Bound to 127.0.0.2 and 127.0.0.3, fixed synthetic marker only.
No retries against arbitrary endpoints. Routing is UNVERIFIED unless the
destination socket actually receives and validates that marker.
"""
import hashlib
import json
import socket
import threading
import time
from . import osmostp
from .protocol import encode_m3ua, decode_m3ua
from .sctp_m3ua import send_m3ua
from .m3ua_data import encode_data, decode_data, PC_A, PC_B, PAYLOAD

STP = ("127.0.0.1", 29065)
SOURCE_IP, DEST_IP = "127.0.0.2", "127.0.0.3"

def _activate(sock):
    send_m3ua(sock, encode_m3ua(3, 1))
    reply = decode_m3ua(sock.recv(4096))
    if (reply["class"],reply["type"]) != (3,4):
        raise RuntimeError("ASPUP_ACK not received")
    send_m3ua(sock, encode_m3ua(4, 1))
    reply = decode_m3ua(sock.recv(4096))
    if (reply["class"],reply["type"]) != (4,3):
        raise RuntimeError("ASPAC_ACK not received")

def _connect(local_ip):
    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_SCTP)
    sock.settimeout(4)
    try:
        sock.bind((local_ip,0))
        sock.connect(STP)
        _activate(sock)
        return sock
    except BaseException:
        sock.close()
        raise

def exercise(timeout=5):
    report={"scope":"127.0.0.0/8", "sender":SOURCE_IP, "receiver":DEST_IP,
            "point_codes":[PC_A,PC_B], "asp_up":False, "destination_received":False,
            "payload_matches":False,"route_healthy":False, "status":"UNVERIFIED"}
    if not osmostp.status()["running"]:
        report["error"]="Managed OsmoSTP is not running"
        return report
    dest=None
    source=None
    try:
        dest=_connect(DEST_IP)
        report["destination_asp_active"]=True
        source=_connect(SOURCE_IP)
        report["asp_up"]=True
        send_m3ua(source, encode_data(PC_A,PC_B), stream=1)
        try:
            result=decode_data(dest.recv(4096))
            report["destination_received"]=True
            report["payload_matches"]=(result["payload"]==PAYLOAD and result["dpc"]==PC_B)
        except socket.timeout:
            report["error"]="No destination M3UA DATA received; inspect routing keys, destination AS and M3UA ERR frames"
        except Exception as exc:
            report["error"]="Received data could not be verified: "+str(exc)
        report["route_healthy"]=bool(report["destination_received"] and report["payload_matches"])
        report["status"]="VERIFIED" if report["route_healthy"] else "UNVERIFIED"
    except (OSError,RuntimeError,ValueError) as exc:
        report["error"]=str(exc)
    finally:
        for sock in (source,dest):
            if sock is not None:
                sock.close()
    return report
