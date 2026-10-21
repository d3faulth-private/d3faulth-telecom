"""Read-only inspection of OsmoSTP's XML VTY command reference."""
from pathlib import Path
import xml.etree.ElementTree as ET

REQUIRED = {
    "config-cs7": (
        "asp NAME <0-65535> <0-65535> (sua|m3ua|ipa) (sctp|tcp)",
        "as NAME (sua|m3ua|ipa)",
    ),
    "config-cs7-as": (
        "asp NAME",
        "traffic-mode (broadcast | loadshare | roundrobin | override)",
        "routing-key RCONTEXT DPC",
    ),
    "config-cs7-asp": (
        "remote-ip (A.B.C.D|X:X::X:X) [primary]",
        "local-ip (A.B.C.D|X:X::X:X) [primary]",
        "role (sg|asp|ipsp)",
        "transport-role (client|server)",
    ),
}

def _tag(element):
    return element.tag.rsplit("}", 1)[-1]

def _norm(value):
    return " ".join((value or "").split())

def check_reference(reference):
    path = Path(reference)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("Reference XML too large")
    root = ET.parse(path).getroot()
    nodes = {}
    for element in root.iter():
        if _tag(element) != "node":
            continue
        commands = {_norm(child.get("id")) for child in element.iter()
                    if _tag(child) == "command"}
        nodes[element.get("id")] = commands
    present, missing = [], []
    for expected_node, commands in REQUIRED.items():
        for command in commands:
            normalized = _norm(command)
            matching_nodes = sorted(n for n, available in nodes.items() if n and normalized in available)
            # Some OsmoSTP releases name the parent CS7 VTY node differently.
            valid = expected_node in matching_nodes or (
                expected_node == "config-cs7" and any(
                    n.startswith("config-cs7") and n not in ("config-cs7-as", "config-cs7-asp")
                    for n in matching_nodes
                )
            )
            entry = {"node": expected_node, "command": command, "found_in": matching_nodes}
            (present if valid else missing).append(entry)
    return {
        "mode": "READ_ONLY", "reference": str(path),
        "discovered_nodes": sorted(str(n) for n in nodes if n),
        "matched": present, "missing": missing,
        "reference_compatible": not missing,
        "config_parse_verified": False, "routing_verified": False,
        "note": "VTY command presence does not establish valid config or operational routing",
    }
