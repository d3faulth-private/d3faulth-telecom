"""Passive evidence audit for isolated M3UA signaling captures.

This module reads two exported, *lab-only* event logs. It never sends
signaling traffic, reads subscriber identities, or contacts a carrier.
A pair of matching observations is evidence of the same transaction seen at
two checkpoints; it does not alone prove OsmoSTP forwarded it.
"""
import hashlib
import json
from pathlib import Path

REQUIRED = {"transaction_id", "node", "direction", "payload_sha256", "timestamp"}
ALLOWED_NODES = {"lab-source", "lab-destination"}
ALLOWED_DIRECTIONS = {"sent", "received"}

def load_observations(path):
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {number}") from exc
            if not isinstance(row, dict) or not REQUIRED.issubset(row):
                raise ValueError(f"Missing evidence fields at line {number}")
            if row["node"] not in ALLOWED_NODES or row["direction"] not in ALLOWED_DIRECTIONS:
                raise ValueError(f"Unknown lab checkpoint at line {number}")
            if not isinstance(row["timestamp"], (int, float)):
                raise ValueError(f"Invalid timestamp at line {number}")
            digest = row["payload_sha256"]
            if not isinstance(digest, str) or len(digest) != 64:
                raise ValueError(f"Invalid payload digest at line {number}")
            rows.append(row)
    return rows

def correlate(rows, maximum_delay=10.0):
    sent = [e for e in rows if e["node"] == "lab-source" and e["direction"] == "sent"]
    received = [e for e in rows if e["node"] == "lab-destination" and e["direction"] == "received"]
    outcomes = []
    for origin in sent:
        candidates = [event for event in received if
                      event["transaction_id"] == origin["transaction_id"]
                      and event["payload_sha256"] == origin["payload_sha256"]
                      and 0 <= event["timestamp"] - origin["timestamp"] <= maximum_delay]
        outcomes.append({"transaction_id": origin["transaction_id"],
                         "status": "CORRELATED" if len(candidates) == 1 else "UNVERIFIED",
                         "matches": len(candidates)})
    return {"checkpoints": len(rows), "transactions": outcomes,
            "osmostp_routing": "UNVERIFIED",
            "note": "Matching observations cannot prove intermediary forwarding; independently captured M3UA DATA is required."}

def audit_file(path):
    return correlate(load_observations(path))
