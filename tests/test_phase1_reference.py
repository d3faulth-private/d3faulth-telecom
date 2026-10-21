import tempfile
import unittest
from pathlib import Path
from d3faulth_telecom.phase1_reference import check_reference

class Phase1ReferenceTests(unittest.TestCase):
    def test_missing_commands_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"ref.xml"
            path.write_text("<vtydoc><node id='config-cs7-as'><command id='asp NAME'/></node></vtydoc>")
            result=check_reference(path)
            self.assertFalse(result["reference_compatible"])
            self.assertFalse(result["config_parse_verified"])
            self.assertFalse(result["routing_verified"])

    def test_invalid_xml_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"ref.xml"
            path.write_text("<not-closed")
            with self.assertRaises(Exception):
                check_reference(path)
