"""Small, standards-oriented M3UA management-message codec (RFC 4666).

This is NOT a MAP or SCCP interrogation implementation. Only handshake
management messages are supported. No subscriber identifiers are accepted.
"""
import struct

ASPUP = (3, 1)
ASPUP_ACK = (3, 4)

class ProtocolError(ValueError):
    pass

def encode_m3ua(message_class: int, message_type: int) -> bytes:
    if (message_class, message_type) not in {ASPUP, ASPUP_ACK}:
        raise ProtocolError("Only ASPUP and ASPUP_ACK are supported in v0.1")
    return struct.pack("!BBBBI", 1, 0, message_class, message_type, 8)

def decode_m3ua(packet: bytes) -> dict:
    if len(packet) < 8:
        raise ProtocolError("Truncated M3UA header")
    version, reserved, msg_class, msg_type, length = struct.unpack("!BBBBI", packet[:8])
    if version != 1 or reserved != 0 or length < 8 or length != len(packet) or length % 4:
        raise ProtocolError("Invalid M3UA header or length")
    return {"version": version, "class": msg_class, "type": msg_type, "length": length,
            "name": {ASPUP: "ASPUP", ASPUP_ACK: "ASPUP_ACK"}.get((msg_class, msg_type), "OTHER")}
