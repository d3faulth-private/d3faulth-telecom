"""Capture actual loopback OsmoSTP traffic for packet-backed verification.

Only the managed lab endpoint 127.0.0.1:29065 is captured. Neither this
module nor its commands send M3UA DATA or contact outside endpoints.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil
import subprocess
import time
from .lab import STATE
from . import osmostp

def run_capture(seconds=8):
    seconds = float(seconds)
    if not 1 <= seconds <= 30:
        raise ValueError("Capture duration must be between 1 and 30 seconds")
    if not shutil.which("tshark"):
        raise RuntimeError("tshark not installed")
    directory = STATE / "osmostp-captures"
    directory.mkdir(parents=True, exist_ok=True)
    filename = directory / ("osmostp-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".pcapng")
    command = ["tshark", "-i", "lo", "-f", "sctp port 29065", "-a", f"duration:{int(seconds)}",
               "-w", str(filename)]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=seconds+8, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Capture timed out") from exc
    if result.returncode or not filename.is_file():
        raise RuntimeError("Capture failed: " + result.stderr[-400:])
    return inspect(filename)

def inspect(filename):
    path = Path(filename).resolve()
    root = (STATE / "osmostp-captures").resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Only local OsmoSTP captures are accepted")
    command = ["tshark", "-r", str(path), "-Y", "m3ua", "-T", "fields",
               "-e", "frame.number", "-e", "m3ua.message_class",
               "-e", "m3ua.message_type", "-e", "sctp.ppid",
               "-E", "separator=,"]
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=10, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Capture decoding timed out") from exc
    if result.returncode:
        raise RuntimeError("Capture decoding failed: " + result.stderr[-400:])
    frames = []
    for line in result.stdout.splitlines():
        fields = line.split(",")
        if len(fields) != 4:
            continue
        try:
            frame, cls, typ, ppid = [int(part) for part in fields]
        except ValueError:
            continue
        frames.append({"frame": frame, "class": cls, "type": typ, "ppid": ppid})
    return {"capture": str(path), "frames": len(frames),
            "aspup_ack_frames": sum(f["class"] == 3 and f["type"] == 4 for f in frames),
            "aspac_ack_frames": sum(f["class"] == 4 and f["type"] == 3 for f in frames),
            "data_frames": sum(f["class"] == 1 for f in frames),
            "ss7_routing": "UNVERIFIED",
            "note": "Passive capture; endpoint-to-endpoint DATA delivery not established"}
