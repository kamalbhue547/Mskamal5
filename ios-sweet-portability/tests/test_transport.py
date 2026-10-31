import subprocess
import unittest
from unittest.mock import patch

from devicecheck.transport import (
    ADB_PROPERTIES, Device, SelectionError, ToolError, _property_value, _run,
    discover, parse_adb_devices, parse_fastboot_devices, read_adb_properties,
)


def completed(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class TransportTests(unittest.TestCase):
    def test_parse_adb_states_without_banner(self):
        out = "* daemon started successfully *\nList of devices attached\nSERIAL1\tdevice\nSERIAL2\tunauthorized\nSERIAL3\toffline\n"
        self.assertEqual(parse_adb_devices(out), [Device("SERIAL1", "device"), Device("SERIAL2", "unauthorized"), Device("SERIAL3", "offline")])

    def test_parse_no_permission(self):
        out = "List of devices attached\n????????????\tno permissions (user in plugdev group; are your udev rules wrong?)\n"
        self.assertEqual(parse_adb_devices(out)[0].state.split(" (")[0], "no permissions")

    def test_parse_fastboot_devices(self):
        self.assertEqual(parse_fastboot_devices("SERIAL\tfastboot\n"), [Device("SERIAL", "fastboot")])

    def test_adb_binary_missing(self):
        with patch("devicecheck.transport.shutil.which", return_value=None):
            with self.assertRaisesRegex(ToolError, "adb is not installed"):
                discover("adb")

    def test_fastboot_binary_missing(self):
        with patch("devicecheck.transport.shutil.which", return_value=None):
            with self.assertRaisesRegex(ToolError, "fastboot is not installed"):
                discover("fastboot")

    def test_auto_with_neither_tool_says_so(self):
        with patch("devicecheck.transport.shutil.which", return_value=None):
            with self.assertRaises(SelectionError) as context:
                discover("auto")
        self.assertIn("adb is not installed", str(context.exception))
        self.assertIn("fastboot is not installed", str(context.exception))

    def test_no_adb_device_is_helpful(self):
        with patch("devicecheck.transport._run", return_value="List of devices attached\n\n"):
            with self.assertRaisesRegex(SelectionError, "USB debugging"):
                discover("adb")

    def test_no_fastboot_device_is_helpful(self):
        with patch("devicecheck.transport._run", return_value=""):
            with self.assertRaisesRegex(SelectionError, "already in fastboot"):
                discover("fastboot")

    def test_unauthorized_adb_stops_auto_without_fallback(self):
        with patch("devicecheck.transport._run", return_value="SERIAL\tunauthorized\n") as runner:
            with self.assertRaisesRegex(SelectionError, "unauthorized"):
                discover("auto")
        self.assertEqual(runner.call_count, 1)

    def test_offline_and_recovery_are_rejected(self):
        for state in ("offline", "recovery", "sideload"):
            with self.subTest(state=state):
                with patch("devicecheck.transport._run", return_value=f"SERIAL\t{state}\n"):
                    with self.assertRaises(SelectionError):
                        discover("adb")

    def test_multiple_devices_fail_unless_explicitly_selected(self):
        with patch("devicecheck.transport._run", return_value="ONE\tdevice\nTWO\tdevice\n"):
            with self.assertRaisesRegex(SelectionError, "multiple"):
                discover("adb")
            self.assertEqual(discover("adb", "TWO").device.serial, "TWO")

    def test_unknown_serial_is_not_echoed(self):
        with patch("devicecheck.transport._run", return_value="ONE\tdevice\n"):
            with self.assertRaises(SelectionError) as context:
                discover("adb", "PRIVATE-SERIAL")
        self.assertNotIn("PRIVATE-SERIAL", str(context.exception))

    def test_auto_can_fall_back_to_fastboot_and_warn_about_missing_adb(self):
        def output(tool, args, operation):
            if tool == "adb":
                raise ToolError("adb is not installed")
            return "PRIVATE\tfastboot\n"
        with patch("devicecheck.transport._run", side_effect=output):
            connection = discover("auto")
        self.assertEqual(connection.transport, "fastboot")
        self.assertIn("adb is not installed", connection.warnings[0])

    def test_timeout_reports_actionable_error_without_serial(self):
        with patch("devicecheck.transport.shutil.which", return_value="/mock/adb"), \
             patch("devicecheck.transport.subprocess.run", side_effect=subprocess.TimeoutExpired(["adb", "PRIVATE"], 8)):
            with self.assertRaises(ToolError) as context:
                discover("adb")
        self.assertIn("timed out", str(context.exception))
        self.assertNotIn("PRIVATE", str(context.exception))

    def test_nonzero_exit_suppresses_stderr_and_serial(self):
        with patch("devicecheck.transport.shutil.which", return_value="/mock/adb"), \
             patch("devicecheck.transport.subprocess.run", return_value=completed(returncode=1, stderr="PRIVATE-SERIAL")):
            with self.assertRaises(ToolError) as context:
                discover("adb")
        self.assertIn("raw diagnostics suppressed", str(context.exception))
        self.assertNotIn("PRIVATE-SERIAL", str(context.exception))

    def test_runtime_allowlist_blocks_unsafe_commands_before_execution(self):
        commands = [
            ("adb", ["reboot"]),
            ("adb", ["shell", "getprop"]),  # full property dump
            ("adb", ["-s", "PRIVATE", "shell", "getprop", "ro.serialno"]),
            ("adb", ["-s", "PRIVATE", "shell", "setprop", "x", "y"]),
            ("fastboot", ["getvar", "product"]),
            ("fastboot", ["flash", "userdata", "image"]),
            ("fastboot", ["reboot"]),
            ("other", ["devices"]),
        ]
        with patch("devicecheck.transport.subprocess.run") as run:
            for tool, args in commands:
                with self.subTest(tool=tool, args=args):
                    with self.assertRaisesRegex(ToolError, "outside the read-only"):
                        _run(tool, args, "test")
        run.assert_not_called()

    def test_properties_are_individually_allowlisted(self):
        def output(tool, args, operation):
            self.assertEqual(tool, "adb")
            self.assertEqual(args[:4], ["-s", "PRIVATE", "shell", "getprop"])
            self.assertIn(args[4], ADB_PROPERTIES)
            return "some value\n"
        with patch("devicecheck.transport._run", side_effect=output) as runner:
            values = read_adb_properties("PRIVATE")
        self.assertEqual(runner.call_count, len(ADB_PROPERTIES))
        self.assertEqual(set(values), set(ADB_PROPERTIES))

    def test_empty_placeholders_multiline_and_controls_are_unknown(self):
        for raw in ("", "\n", "unknown\n", "N/A", "value\nmore", "abc\x1b[2J", "x" * 161):
            with self.subTest(raw=raw):
                self.assertIsNone(_property_value(raw))
        self.assertEqual(_property_value("Redmi Note 10 Pro\n"), "Redmi Note 10 Pro")

    def test_selected_serial_is_redacted_even_if_it_appears_in_a_property(self):
        self.assertIsNone(_property_value("Custom model PRIVATE-SERIAL\n", "PRIVATE-SERIAL"))
        self.assertIsNone(_property_value("private-serial\n", "PRIVATE-SERIAL"))
        self.assertEqual(_property_value("Redmi Note 10 Pro\n", "PRIVATE-SERIAL"), "Redmi Note 10 Pro")

    def test_failed_property_query_is_not_a_match(self):
        with patch("devicecheck.transport._run", side_effect=ToolError("adb connection lost")):
            with self.assertRaisesRegex(ToolError, "connection lost"):
                read_adb_properties("PRIVATE")


if __name__ == "__main__":
    unittest.main()
