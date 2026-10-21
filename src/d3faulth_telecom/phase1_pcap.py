"""Optional packet evidence for the fixed isolated candidate M3UA port."""
from pathlib import Path
from datetime import datetime, timezone
import shutil
import subprocess
import threading
import time
from .lab import STATE
from .phase1_concurrent import exercise

def verify_with_capture():
    result = {"mode":"ISOLATED_CANDIDATE_PCAP", "status":"UNVERIFIED",
              "routing":"UNVERIFIED", "pcap_verified":False}
    if not shutil.which("tshark"):
        result["error"] = "tshark not installed"
        return result
    directory = STATE / "phase1-captures"
    directory.mkdir(parents=True, exist_ok=True)
    filename = directory / ("phase1-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".pcapng")
    command = ["tshark", "-i", "lo", "-f", "sctp port 29165",
               "-a", "duration:12", "-w", str(filename)]
    try:
        proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        time.sleep(1.5)
        result["delivery"] = exercise()
        try:
            _, stderr = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise RuntimeError("Capture timed out")
        if proc.returncode != 0 or not filename.is_file():
            raise RuntimeError("Capture failed: " + stderr.decode("utf8", "replace")[-300:])
        result["capture"] = str(filename)
        decoded = subprocess.run(["tshark", "-r", str(filename), "-Y", "m3ua",
                                  "-T", "fields", "-e", "m3ua.message_class",
                                  "-e", "m3ua.message_type", "-e", "sctp.data_payload_proto_id"],
                                 capture_output=True, text=True, timeout=10, check=True)
        frames = []
        for line in decoded.stdout.splitlines():
            try:
                cls, typ, ppid = (int(v) for v in line.split("\t"))
            except ValueError:
                continue
            frames.append((cls, typ, ppid))
        data_count = sum(cls == 1 and typ == 1 and ppid == 3 for cls,typ,ppid in frames)
        result["data_frames"] = data_count
        result["pcap_verified"] = bool(result["delivery"].get("receiver_verified") and data_count >= 2)
        if result["pcap_verified"]:
            result["status"] = "VERIFIED"
            result["routing"] = "VERIFIED"
        else:
            result["reason"] = "Receiver proof or at least two M3UA DATA frames absent"
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        result["error"] = str(exc)
    return result
