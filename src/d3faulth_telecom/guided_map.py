"""Guided offline MAP authorization demonstrations.

Synthetic subscribers only. No MAP packet generator, network I/O,
carrier endpoints, or changes to the real OsmoSTP configuration.
"""
from dataclasses import dataclass
from copy import deepcopy

@dataclass
class Subscriber:
    name: str
    msisdn: str
    imsi: str
    serving_vlr: str
    location_area: str

def fixtures():
    return {
        "TEST-SIM-001": Subscriber("TEST-SIM-001", "+15550100001", "001010000000001", "LAB-VLR-A", "LAB-LAC-01"),
        "TEST-SIM-002": Subscriber("TEST-SIM-002", "+15550100002", "001010000000002", "LAB-VLR-B", "LAB-LAC-02"),
    }

SCENARIOS = ("ati", "update-location")

def describe(scenario):
    if scenario not in SCENARIOS:
        raise ValueError("Choose ati or update-location")
    return {
        "scenario": scenario, "scope": "SYNTHETIC_OFFLINE",
        "subscriber": "TEST-SIM-001",
        "policy": "Compare denied and authorized synthetic requesters",
        "mutates_real_subscriber": False, "network_io": False,
        "requires_approval": scenario == "update-location",
    }

def execute(scenario, *, approved=False):
    spec = describe(scenario)
    if spec["requires_approval"] and not approved:
        raise PermissionError("Explicit approval required for synthetic state-change demonstration")
    before = fixtures()
    after = deepcopy(before)
    denied = {"requester": "UNTRUSTED-LAB", "decision": "DENY"}
    permitted = {"requester": "AUTHORIZED-LAB", "decision": "ALLOW"}
    if scenario == "ati":
        denied["disclosed"] = False
        permitted["subscriber_status"] = "AVAILABLE"
        permitted["location_area"] = after["TEST-SIM-001"].location_area
    else:
        denied["subscriber_state_changed"] = False
        after["TEST-SIM-001"].serving_vlr = "LAB-VLR-B"
        permitted["synthetic_vlr_updated"] = True
    observed_changed = before["TEST-SIM-001"].serving_vlr != after["TEST-SIM-001"].serving_vlr
    # The copies are intentionally discarded: no persistent subscriber state.
    return {**spec, "status": "SIMULATED", "unprivileged": denied,
            "authorized": permitted, "synthetic_state_changed_during_test": observed_changed,
            "state_restored": True, "real_map_executed": False,
            "note": "This is a policy simulation, not an HLR/VLR protocol or carrier vulnerability test"}

def run_guided(*, input_fn=input, output_fn=print):
    output_fn("D3FAULTH // GUIDED TELECOM SECURITY (OFFLINE SIMULATION)")
    output_fn("1) ATI authorization check  2) UpdateLocation integrity check  0) Exit")
    selection = input_fn("Select scenario: ").strip()
    if selection == "0":
        return {"status":"CANCELLED"}
    name = {"1":"ati","2":"update-location"}.get(selection)
    if name is None:
        return {"status":"INVALID_SELECTION"}
    info = describe(name)
    output_fn("Scope: SYNTHETIC_OFFLINE | Subscriber: TEST-SIM-001 | No network traffic")
    approved = False
    if info["requires_approval"]:
        approved = input_fn("Approve temporary synthetic UpdateLocation test? Type YES: ").strip() == "YES"
        if not approved:
            return {"status":"CANCELLED", "scenario":name}
    return execute(name, approved=approved)
