import socket
import unittest
from unittest.mock import Mock, patch
from d3faulth_telecom.sctp_m3ua import M3UA_PPID, SCTPSendError, send_m3ua

class FakeCall:
    def __init__(self, returned):
        self.argtypes = None
        self.restype = None
        self.returned = returned
        self.arguments = None
    def __call__(self, *args):
        self.arguments = args
        return self.returned

class M3UAPPIDTests(unittest.TestCase):
    def test_uses_network_order_ppid_three(self):
        payload = b"\x01\x00\x03\x01\x00\x00\x00\x08"
        lib = Mock()
        lib.sctp_sendmsg = FakeCall(len(payload))
        sock = Mock(family=socket.AF_INET)
        sock.getpeername.return_value = ("127.0.0.1", 29065)
        sock.fileno.return_value = 9
        self.assertEqual(send_m3ua(sock, payload, lib), len(payload))
        self.assertEqual(lib.sctp_sendmsg.arguments[5], socket.htonl(M3UA_PPID))
        self.assertEqual(lib.sctp_sendmsg.arguments[7], 0)

    def test_rejects_non_loopback_endpoint(self):
        sock = Mock(family=socket.AF_INET)
        sock.getpeername.return_value = ("10.10.10.5", 29065)
        with self.assertRaises(SCTPSendError):
            send_m3ua(sock, b"x", Mock())

    def test_rejects_short_send(self):
        lib = Mock()
        lib.sctp_sendmsg = FakeCall(-1)
        sock = Mock(family=socket.AF_INET)
        sock.getpeername.return_value = ("127.0.0.1", 29065)
        with self.assertRaises(SCTPSendError):
            send_m3ua(sock, b"message", lib)
