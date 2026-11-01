"""Default reports must not expose synthetic property values, even in JSON."""

import contextlib
import io
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from devicecheck.__main__ import main
from devicecheck.transport import ADB_PROPERTIES


SERIAL = "SYNTHETIC-PRIVATE-SERIAL"
SWEET = {
    "ro.product.device": "sweet",
    "ro.build.product": "sweet",
    "ro.product.manufacturer": "Xiaomi",
    "ro.product.model": "Redmi Note 10 Pro",
    "ro.soc.model": "SM7150",
}


def run_mocked(mode, arguments=(), values=None):
    values = SWEET if values is None else values
    calls = []

    def which(tool):
        return f"/mock/{tool}" if tool in {"adb", "fastboot"} else None

    def run(argv, **kwargs):
        calls.append(argv)
        tool = Path(argv[0]).name
        if tool == "adb" and argv[1:] == ["devices"]:
            output = f"List of devices attached\n{SERIAL}\tdevice\n"
        elif tool == "adb" and len(argv) == 6 and argv[1:5] == ["-s", SERIAL, "shell", "getprop"]:
            output = values.get(argv[5], "") + "\n"
        elif tool == "getprop" and len(argv) == 2:
            output = values.get(argv[1], "") + "\n"
        else:
            raise AssertionError(f"unexpected command: {argv}")
        return subprocess.CompletedProcess(argv, 0, output, "")

    out, err = io.StringIO(), io.StringIO()
    with patch("devicecheck.transport.shutil.which", side_effect=which), \
         patch("devicecheck.transport.subprocess.run", side_effect=run), \
         contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(["--transport", mode, *arguments])
    return code, out.getvalue(), err.getvalue(), calls


class ReportPrivacyTests(unittest.TestCase):
    def test_default_output_hides_custom_values_for_every_key_and_transport(self):
        for mode in ("local", "adb"):
            for key in ADB_PROPERTIES:
                for arguments in ((), ("--json",)):
                    with self.subTest(mode=mode, key=key, arguments=arguments):
                        secret = "SYNTHETIC-PRIVATE-PROPERTY-" + key
                        values = {**SWEET, key: secret}
                        _, out, err, _ = run_mocked(mode, arguments, values)
                        self.assertNotIn(secret, out + err)
                        self.assertNotIn(SERIAL, out + err)
                        if arguments:
                            report = json.loads(out)
                            self.assertTrue(report["properties_hidden"])
                            self.assertEqual(report["properties"][key], "[hidden]")

    def test_show_properties_is_explicit_and_works_in_text_and_json(self):
        value = "SYNTHETIC-CUSTOM-PROPERTY"
        values = {**SWEET, "ro.hardware": value}
        for mode in ("local", "adb"):
            for arguments in (("--show-properties",), ("--show-properties", "--json")):
                with self.subTest(mode=mode, arguments=arguments):
                    code, out, err, _ = run_mocked(mode, arguments, values)
                    self.assertEqual((code, err), (0, ""))
                    self.assertIn(value, out)
                    self.assertNotIn(SERIAL, out)
                    self.assertIn("before sharing", out.lower())
                    if "--json" in arguments:
                        report = json.loads(out)
                        self.assertFalse(report["properties_hidden"])
                        self.assertEqual(report["properties"]["ro.hardware"], value)

    def test_missing_values_are_distinguishable_from_hidden_values(self):
        code, out, _, _ = run_mocked("local", ("--json",), {**SWEET, "ro.soc.model": ""})
        report = json.loads(out)
        self.assertEqual(code, 1)
        self.assertIsNone(report["properties"]["ro.soc.model"])
        self.assertEqual(report["properties"]["ro.product.model"], "[hidden]")
        self.assertTrue(report["properties_hidden"])

    def test_human_label_is_clear_but_json_status_and_exit_code_are_stable(self):
        code, text, err, _ = run_mocked("local")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Result: REFERENCE IDENTITY MATCH", text)
        self.assertNotIn("Result: SUPPORTED", text)
        self.assertIn("not a hardware validation", text)
        code, out, _, _ = run_mocked("local", ("--json",))
        report = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "supported")
        self.assertEqual(report["result_label"], "reference identity match")

    def test_selected_profile_mismatch_label_is_scoped_but_status_is_stable(self):
        values = {**SWEET, "ro.product.device": "other", "ro.build.product": "other"}
        code, text, err, _ = run_mocked("local", ("--profile", "sweet"), values)
        self.assertEqual((code, err), (2, ""))
        self.assertIn("Result: REFERENCE PROFILE MISMATCH", text)
        code, out, _, _ = run_mocked("local", ("--profile", "sweet", "--json"), values)
        report = json.loads(out)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "incompatible")
        self.assertEqual(report["result_label"], "reference profile mismatch")

    def test_selected_adb_serial_remains_suppressed_when_values_are_shown(self):
        values = {**SWEET, "ro.product.model": "Model containing " + SERIAL}
        code, out, err, _ = run_mocked("adb", ("--show-properties", "--json"), values)
        self.assertEqual(code, 1)
        self.assertNotIn(SERIAL, out + err)
        self.assertIsNone(json.loads(out)["properties"]["ro.product.model"])

    def test_report_privacy_mode_does_not_change_identity_comparison(self):
        for mode in ("local", "adb"):
            with self.subTest(mode=mode):
                _, hidden, _, _ = run_mocked(mode, ("--json",))
                _, shown, _, _ = run_mocked(mode, ("--json", "--show-properties"))
                hidden, shown = json.loads(hidden), json.loads(shown)
                self.assertEqual(hidden["status"], shown["status"])
                self.assertEqual(hidden["checks"], shown["checks"])
                self.assertEqual(hidden["profile"], shown["profile"])
                self.assertEqual(shown["properties"]["ro.product.model"], "Redmi Note 10 Pro")
                self.assertEqual(hidden["properties"]["ro.product.model"], "[hidden]")


if __name__ == "__main__":
    unittest.main()
