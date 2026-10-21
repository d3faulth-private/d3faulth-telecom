"""Read-only inspection of an isolated OsmoSTP configuration and logs."""
from pathlib import Path
import re
from .lab import STATE

CONFIG = STATE / "osmo-stp.cfg"
LOG = STATE / "osmostp.log"

def audit_text(configuration, logs=""):
    as_defs = re.findall(r"(?m)^\s*as\s+([^\s]+)", configuration)
    asp_defs = re.findall(r"(?m)^\s*asp\s+([^\s]+)", configuration)
    contexts = re.findall(r"(?mi)\brouting-context\s+(\d+)", configuration)
    point_codes = re.findall(r"(?mi)\b(?:point-code|dpc)\s+(\S+)", configuration)
    issues = []
    if not as_defs:
        issues.append({"code": "NO_AS", "severity": "warning",
                       "message": "No explicit Application Server definition found"})
    if not asp_defs:
        issues.append({"code": "NO_STATIC_ASP", "severity": "info",
                       "message": "No static ASP definition found; dynamic ASP acceptance may be in use"})
    if not contexts:
        issues.append({"code": "NO_ROUTING_CONTEXT", "severity": "warning",
                       "message": "No explicit routing-context assignment found"})
    if not point_codes:
        issues.append({"code": "NO_POINT_CODES", "severity": "warning",
                       "message": "No explicit point-code or DPC definition found"})
    if "unable to uniquely identify the AS" in logs:
        issues.append({"code": "AS_AMBIGUOUS", "severity": "error",
                       "message": "Logs show incoming DATA could not be matched uniquely to an AS"})
    if "Invalid Routing Context" in logs:
        issues.append({"code": "INVALID_ROUTING_CONTEXT", "severity": "error",
                       "message": "Logs include M3UA Invalid Routing Context"})
    return {"mode": "READ_ONLY", "service_modified": False,
            "application_servers": as_defs, "asps": asp_defs,
            "routing_contexts": contexts, "point_codes": point_codes,
            "issues": issues, "routing": "UNVERIFIED",
            "note": "Static text inspection is not a substitute for OsmoSTP runtime route state"}

def audit_files(config=CONFIG, log=LOG):
    config = Path(config)
    log = Path(log)
    if not config.is_file():
        raise FileNotFoundError(f"Config file missing: {config}")
    if config.stat().st_size > 1024*1024:
        raise ValueError("Configuration exceeds review limit")
    logs = ""
    if log.is_file():
        with log.open(encoding="utf-8", errors="replace") as fh:
            from collections import deque
            logs = "".join(deque(fh, maxlen=500))
    return audit_text(config.read_text(encoding="utf-8"), logs)
