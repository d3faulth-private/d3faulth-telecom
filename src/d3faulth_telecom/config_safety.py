"""Read-only configuration preflight and explicit local backup/restore.

Never edits running OsmoSTP automatically. Restore requires explicit CLI action,
checks destination identity and refuses to overwrite a running service's config.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from .routing_audit import CONFIG, audit_files
from .as_validation import compare_config
from .lab import STATE

BACKUPS = STATE / "config-backups"

def _digest(data):
    return hashlib.sha256(data).hexdigest()

def preflight(config=CONFIG):
    path = Path(config)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    content = path.read_text(encoding="utf8")
    current = compare_config(configuration=content)
    audit = audit_files(config=path)
    warnings = []
    if "bind 127.0.0.1" not in content or "local-ip 127.0.0.1" not in content:
        warnings.append("Loopback-only bind not established in config text")
    if "no login" in content:
        warnings.append("VTY no-login line detected")
    return {"mode":"READ_ONLY", "path":str(path), "sha256":_digest(path.read_bytes()),
            "audit":audit, "manifest":current, "warnings":warnings,
            "configuration_ready":False,
            "runtime_verified":False,
            "note":"Static validation cannot prove syntax compatibility or live routing"}

def backup_config(config=CONFIG):
    path = Path(config).resolve()
    if path != CONFIG.resolve():
        raise ValueError("Only managed lab configuration may be backed up")
    if not path.is_file():
        raise FileNotFoundError(str(path))
    data = path.read_bytes()
    BACKUPS.mkdir(parents=True,exist_ok=True)
    timestamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target=BACKUPS/(timestamp+"-"+_digest(data)[:12]+".cfg")
    target.write_bytes(data)
    target.chmod(0o600)
    return {"backup":str(target),"sha256":_digest(data),"original":str(path)}

def verify_backup(filename):
    candidate=Path(filename).resolve()
    if not candidate.is_relative_to(BACKUPS.resolve()) or candidate.suffix!=".cfg":
        raise ValueError("Backup must be within managed backup directory")
    if not candidate.is_file() or candidate.stat().st_size > 1024*1024:
        raise ValueError("Backup missing or too large")
    data=candidate.read_bytes()
    suffix=candidate.stem.rsplit("-",1)[-1]
    if _digest(data)[:12]!=suffix:
        raise ValueError("Backup integrity check failed")
    return {"backup":str(candidate),"sha256":_digest(data),"valid":True}

def restore_backup(filename, *, expected_current_sha256, service_running):
    """Explicit restore only when service is stopped and current checksum matches."""
    if service_running:
        raise RuntimeError("Stop managed OsmoSTP before restoring a config")
    proof=verify_backup(filename)
    if not CONFIG.is_file():
        raise RuntimeError("Managed configuration is missing")
    current=CONFIG.read_bytes()
    if _digest(current)!=expected_current_sha256:
        raise RuntimeError("Current config changed; refusing to overwrite")
    replacement=Path(proof["backup"]).read_bytes()
    staged=CONFIG.with_name(CONFIG.name+".restore-pending")
    staged.write_bytes(replacement)
    staged.chmod(0o600)
    staged.replace(CONFIG)
    return {"restored":True,"config":str(CONFIG),"sha256":_digest(replacement),
            "note":"Service remains stopped; start it separately after reviewing configuration"}
