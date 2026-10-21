import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from d3faulth_telecom import config_safety

class ConfigSafetyTests(unittest.TestCase):
    def test_preflight_reports_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"osmo-stp.cfg"
            path.write_text("line vty\n bind 127.0.0.1\ncs7 instance 0\n listen m3ua 29065\n  local-ip 127.0.0.1\n")
            report=config_safety.preflight(path)
            self.assertFalse(report["configuration_ready"])
            self.assertFalse(report["runtime_verified"])

    def test_backup_integrity_and_explicit_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=Path(tmp)/"osmo-stp.cfg"
            cfg.write_text("original")
            folder=Path(tmp)/"backups"
            with patch.object(config_safety,"CONFIG",cfg), patch.object(config_safety,"BACKUPS",folder):
                backup=config_safety.backup_config(cfg)
                self.assertTrue(config_safety.verify_backup(backup["backup"])["valid"])
                cfg.write_text("modified")
                current=config_safety._digest(cfg.read_bytes())
                with self.assertRaises(RuntimeError):
                    config_safety.restore_backup(backup["backup"],expected_current_sha256=current,service_running=True)
                with self.assertRaises(RuntimeError):
                    config_safety.restore_backup(backup["backup"],expected_current_sha256="0"*64,service_running=False)
                result=config_safety.restore_backup(backup["backup"],expected_current_sha256=current,service_running=False)
                self.assertTrue(result["restored"])
                self.assertEqual(cfg.read_text(),"original")

    def test_rejects_altered_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=Path(tmp)/"osmo-stp.cfg"
            cfg.write_text("original")
            with patch.object(config_safety,"CONFIG",cfg), patch.object(config_safety,"BACKUPS",Path(tmp)/"backups"):
                backup=config_safety.backup_config(cfg)
                Path(backup["backup"]).write_text("tampered")
                with self.assertRaises(ValueError):
                    config_safety.verify_backup(backup["backup"])
