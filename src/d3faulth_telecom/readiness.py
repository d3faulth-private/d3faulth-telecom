"""One-command, read-only laboratory readiness verification.

Checks actual local OsmoSTP response and the external capture stack.
Never changes configuration, uses subscriber data, or asserts routed DATA.
"""
import shutil
from . import osmostp
from .activation import activation_probe

def verify_lab():
    stp = osmostp.status()
    result = {
        "scope": "127.0.0.1 only",
        "checks": {
            "osmostp_process": "PASS" if stp["running"] else "FAIL",
            "m3ua_asp_up": "PASS" if stp["m3ua_ack"] else "UNVERIFIED",
            "m3ua_asp_active": "UNVERIFIED",
            "tshark_installed": "PASS" if shutil.which("tshark") else "MISSING",
            "wireshark_installed": "PASS" if shutil.which("wireshark") else "MISSING",
            "ss7_data_routing": "UNVERIFIED",
        },
        "route_healthy": False,
    }
    if stp["running"] and stp["m3ua_ack"]:
        active = activation_probe()
        result["activation"] = active
        if active.get("asp_active") == "ACTIVE":
            result["checks"]["m3ua_asp_active"] = "PASS"
    result["ready_for_capture_review"] = (
        result["checks"]["m3ua_asp_active"] == "PASS"
        and result["checks"]["tshark_installed"] == "PASS")
    result["next_requirement"] = (
        "Two independently configured lab ASPs, OsmoSTP M3UA DATA "
        "forwarding evidence and a verified destination receipt."
    )
    return result
