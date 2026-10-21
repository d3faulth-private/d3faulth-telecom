"""SCTP M3UA sender: explicitly set PPID=3 (RFC 4666 / IANA).

The socket must already be connected to the loopback lab gateway.
Uses libsctp's documented sctp_sendmsg interface, because sendall()
leaves SCTP PPID at zero on Linux.
"""
import ctypes
import ctypes.util
import socket

M3UA_PPID = 3

class SCTPSendError(RuntimeError):
    pass

def send_m3ua(sock, payload, library=None, *, stream=0):
    if not isinstance(payload, bytes) or not payload:
        raise ValueError("M3UA payload must be nonempty bytes")
    if stream not in (0, 1):
        raise ValueError("Only lab management stream 0 and DATA stream 1 are supported")
    if len(payload) < 4:
        raise ValueError("M3UA header required")
    if payload[2] == 1 and stream != 1:
        raise ValueError("M3UA DATA must use stream 1")
    if payload[2] != 1 and stream != 0:
        raise ValueError("M3UA management must use stream 0")
    if sock.family != socket.AF_INET or sock.getpeername()[0] != "127.0.0.1":
        raise SCTPSendError("Only connected IPv4 loopback test sockets are supported")
    if library is None:
        name = ctypes.util.find_library("sctp") or "libsctp.so.1"
        try:
            library = ctypes.CDLL(name, use_errno=True)
        except OSError as exc:
            raise SCTPSendError("libsctp unavailable: install lksctp-tools/libsctp1") from exc
    send = library.sctp_sendmsg
    send.argtypes = [
        ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
        ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
        ctypes.c_uint16, ctypes.c_uint32, ctypes.c_uint32]
    send.restype = ctypes.c_int
    data = ctypes.create_string_buffer(payload)
    sent = send(sock.fileno(), data, len(payload), None, 0,
                socket.htonl(M3UA_PPID), 0, stream, 0, 0)
    if sent != len(payload):
        raise SCTPSendError(f"sctp_sendmsg returned {sent} for {len(payload)} bytes")
    return sent
