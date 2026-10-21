"""Read-only comparison against installed OsmoSTP VTY XML command reference."""
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

def check_reference(reference):
    path=Path(reference)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    if path.stat().st_size > 5*1024*1024:
        raise ValueError("Reference XML too large")
    root=ET.parse(path).getroot()
    nodes={node.attrib.get("id"): node for node in root.iter("node")}
    missing=[]
    present=[]
    for node_name,commands in REQUIRED.items():
        node=nodes.get(node_name)
        available={command.attrib.get("id") for command in node.iter("command")} if node is not None else set()
        for command in commands:
            entry={"node":node_name,"command":command}
            (present if command in available else missing).append(entry)
    return {"mode":"READ_ONLY", "reference":str(path),
            "matched":present, "missing":missing, "reference_compatible":not missing,
            "config_parse_verified":False, "routing_verified":False,
            "note":"VTY command presence is not equivalent to valid config or operational routing"}
