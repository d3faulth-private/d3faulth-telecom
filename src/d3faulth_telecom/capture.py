"""Capture only the loopback M3UA lab flow. Never capture a public interface."""
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timezone
from .lab import STATE, PORT, event

_process = None
_file = None

def status():
    global _process
    active = _process is not None and _process.poll() is None
    return {"active": active, "file": str(_file) if _file else None}

def start():
    global _process, _file
    if status()["active"]:
        return status()
    tshark = shutil.which("tshark")
    if not tshark:
        raise RuntimeError("tshark not installed")
    folder = STATE / "captures"
    folder.mkdir(parents=True, exist_ok=True)
    _file = folder / ("loopback-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".pcapng")
    _process = subprocess.Popen([tshark, "-i", "lo", "-f", f"sctp port {PORT}",
                                 "-w", str(_file)], stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, start_new_session=True)
    try:
        _process.wait(timeout=0.7)
        raise RuntimeError("tshark exited early; check permissions for loopback capture")
    except subprocess.TimeoutExpired:
        pass
    event("capture", "Started lab loopback capture", file=str(_file))
    return status()

def stop():
    global _process
    if status()["active"]:
        _process.terminate()
        try:
            _process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _process.kill()
            _process.wait()
        event("capture", "Stopped loopback capture", file=str(_file))
    _process = None
    return status()

def open_wireshark():
    wireshark = shutil.which("wireshark")
    if not wireshark:
        raise RuntimeError("Wireshark not installed")
    args = [wireshark]
    if _file and _file.is_file():
        args += ["-r", str(_file)]
    subprocess.Popen(args, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return "Opened Wireshark directly" + (f" with {_file.name}" if len(args) > 1 else "")

def summarize(limit=12):
    if not _file or not _file.is_file() or not shutil.which("tshark"):
        return []
    try:
        result = subprocess.run(["tshark", "-r", str(_file), "-Y", "m3ua",
                                 "-T", "fields", "-e", "frame.time_relative", "-e", "_ws.col.Info"],
                                text=True, capture_output=True, timeout=4, check=False)
        return result.stdout.splitlines()[-limit:]
    except (OSError, subprocess.TimeoutExpired):
        return []
