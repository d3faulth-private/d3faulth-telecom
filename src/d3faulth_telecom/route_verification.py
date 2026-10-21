"""One command: capture actual local M3UA DATA traffic and verify destination receipt."""
import threading
import time
from .local_route import exercise
from .stp_capture import run_capture

def verify_route():
    capture_holder={}
    def record():
        try: capture_holder["data"]=run_capture(8)
        except (OSError, ValueError, RuntimeError) as exc: capture_holder["error"]=str(exc)
    thread=threading.Thread(target=record,daemon=True)
    thread.start()
    time.sleep(1.25)
    delivery=exercise()
    thread.join(12)
    capture=capture_holder.get("data")
    frames=capture.get("data_frames",0) if capture else 0
    passed=bool(delivery.get("destination_received") and delivery.get("payload_matches") and frames >= 2)
    return {"mode":"ISOLATED-OSMOSTP-DATA", "delivery":delivery, "capture":capture,
            "capture_error":capture_holder.get("error"),
            "m3ua_data_frames":frames,
            "route_healthy":passed, "status":"VERIFIED" if passed else "UNVERIFIED",
            "reason":("Destination payload received with DATA observed in loopback PCAP" if passed
                      else "Destination delivery, OsmoSTP routing configuration, or packet evidence incomplete")}
