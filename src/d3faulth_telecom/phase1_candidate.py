"""Generate a review-only, loopback-only OsmoSTP candidate.

No service start, configuration replacement or remote network access.
The template must pass an actual OsmoSTP parse/start test before use.
"""
from pathlib import Path
import hashlib
from .lab import STATE

CANDIDATE = STATE / "candidates" / "osmo-stp-phase1.cfg"
CONFIG_TEXT = """!
log stderr
 logging filter all 1
 logging print category 1
 logging level lm3ua info
line vty
 bind 127.0.0.1 4240
cs7 instance 0
 point-code 1
 xua rkm routing-key-allocation static-only
 asp source-asp 0 29165 m3ua sctp
  remote-ip 127.0.0.2
  local-ip 127.0.0.1
  role sg
  transport-role server
 as source-as m3ua
  asp source-asp
  traffic-mode override
  routing-key 100 23
 asp destination-asp 0 29165 m3ua sctp
  remote-ip 127.0.0.3
  local-ip 127.0.0.1
  role sg
  transport-role server
 as destination-as m3ua
  asp destination-asp
  traffic-mode override
  routing-key 200 42
 listen m3ua 29165
  local-ip 127.0.0.1
  accept-asp-connections pre-configured
"""

def inspect_candidate(content=CONFIG_TEXT):
    problems = []
    for required in ("bind 127.0.0.1 4240", "listen m3ua 29165", "local-ip 127.0.0.1",
                     "accept-asp-connections pre-configured",
                     "routing-key 100 23", "routing-key 200 42",
                     "remote-ip 127.0.0.2", "remote-ip 127.0.0.3"):
        if required not in content:
            problems.append("Missing: " + required)
    lines = {line.strip() for line in content.splitlines()}
    if "bind 127.0.0.1 4239" in lines or "listen m3ua 29065" in lines:
        problems.append("Candidate uses existing service port")
    if any(line.startswith("accept-asp-connections ") and line != "accept-asp-connections pre-configured" for line in lines):
        problems.append("Unsupported candidate ASP acceptance policy")
    if "xua rkm routing-key-allocation static-only" not in lines:
        problems.append("Expected static routing-key allocation not configured")
    return {"mode":"OFFLINE_REVIEW", "issues":problems,
            "syntax_verified":False, "routing_verified":False,
            "note":"Candidate text is not proof of accepted OsmoSTP syntax or delivery"}

def write_candidate(path=CANDIDATE):
    path=Path(path)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing candidate: {path}")
    check=inspect_candidate()
    if check["issues"]:
        raise ValueError(check["issues"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CONFIG_TEXT, encoding="utf-8")
    path.chmod(0o600)
    return {"candidate":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "review":check, "service_modified":False}
