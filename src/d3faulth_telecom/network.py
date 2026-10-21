"""v0.3 isolated three-process SCTP/M3UA management-path harness.

This is a *signaling transport* test, NOT an MSC, HLR, MAP or TCAP implementation.
A source ASP connects to a forwarding relay, which separately connects to a
destination ASP-up responder. Both links are strictly 127.0.0.1.
"""
import multiprocessing as mp
import queue
import socket
import time
from .protocol import encode_m3ua, decode_m3ua, ASPUP, ASPUP_ACK
from .lab import sctp_socket, event

HOST = "127.0.0.1"
RELAY_PORT = 29061
DEST_PORT = 29062

def _listener(port, ready, output, fault=False):
    try:
        with sctp_socket() as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((HOST, port))
            srv.listen(1)
            srv.settimeout(5)
            ready.set()
            with srv.accept()[0] as client:
                client.settimeout(4)
                data = client.recv(2048)
                decoded = decode_m3ua(data)
                if (decoded["class"], decoded["type"]) != ASPUP:
                    raise ValueError("Unexpected M3UA management frame")
                if not fault:
                    client.sendall(encode_m3ua(*ASPUP_ACK))
                output.put(("destination", "FAULT" if fault else "ACK"))
    except Exception as exc:
        ready.set()
        output.put(("destination", "ERROR:" + str(exc)))

def _relay(ready, output):
    try:
        with sctp_socket() as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, RELAY_PORT))
            server.listen(1)
            server.settimeout(5)
            ready.set()
            with server.accept()[0] as client:
                client.settimeout(4)
                packet = client.recv(2048)
                msg = decode_m3ua(packet)
                if (msg["class"], msg["type"]) != ASPUP:
                    raise ValueError("Unsupported management message")
                with sctp_socket() as upstream:
                    upstream.settimeout(4)
                    upstream.connect((HOST, DEST_PORT))
                    upstream.sendall(packet)
                    reply = upstream.recv(2048)
                    if reply:
                        client.sendall(reply)
                    output.put(("relay", "FORWARDED" if reply else "NO_ACK"))
    except Exception as exc:
        ready.set()
        output.put(("relay", "ERROR:" + str(exc)))

def _read(q):
    result = {}
    while True:
        try:
            key, value = q.get_nowait()
        except queue.Empty:
            break
        result[key] = value
    return result

def run_path(fail=False, timeout=7):
    """Run a two-hop local SCTP path. Uses isolated processes, never an external IP."""
    ready_destination, ready_relay = mp.Event(), mp.Event()
    q = mp.Queue()
    children = [
        mp.Process(target=_listener, args=(DEST_PORT, ready_destination, q, fail)),
        mp.Process(target=_relay, args=(ready_relay, q))
    ]
    results = {"mode": "ISOLATED LAB", "segments": [
        {"from": "ASP", "to": "RELAY", "status": "UNTESTED"},
        {"from": "RELAY", "to": "DESTINATION", "status": "UNTESTED"}], "protocol": "M3UA ASPUP/ACK"}
    try:
        children[0].start()
        if not ready_destination.wait(timeout):
            raise RuntimeError("Destination startup timeout")
        children[1].start()
        if not ready_relay.wait(timeout):
            raise RuntimeError("Relay startup timeout")
        with sctp_socket() as sock:
            sock.settimeout(4)
            sock.connect((HOST, RELAY_PORT))
            results["segments"][0]["status"] = "SCTP_UP"
            sock.sendall(encode_m3ua(*ASPUP))
            response = sock.recv(2048)
            results["segments"][0]["status"] = "HEALTHY" if response and decode_m3ua(response)["name"] == "ASPUP_ACK" else "FAILED"
        for p in children:
            p.join(timeout=2)
        details = _read(q)
        results["segments"][1]["status"] = "HEALTHY" if details.get("relay") == "FORWARDED" else "FAILED"
        results["details"] = details
        results["status"] = "HEALTHY" if all(s["status"] == "HEALTHY" for s in results["segments"]) else "FAILED"
    except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
        results["status"] = "FAILED"
        results["error"] = str(exc)
        event("error", "Multi-node path test failed", detail=str(exc))
    finally:
        for p in children:
            if p.is_alive():
                p.terminate()
            p.join(timeout=2)
        q.close()
    event("path", "Two-hop signaling transport path checked", status=results["status"], segments=results["segments"])
    return results
