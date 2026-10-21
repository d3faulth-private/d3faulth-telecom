"""One-shot capture-and-activate workflow against managed localhost OsmoSTP."""
import threading
import time
from .activation import activation_probe
from .stp_capture import run_capture

def verify_capture_session(seconds=6):
    capture_result = {}
    def recording():
        try:
            capture_result["capture"] = run_capture(seconds)
        except (ValueError, RuntimeError) as exc:
            capture_result["error"] = str(exc)
    worker = threading.Thread(target=recording, daemon=True)
    worker.start()
    time.sleep(1.5)
    activation = activation_probe()
    worker.join(timeout=seconds + 10)
    evidence = capture_result.get("capture")
    return {
        "activation": activation,
        "capture": evidence,
        "capture_error": capture_result.get("error"),
        "verified_management_exchange": bool(
            activation.get("asp_active") == "ACTIVE"
            and evidence
            and evidence.get("aspup_ack_frames", 0) > 0
            and evidence.get("aspac_ack_frames", 0) > 0),
        "ss7_data_route_healthy": False,
        "ss7_data_routing": "UNVERIFIED",
        "note": "OsmoSTP management-plane capture only; no independent DATA destination receipt"
    }
