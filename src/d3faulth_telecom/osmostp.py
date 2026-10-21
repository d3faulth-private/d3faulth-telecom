"""Isolated OsmoSTP integration. Binds M3UA to IPv4 loopback only.

Intentional constraints: no carrier interconnect, no subscriber operations,
no dynamic wide-area listening, no preconfigured Global Titles.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
from .lab import STATE
from .protocol import ASPUP, ASPUP_ACK, encode_m3ua, decode_m3ua

PORT = 29065
HOST = "127.0.0.1"
PID = STATE / "osmostp.pid"
CONFIG = STATE / "osmo-stp.cfg"
LOG = STATE / "osmostp.log"
META = STATE / "osmostp.json"

def config_text():
    # Restrict M3UA listener to loopback; VTY binds are version-specific and
    # must not be exposed on shared interfaces.
    return """!
log stderr
 logging filter all 1
 logging print category 1
 logging level lm3ua info
line vty
 no login
cs7 instance 0
 xua rkm routing-key-allocation dynamic-permitted
 listen m3ua 29065
  accept-asp-connections dynamic-permitted
  local-ip 127.0.0.1
"""

def _read_pid():
    try:
        return int(PID.read_text().strip())
    except (OSError, ValueError):
        return None

def _owned(pid):
    if not pid or pid <= 0:
        return False
    try:
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\\x00", b" ").decode("utf-8", "replace")
        return "osmo-stp" in cmd and str(CONFIG) in cmd
    except OSError:
        return False

def _probe():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP) as sock:
            sock.settimeout(1.5)
            sock.connect((HOST, PORT))
            sock.sendall(encode_m3ua(*ASPUP))
            response = sock.recv(4096)
            ack = decode_m3ua(response)
            return ack["class"] == ASPUP_ACK[0] and ack["type"] == ASPUP_ACK[1]
    except (OSError, ValueError):
        return False

def status():
    pid = _read_pid()
    owned = _owned(pid)
    return {"running": owned, "pid": pid if owned else None,
            "m3ua_ack": _probe() if owned else False,
            "host": HOST, "port": PORT, "implementation": "OsmoSTP"}

def start():
    executable = shutil.which("osmo-stp")
    if not executable:
        raise RuntimeError("osmo-stp is not installed; install Osmocom OsmoSTP first")
    current = status()
    if current["running"]:
        return current
    if PID.exists():
        raise RuntimeError("Unrecognized PID file; inspect state directory before restarting")
    STATE.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(config_text(), encoding="utf8")
    # Exit if another service uses our loopback SCTP port; never terminate it.
    with LOG.open("ab") as log:
        process = subprocess.Popen([executable, "-c", str(CONFIG)], stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=log, start_new_session=True)
    PID.write_text(str(process.pid))
    for _ in range(30):
        if process.poll() is not None:
            PID.unlink(missing_ok=True)
            raise RuntimeError("OsmoSTP exited; review " + str(LOG))
        if _probe():
            return status()
        time.sleep(.2)
    return status()  # Process running but ASPUP ACK unverified.

def stop():
    pid = _read_pid()
    if pid is None:
        return status()
    if not _owned(pid):
        raise RuntimeError("Refusing to stop unrecognized process")
    os.kill(pid, signal.SIGTERM)
    for _ in range(30):
        if not _owned(pid):
            PID.unlink(missing_ok=True)
            return status()
        time.sleep(.1)
    raise RuntimeError("OsmoSTP did not exit; inspect its state manually")
