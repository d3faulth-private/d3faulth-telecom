"""Read-only route-table preflight for the two isolated point codes.

Uses confirmed OsmoSTP VTY syntax, but does not claim that an AS name
is an accepted route linkset until the local parser verifies it.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from .phase1_candidate import CANDIDATE

ROUTES = (("0.2.7", "source-as"), ("0.5.2", "destination-as"))
ROUTE_COMMAND = "update route POINT_CODE MASK linkset LS_NAME"

def route_command_supported(reference):
    root = ET.parse(reference).getroot()
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "node" or node.get("id") != "config-cs7-rt":
            continue
        return any(child.get("id", "").startswith(ROUTE_COMMAND)
                   for child in node.iter() if child.tag.rsplit("}", 1)[-1] == "command")
    return False

def analyze(config_text):
    found = []
    missing = []
    for dpc, as_name in ROUTES:
        # Match only explicit static routes, not AS routing-key declarations.
        expr = r"(?m)^\s*update route\s+" + re.escape(dpc) + r"\s+\S+\s+linkset\s+" + re.escape(as_name) + r"(?:\s|$)"
        (found if re.search(expr, config_text) else missing).append({"dpc": dpc, "target": as_name})
    return {"mode": "READ_ONLY", "routes_present": found, "routes_missing": missing,
            "runtime_verified": False, "data_delivery_verified": False}

def candidate_with_routes(existing=CANDIDATE):
    path = Path(existing)
    content = path.read_text(encoding="utf-8")
    if "127.0.0.1 4240" not in content or "listen m3ua 29165" not in content:
        raise ValueError("Not the isolated Phase 1 candidate")
    if "update route " in content:
        raise ValueError("Candidate already contains explicit routes")
    # A /14 equivalent bit-mask in OsmoSTP 3.8.3 representation is
    # intentionally NOT assumed here. Format must be learned from installed VTY.
    return {"source": str(path), "inspection": analyze(content),
            "proposed_route_targets": list(ROUTES),
            "candidate_generated": False,
            "reason": "Route mask syntax and AS/linkset target semantics must be validated on OsmoSTP 2.1.0"}
