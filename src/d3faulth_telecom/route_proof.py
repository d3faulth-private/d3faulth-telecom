"""Conservative proof of delivery through a lab STP.

Evidence must come from independently recorded source, STP ingress,
STP egress and destination checkpoints. This validates records only;
it never generates M3UA DATA or touches network interfaces.
"""
import json
from pathlib import Path

STAGES = ("source-tx", "stp-rx", "stp-tx", "destination-rx")
MAX_SPAN = 10.0

def verify_route_evidence(events):
    if not isinstance(events, list) or not events:
        return {"status": "UNVERIFIED", "reason": "No route evidence"}
    ids = {e.get("transaction_id") for e in events if isinstance(e, dict)}
    if len(ids) != 1 or None in ids:
        return {"status": "UNVERIFIED", "reason": "Ambiguous or missing transaction ID"}
    matches = {}
    for stage in STAGES:
        candidates = [e for e in events if isinstance(e, dict) and e.get("stage") == stage]
        if len(candidates) != 1:
            return {"status": "UNVERIFIED", "reason": f"Expected exactly one {stage} checkpoint"}
        matches[stage] = candidates[0]
    records = [matches[k] for k in STAGES]
    digest = records[0].get("payload_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        return {"status": "UNVERIFIED", "reason": "Invalid payload digest"}
    if any(r.get("payload_sha256") != digest for r in records):
        return {"status": "FAILED", "reason": "Payload differs between checkpoints"}
    if any(r.get("protocol") != "M3UA-DATA" for r in records):
        return {"status": "UNVERIFIED", "reason": "Missing M3UA DATA protocol evidence"}
    try:
        times = [float(r["timestamp"]) for r in records]
    except (KeyError, ValueError, TypeError):
        return {"status": "UNVERIFIED", "reason": "Missing timestamp"}
    if any(b < a for a,b in zip(times, times[1:])) or times[-1] - times[0] > MAX_SPAN:
        return {"status": "UNVERIFIED", "reason": "Invalid route timeline"}
    if not all(r.get("capture_file") and r.get("frame_number") for r in records[1:3]):
        return {"status": "UNVERIFIED", "reason": "No STP packet-capture references"}
    if records[-1].get("receipt_verified") is not True:
        return {"status": "UNVERIFIED", "reason": "Destination receipt not verified"}
    return {"status": "EVIDENCE_COMPLETE",
            "reason": "Four consistent checkpoint records; capture authenticity requires independent inspection",
            "transaction_id": records[0]["transaction_id"],
            "route_healthy": False}

def audit_route_file(filename):
    source = Path(filename)
    if not source.is_file() or source.stat().st_size > 2_000_000:
        raise ValueError("Evidence file missing or too large")
    events = json.loads(source.read_text(encoding="utf8"))
    return verify_route_evidence(events)
