"""Phone-side transport tests use synthetic properties, never a real device."""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devicecheck.__main__ import main
from devicecheck.transport import ADB_PROPERTIES, ToolError, _run


VALUES = {
    "ro.product.device": "sweet",
    "ro.build.product": "sweet",
    "ro.product.manufacturer": "Xiaomi",
    "ro.product.model": "Redmi Note 10 Pro",
    "ro.soc.model": "SM7150",
}


def run_main(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        result = main(args)
    return result, out.getvalue(), err.getvalue()


class AndroidLocalTests(unittest.TestCase):
    def run_with_properties(self, args, values=None):
        values = VALUES if values is None else values
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            self.assertEqual(argv[0], "/system/bin/getprop")
            self.assertEqual(len(argv), 2)
            self.assertIn(argv[1], ADB_PROPERTIES)
            self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
            self.assertTrue(kwargs["capture_output"])
            self.assertEqual(kwargs["timeout"], 8)
            self.assertFalse(kwargs["check"])
            self.assertFalse(kwargs.get("shell", False))
            return subprocess.CompletedProcess(argv, 0, values.get(argv[1], "") + "\n", "")

        with patch("devicecheck.transport.subprocess.run", side_effect=run), \
             patch("devicecheck.transport.shutil.which", side_effect=AssertionError("must not run adb or fastboot")):
            code, out, err = run_main(args)
        return code, out, err, calls

    def test_local_json_matches_reference_without_adb_or_serial(self):
        code, out, err, calls = self.run_with_properties(["--transport", "local", "--json"])
        self.assertEqual((code, err), (0, ""))
        report = json.loads(out)
        self.assertEqual(report["transport"], "local")
        self.assertEqual(report["status"], "supported")
        self.assertEqual(report["profile"]["id"], "sweet")
        self.assertTrue(any("sharing" in warning.lower() for warning in report["warnings"]))
        self.assertEqual([argv[1] for argv in calls], list(ADB_PROPERTIES))
        self.assertNotIn("ro.serialno", " ".join(" ".join(argv) for argv in calls))

    def test_local_unknown_when_properties_are_missing(self):
        values = {**VALUES, "ro.soc.model": ""}
        code, out, _, _ = self.run_with_properties(["--transport", "local", "--json"], values)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["status"], "unknown")
        self.assertIsNone(json.loads(out)["properties"]["ro.soc.model"])

    def test_local_profile_mismatch_is_not_a_universal_verdict(self):
        values = {**VALUES, "ro.product.device": "other", "ro.build.product": "other"}
        code, out, _, _ = self.run_with_properties(["--transport", "local", "--profile", "sweet", "--json"], values)
        self.assertEqual(code, 2)
        report = json.loads(out)
        self.assertEqual(report["status"], "incompatible")
        self.assertIn("profile only", report["summary"])

    def test_local_different_phone_is_unknown_without_an_explicit_profile(self):
        values = {**VALUES, "ro.product.device": "other", "ro.build.product": "other"}
        code, out, _, _ = self.run_with_properties(["--transport", "local", "--json"], values)
        self.assertEqual(code, 1)
        report = json.loads(out)
        self.assertEqual(report["status"], "unknown")
        self.assertIsNone(report["profile"])
        self.assertIn("not a judgment about future porting", report["summary"])

    def test_local_text_report_shows_transport_and_safety(self):
        code, out, err, _ = self.run_with_properties(["--transport", "local"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Transport: local", out)
        self.assertIn("not a hardware validation", out)
        self.assertIn("erases Android userdata", out)

    def test_local_mode_rejects_serial_before_calling_a_tool(self):
        for serial in ("PRIVATE-DEVICE", ""):
            with self.subTest(serial=serial):
                with patch("devicecheck.transport.subprocess.run") as run:
                    code, out, _ = run_main(["--transport", "local", "--serial", serial, "--json"])
                self.assertEqual(code, 3)
                self.assertIn("--serial", json.loads(out)["error"])
                self.assertNotIn("PRIVATE-DEVICE", out)
                run.assert_not_called()

    def test_invalid_profile_is_rejected_before_local_query(self):
        with patch("devicecheck.transport.subprocess.run") as run:
            code, out, _ = run_main(["--transport", "local", "--profile", "missing", "--json"])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["status"], "error")
        run.assert_not_called()

    def test_getprop_runtime_allowlist_blocks_private_or_write_commands(self):
        invalid = [
            ("getprop", []),
            ("getprop", ["ro.serialno"]),
            ("getprop", ["ro.product.device", "ro.serialno"]),
            ("getprop", ["--help"]),
            ("setprop", ["ro.product.device", "x"]),
        ]
        with patch("devicecheck.transport.subprocess.run") as run:
            for tool, args in invalid:
                with self.subTest(tool=tool, args=args):
                    with self.assertRaisesRegex(ToolError, "outside the read-only"):
                        _run(tool, args, "test")
        run.assert_not_called()

    def test_missing_android_getprop_is_actionable_and_redacted(self):
        with patch("devicecheck.transport.subprocess.run", side_effect=FileNotFoundError("PRIVATE-DETAIL")):
            code, out, _ = run_main(["--transport", "local", "--json"])
        self.assertEqual(code, 3)
        error = json.loads(out)["error"]
        self.assertIn("getprop", error)
        self.assertIn("Android", error)
        self.assertNotIn("PRIVATE-DETAIL", error)

    def test_local_getprop_failure_does_not_echo_raw_output(self):
        result = subprocess.CompletedProcess([], 1, "PRIVATE-STDOUT", "PRIVATE-STDERR")
        with patch("devicecheck.transport.subprocess.run", return_value=result):
            code, out, _ = run_main(["--transport", "local", "--json"])
        self.assertEqual(code, 3)
        self.assertNotIn("PRIVATE-STDOUT", out)
        self.assertNotIn("PRIVATE-STDERR", out)

    def test_local_timeout_does_not_echo_raw_details(self):
        exc = subprocess.TimeoutExpired(["getprop", "PRIVATE-DETAIL"], 8)
        with patch("devicecheck.transport.subprocess.run", side_effect=exc):
            code, out, _ = run_main(["--transport", "local", "--json"])
        self.assertEqual(code, 3)
        self.assertIn("timed out", json.loads(out)["error"])
        self.assertNotIn("PRIVATE-DETAIL", out)

    def test_local_values_reject_multiline_controls_and_placeholders(self):
        values = {**VALUES, "ro.product.model": "Secret\nextra\x1b[2J"}
        code, out, _, _ = self.run_with_properties(["--transport", "local", "--json"], values)
        self.assertEqual(code, 1)
        self.assertIsNone(json.loads(out)["properties"]["ro.product.model"])
        self.assertNotIn("Secret", out)

    def test_local_hides_custom_properties_by_default_and_warns_when_shown(self):
        values = {**VALUES, "ro.product.model": "CUSTOM-FAKE-IDENTIFIER"}
        code, out, _, _ = self.run_with_properties(["--transport", "local", "--json"], values)
        self.assertEqual(code, 1)
        report = json.loads(out)
        self.assertEqual(report["properties"]["ro.product.model"], "[hidden]")
        self.assertNotIn("CUSTOM-FAKE-IDENTIFIER", out)
        self.assertTrue(any("before sharing" in warning for warning in report["warnings"]))
        code, out, _, _ = self.run_with_properties(
            ["--transport", "local", "--json", "--show-properties"], values)
        self.assertEqual(code, 1)
        report = json.loads(out)
        self.assertEqual(report["properties"]["ro.product.model"], "CUSTOM-FAKE-IDENTIFIER")
        self.assertTrue(any("before sharing" in warning for warning in report["warnings"]))

    def test_real_subprocess_boundary_with_fake_getprop(self):
        with tempfile.TemporaryDirectory() as temp:
            fake = Path(temp) / "getprop"
            log = Path(temp) / "commands.jsonl"
            fake.write_text(
                f"#!{sys.executable}\n"
                "import json, sys\n"
                f"values = {VALUES!r}\n"
                f"with open({str(log)!r}, 'a', encoding='utf-8') as stream:\n"
                "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "if len(sys.argv) != 2:\n"
                "    sys.exit(99)\n"
                "print(values.get(sys.argv[1], ''))\n", encoding="utf-8")
            fake.chmod(0o755)
            with patch("devicecheck.transport.ANDROID_GETPROP", str(fake)):
                code, out, err = run_main(["--transport", "local", "--json"])
            self.assertEqual((code, err), (0, ""))
            self.assertEqual(json.loads(out)["transport"], "local")
            self.assertEqual(json.loads(out)["status"], "supported")
            commands = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(commands, [[key] for key in ADB_PROPERTIES])


if __name__ == "__main__":
    unittest.main()
