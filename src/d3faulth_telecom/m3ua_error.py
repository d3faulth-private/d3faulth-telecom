"""Minimal decoder for OsmoSTP M3UA management ERR responses."""
import struct

ERRORS = {
    1: "Invalid Version",
    2: "Unsupported Message Class",
    3: "Unsupported Message Type",
    4: "Unsupported Traffic Handling Mode",
    5: "Unexpected Message",
    6: "Protocol Error",
    7: "Invalid Stream Identifier",
    9: "Invalid Stream Identifier",
    13: "Refused Management Blocking",
    14: "ASP Identifier Required",
    15: "Invalid ASP Identifier",
    17: "Invalid Parameter Value",
    18: "Parameter Field Error",
    19: "Unexpected Parameter",
    20: "Destination Status Unknown",
    21: "Invalid Network Appearance",
    22: "Missing Parameter",
    25: "Invalid Routing Context",
    26: "No Configured AS for ASP",
}

def decode_error(packet):
    if len(packet) < 16:
        return None
    version, reserved, cls, typ, size = struct.unpack("!BBBBI", packet[:8])
    if (version, reserved, cls, typ) != (1, 0, 0, 0) or size != len(packet):
        return None
    offset = 8
    while offset + 4 <= len(packet):
        tag, length = struct.unpack("!HH", packet[offset:offset+4])
        if length < 4 or offset + length > len(packet):
            break
        if tag == 12 and length >= 8:
            code = struct.unpack("!I", packet[offset+4:offset+8])[0]
            return {"code": code, "description": ERRORS.get(code, "Other M3UA error")}
        offset += (length + 3) & ~3
    return {"code": None, "description": "M3UA ERR without parsed error-code parameter"}
