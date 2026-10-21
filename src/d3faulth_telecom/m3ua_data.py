"""Strict fixed laboratory M3UA DATA codec.

Only two lab point codes, one synthetic opaque payload, and SI=3. No external
destinations, no MAP messages, and no subscriber identifiers.
"""
import struct
from .protocol import ProtocolError

PC_A, PC_B = 23, 42
PAYLOAD = b"D3FAULTH-LOCAL-SYNTHETIC-DATA-01"
TAG_PROTOCOL_DATA = 0x0210

def encode_data(opc, dpc, payload=PAYLOAD):
    if (opc, dpc) not in ((PC_A, PC_B), (PC_B, PC_A)):
        raise ProtocolError("Only the two built-in lab point-code directions are allowed")
    if payload != PAYLOAD:
        raise ProtocolError("Payload must be the fixed synthetic lab marker")
    protocol_data = struct.pack("!IIBBBB", opc, dpc, 3, 0, 0, 0) + payload
    size = 4 + len(protocol_data)
    padding = (-size) % 4
    parameter = struct.pack("!HH", TAG_PROTOCOL_DATA, size) + protocol_data + b"\x00" * padding
    return struct.pack("!BBBBI", 1, 0, 1, 1, 8 + len(parameter)) + parameter

def decode_data(packet):
    if len(packet) < 24 or len(packet) % 4:
        raise ProtocolError("Truncated M3UA DATA")
    version, reserved, cls, typ, length = struct.unpack("!BBBBI", packet[:8])
    if (version, reserved, cls, typ, length) != (1, 0, 1, 1, len(packet)):
        raise ProtocolError("Invalid M3UA DATA header")
    tag, size = struct.unpack("!HH", packet[8:12])
    if tag != TAG_PROTOCOL_DATA or size < 16 or size > len(packet) - 8:
        raise ProtocolError("Invalid protocol-data parameter")
    opc, dpc, si, ni, mp, sls = struct.unpack("!IIBBBB", packet[12:24])
    payload = packet[24:8+size]
    if (opc,dpc) not in ((PC_A, PC_B), (PC_B,PC_A)) or si != 3 or payload != PAYLOAD:
        raise ProtocolError("Unexpected point code, service indicator, or payload")
    return {"opc":opc,"dpc":dpc,"si":si,"ni":ni,"payload":payload,"sls":sls}
