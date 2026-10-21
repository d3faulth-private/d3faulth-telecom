"""Offline, privacy-first MSISDN field analysis for authorized capture files.

This module does not monitor any interface or interrogate subscribers.
Only explicitly named MSISDN protocol fields are considered.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

MAX_CAPTURE_BYTES = 100 * 1024 * 1024
MAX_JSON_BYTES = 32 * 1024 * 1024
MSISDN_FIELD = re.compile(r"(?:^|[._-])msisdn(?:$|[._-])", re.IGNORECASE)

def decode_tbcd(value):
    """Decode TBCD bytes (low nibble first; 0xF allowed only as final filler)."""
    if not isinstance(value, (bytes, bytearray)) or not value:
        raise ValueError("TBCD input must contain bytes")
    digits = []
    for index, byte in enumerate(value):
        for nibble_index, nibble in enumerate((byte & 15, byte >> 4)):
            if nibble == 15 and index == len(value)-1 and nibble_index == 1:
                return "".join(digits)
            if nibble > 9:
                raise ValueError("Invalid TBCD digit or filler position")
            digits.append(str(nibble))
    return "".join(digits)

def mask_msisdn(value):
    digits = re.sub(r"\D", "", str(value))
    if not 3 <= len(digits) <= 15:
        return None
    return "•" * max(0, len(digits)-2) + digits[-2:]

def _walk(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if MSISDN_FIELD.search(key):
                if isinstance(value, str):
                    yield key, value
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            yield key, item
            if isinstance(value, (dict, list)):
                yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)

def inspect_decoded_json(document):
    fields, total = {}, 0
    for name, value in _walk(document):
        masked = mask_msisdn(value)
        if masked is not None:
            total += 1
            fields[name] = fields.get(name, 0) + 1
    return {"mode":"OFFLINE_ONLY", "msisdn_fields_detected":total,
            "field_counts":fields, "numbers_exposed":False,
            "note":"Counts only explicitly named MSISDN fields decoded by tshark; no arbitrary payload scanning"}

def analyze_pcap(filename, *, tshark="tshark"):
    path = Path(filename).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in (".pcap", ".pcapng", ".cap"):
        raise ValueError("Expected a local PCAP/PCAPNG capture")
    if path.stat().st_size > MAX_CAPTURE_BYTES:
        raise ValueError("Capture exceeds offline review limit")
    if not shutil.which(tshark):
        raise RuntimeError("tshark must be installed")
    try:
        completed = subprocess.run(
            [tshark, "-r", str(path), "-T", "json", "-Y", "gsm_map || e164"],
            capture_output=True, timeout=40, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Offline tshark decoding timed out") from exc
    if completed.returncode:
        raise RuntimeError("tshark decode failed: " + completed.stderr.decode("utf8", "replace")[-250:])
    if len(completed.stdout) > MAX_JSON_BYTES:
        raise ValueError("Decoded capture exceeds analysis limit")
    document = json.loads(completed.stdout)
    result = inspect_decoded_json(document)
    result["capture"] = str(path)
    return result
