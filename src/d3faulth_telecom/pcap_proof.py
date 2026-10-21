"""Verify that referenced STP M3UA DATA frames actually exist in a PCAP.

Only offline, explicitly supplied local capture files are read. This does not
configure or send signaling, and cannot by itself establish STP routing.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path
from .route_proof import verify_route_evidence

HEX = re.compile(r"^[0-9a-f]{64}$")

def inspect_capture(path, frames, tshark="tshark"):
    file = Path(path).resolve()
    if not file.is_file() or file.stat().st_size > 64_000_000:
        raise ValueError("Capture missing or exceeds 64MB review limit")
    if not shutil.which(tshark):
        raise RuntimeError("tshark not installed")
    if not frames or any(not isinstance(n, int) or n < 1 for n in frames):
        raise ValueError("Frame numbers must be positive integers")
    proc = subprocess.run([tshark, "-r", str(file), "-Y", "m3ua && m3ua.message_class == 1",
                           "-T", "fields", "-e", "frame.number", "-e", "sctp.ppid",
                           "-e", "frame.time_epoch", "-E", "separator=,"],
                          text=True, capture_output=True, timeout=15, check=False)
    if proc.returncode:
        raise RuntimeError("tshark decoding failed: " + proc.stderr[:250])
    observed = {}
    for row in proc.stdout.splitlines():
        fields = row.split(",")
        if len(fields) < 3:
            continue
        try:
            frame = int(fields[0])
            ppid = int(fields[1])
            epoch = float(fields[2])
        except ValueError:
            continue
        if frame in frames:
            observed[frame] = {"ppid": ppid, "epoch": epoch}
    return observed

def audit_verified_captures(evidence_path, capture_root):
    records = json.loads(Path(evidence_path).read_text(encoding="utf8"))
    base = verify_route_evidence(records)
    if base["status"] != "EVIDENCE_COMPLETE":
        return {"status": "UNVERIFIED", "route_healthy": False, "reason": base["reason"]}
    root = Path(capture_root).resolve()
    stages = {r["stage"]: r for r in records}
    inspected = []
    for stage in ("stp-rx", "stp-tx"):
        record = stages[stage]
        capture_file = (root / record["capture_file"]).resolve()
        if not capture_file.is_relative_to(root):
            return {"status": "UNVERIFIED", "route_healthy": False,
                    "reason": "Capture path outside evidence directory"}
        try:
            frames = inspect_capture(capture_file, [record["frame_number"]])
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            return {"status": "UNVERIFIED", "route_healthy": False, "reason": str(exc)}
        observed = frames.get(record["frame_number"])
        if not observed or observed["ppid"] != 3:
            return {"status": "UNVERIFIED", "route_healthy": False,
                    "reason": f"{stage} M3UA DATA frame/PPID not verified"}
        inspected.append({"stage": stage, "frame": record["frame_number"], "ppid": observed["ppid"]})
    return {"status": "CAPTURE_CORRELATED", "route_healthy": False,
            "observations": inspected,
            "reason": "Referenced DATA frames found; independent capture origin and payload matching still required"}
