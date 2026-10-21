"""Persistent, localhost-only two-hop SCTP/M3UA transport laboratory.

The supervisor runs in a dedicated process and keeps its child processes alive.
No carrier interconnect, subscriber queries or telecom core nodes are provided.
"""
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from .lab import STATE
from .network import HOST, RELAY_PORT, DEST_PORT
from .protocol import encode_m3ua, decode_m3ua, ASPUP, ASPUP_ACK

PIDFILE = STATE / "persistent.pid"
HEALTHFILE = STATE / "persistent-health.json"
STOPFILE = STATE / "persistent.stop"

def _atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)

def _pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def state():
    pid = None
    try:
        pid = int(PIDFILE.read_text().strip())
    except (ValueError, OSError):
        pass
    data = {}
    try:
        data = json.loads(HEALTHFILE.read_text())
    except (ValueError, OSError):
        pass
    alive = _pid_alive(pid)
    return {"running": alive, "pid": pid if alive else None,
            "routes": data.get("routes", [] ) if alive else [],
            "observed_at": data.get("observed_at") if alive else None,
            "interval_seconds": data.get("interval_seconds", 2)}

def start():
    if state()["running"]:
        return state()
    STATE.mkdir(parents=True, exist_ok=True)
    STOPFILE.unlink(missing_ok=True)
    p = subprocess.Popen([sys.executable, "-m", "d3faulth_telecom.persistent", "serve"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=(STATE / "persistent-stderr.log").open("a"),
                         start_new_session=True, close_fds=True)
    for _ in range(35):
        time.sleep(.1)
        if state()["running"] and state()["routes"]:
            return state()
        if p.poll() is not None:
            raise RuntimeError("Supervisor exited. Inspect persistent-stderr.log")
    raise RuntimeError("Supervisor did not publish health in time")

def stop():
    if state()["running"]:
        STOPFILE.write_text("stop")
        for _ in range(35):
            if not state()["running"]:
                break
            time.sleep(.1)
    return state()

def _listen(port, forward=None):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, port))
        server.listen(8)
        server.settimeout(.5)
        while not STOPFILE.exists():
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            with conn:
                conn.settimeout(1.5)
                try:
                    request = conn.recv(2048)
                    decoded = decode_m3ua(request)
                    if (decoded["class"], decoded["type"]) != ASPUP:
                        continue
                    if forward is None:
                        conn.sendall(encode_m3ua(*ASPUP_ACK))
                    else:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP) as upstream:
                            upstream.settimeout(1.5)
                            upstream.connect((HOST, forward))
                            upstream.sendall(request)
                            response = upstream.recv(2048)
                            if response:
                                conn.sendall(response)
                except (OSError, ValueError):
                    continue

def _probe(port):
    started = time.monotonic()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP) as sock:
            sock.settimeout(1.5)
            sock.connect((HOST, port))
            sock.sendall(encode_m3ua(*ASPUP))
            response = decode_m3ua(sock.recv(2048))
            healthy = (response["class"], response["type"]) == ASPUP_ACK
            return {"status": "HEALTHY" if healthy else "FAILED",
                    "latency_ms": round((time.monotonic()-started)*1000, 2)}
    except (OSError, ValueError) as exc:
        return {"status": "FAILED", "error": str(exc)}

def _child(role):
    _listen(DEST_PORT if role == "destination" else RELAY_PORT,
            None if role == "destination" else DEST_PORT)

def serve():
    if state()["running"]:
        raise RuntimeError("Lab already running")
    STATE.mkdir(parents=True, exist_ok=True)
    PIDFILE.write_text(str(os.getpid()))
    children = []
    try:
        for role in ("destination", "relay"):
            children.append(subprocess.Popen([sys.executable, "-m", "d3faulth_telecom.persistent", role],
                                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                             stderr=(STATE / "persistent-stderr.log").open("a")))
        while not STOPFILE.exists():
            direct = _probe(DEST_PORT)
            path = _probe(RELAY_PORT)
            _atomic_json(HEALTHFILE, {
                "observed_at": time.time(), "interval_seconds": 2,
                "routes": [
                    {"from": "RELAY", "to": "DESTINATION", **direct},
                    {"from": "ASP CLIENT", "to": "RELAY", **path}
                ],
                "processes": {role: p.poll() is None for role,p in zip(("destination", "relay"), children)}
            })
            time.sleep(2)
    finally:
        STOPFILE.write_text("stop")
        for p in children:
            if p.poll() is None:
                p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        PIDFILE.unlink(missing_ok=True)
        HEALTHFILE.unlink(missing_ok=True)
        STOPFILE.unlink(missing_ok=True)

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv)>1 else ""
    if action == "serve":
        serve()
    elif action in ("destination", "relay"):
        _child(action)
    else:
        raise SystemExit("Expected serve, destination, or relay")
