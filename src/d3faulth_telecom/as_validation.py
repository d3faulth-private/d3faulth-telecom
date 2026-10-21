"""Offline validation of expected isolated AS/ASP topology; never edits OsmoSTP."""
import json
from pathlib import Path
from .routing_audit import audit_text, CONFIG

EXPECTED = {
    "mode": "ISOLATED",
    "nodes": [
        {"name": "source-asp", "host": "127.0.0.2", "point_code": 23, "routing_context": 100},
        {"name": "destination-asp", "host": "127.0.0.3", "point_code": 42, "routing_context": 200}
    ],
    "stp": {"host": "127.0.0.1", "port": 29065}
}

def validate_manifest(manifest):
    issues = []
    if not isinstance(manifest, dict) or manifest.get("mode") != "ISOLATED":
        return [{"code": "INVALID_MODE", "message": "An isolated manifest is required"}]
    stp = manifest.get("stp", {})
    if stp != {"host": "127.0.0.1", "port": 29065}:
        issues.append({"code": "INVALID_STP", "message": "STP must be fixed local lab endpoint"})
    nodes = manifest.get("nodes", [])
    if not isinstance(nodes, list) or len(nodes) != 2:
        return issues + [{"code": "INVALID_NODES", "message": "Exactly two lab ASPs required"}]
    hosts, pcs, contexts = [], [], []
    for node in nodes:
        if not isinstance(node, dict):
            issues.append({"code": "INVALID_NODE", "message": "Node must be an object"})
            continue
        hosts.append(node.get("host"))
        pcs.append(node.get("point_code"))
        contexts.append(node.get("routing_context"))
    if set(hosts) != {"127.0.0.2", "127.0.0.3"}:
        issues.append({"code": "INVALID_HOSTS", "message": "Only fixed loopback lab ASP addresses allowed"})
    for name, values in (("point codes", pcs), ("routing contexts", contexts)):
        if len(set(map(str, values))) != 2 or any(not isinstance(v, int) or v <= 0 for v in values):
            issues.append({"code": "INVALID_IDENTIFIERS", "message": "Two unique positive "+name+" required"})
    return issues

def compare_config(manifest=EXPECTED, configuration=None):
    errors = validate_manifest(manifest)
    if configuration is None:
        configuration = CONFIG.read_text(encoding="utf-8")
    audit = audit_text(configuration)
    desired = manifest.get("nodes", []) if not errors else []
    missing = []
    for node in desired:
        pc = str(node["point_code"])
        rc = str(node["routing_context"])
        if pc not in audit["point_codes"]:
            missing.append({"node":node["name"],"type":"point_code","value":pc})
        if rc not in audit["routing_contexts"]:
            missing.append({"node":node["name"],"type":"routing_context","value":rc})
    if not audit["application_servers"]:
        missing.append({"type":"application_server","value":"explicit AS association"})
    return {"mode":"READ_ONLY","manifest_issues":errors,"missing_expectations":missing,
            "observed":audit,"configuration_ready":False,
            "note":"Text inspection cannot prove AS/ASP binding or actual routing"}

def compare_snapshots(before, after):
    def codes(snapshot):
        return {issue["code"] for issue in snapshot.get("observed",{}).get("issues",[])}
    old, new = codes(before), codes(after)
    return {"resolved_issue_codes":sorted(old-new), "new_issue_codes":sorted(new-old),
            "before_missing":len(before.get("missing_expectations",[])),
            "after_missing":len(after.get("missing_expectations",[])),
            "routing":"UNVERIFIED"}
