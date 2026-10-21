import struct
import unittest
from d3faulth_telecom.m3ua_error import decode_error

class M3UAErrorTests(unittest.TestCase):
    def test_invalid_stream_identifier(self):
        packet = struct.pack("!BBBBIHHI", 1, 0, 0, 0, 16, 12, 8, 9)
        result = decode_error(packet)
        self.assertEqual(result["code"], 9)
        self.assertIn("Stream", result["description"])

    def test_regular_management_message_is_not_err(self):
        packet = struct.pack("!BBBBI", 1, 0, 3, 4, 8)
        self.assertIsNone(decode_error(packet))
