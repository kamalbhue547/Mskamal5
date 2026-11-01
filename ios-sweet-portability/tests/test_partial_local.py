"""Synthetic failures exercise conservative local partial-result handling."""

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
from devicecheck.transport import ADB_PROPERTIES


VALUES = {
    "ro.product.device": "sweet",
    "ro.build.product": "sweet",
    "ro.product.manufacturer": "Xiaomi",
    "ro.product.model": "Redmi Note 10 Pro",
    "ro.soc.model": "SM7150",
    "ro.product.cpu.abilist64": "arm64-v8a",
}
PRIVATE = "SYNTHETIC-PRIVATE-TOOL-DIAGNOSTIC"


def run_local(*, failed=(), values=None, timeout_at=None, extra=()):
    values = VALUES if values is None else values
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        assert argv[0] == "/system/bin/getprop" and len(argv) == 2
        key = argv[1]
        assert key in ADB_PROPERTIES
        if key == timeout_at:
            raise subprocess.TimeoutExpired(["getprop", PRIVATE], 8)
        if key in failed:
            return subprocess.CompletedProcess(argv, 1, PRIVATE, PRIVATE)
        return subprocess.CompletedProcess(argv, 0, values.get(key, "") + "\n", "")

    out, err = io.StringIO(), io.StringIO()
    with patch("devicecheck.transport.subprocess.run", side_effect=run), \
         patch("devicecheck.transport.shutil.which", side_effect=AssertionError("must stay local")), \
         contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(["--transport", "local", "--json", *extra])
    return code, json.loads(out.getvalue()), out.getvalue(), err.getvalue(), calls


class PartialLocalTests(unittest.TestCase):
    def test_failed_optional_property_yields_a_partial_unknown_report(self):
        key = "ro.boot.flash.locked"
        code, report, out, err, calls = run_local(failed={key})
        self.assertEqual((code, err), (1, ""))
        self.assertEqual(report["status"], "unknown")
        self.assertEqual(report["failed_properties"], [key])
        self.assertIsNone(report["properties"][key])
        self.assertTrue(any(key in warning for warning in report["warnings"]))
        self.assertIn("partial", report["summary"].lower())
        self.assertNotIn(PRIVATE, out)
        self.assertEqual([call[1] for call in calls], list(ADB_PROPERTIES))
        self.assertEqual(report["profile"]["id"], "sweet")

    def test_failed_required_identity_property_never_becomes_a_match(self):
        for key in ("ro.product.device", "ro.build.product", "ro.product.manufacturer", "ro.product.model", "ro.soc.model", "ro.product.cpu.abilist64"):
            with self.subTest(key=key):
                code, report, _, _, _ = run_local(failed={key}, extra=("--profile", "sweet"))
                self.assertEqual(code, 1)
                self.assertEqual(report["status"], "unknown")
                self.assertEqual(report["failed_properties"], [key])
                self.assertIsNone(report["properties"][key])

    def test_each_single_property_failure_is_listed_and_fails_closed(self):
        for key in ADB_PROPERTIES:
            with self.subTest(key=key):
                code, report, out, err, calls = run_local(failed={key})
                self.assertEqual((code, err), (1, ""))
                self.assertEqual(report["status"], "unknown")
                self.assertEqual(report["failed_properties"], [key])
                self.assertIsNone(report["properties"][key])
                self.assertNotIn(PRIVATE, out)
                self.assertEqual([call[1] for call in calls], list(ADB_PROPERTIES))

    def test_multiple_failures_are_reported_in_allowlist_order(self):
        failed = {"ro.product.device", "ro.soc.model", "ro.boot.flash.locked"}
        code, report, out, _, _ = run_local(failed=failed)
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "unknown")
        self.assertEqual(report["failed_properties"], [key for key in ADB_PROPERTIES if key in failed])
        self.assertTrue(all(report["properties"][key] is None for key in failed))
        self.assertNotIn(PRIVATE, out)

    def test_all_failed_properties_are_a_tool_error_not_a_partial_result(self):
        code, report, out, err, calls = run_local(failed=set(ADB_PROPERTIES))
        self.assertEqual((code, err), (3, ""))
        self.assertEqual(report["status"], "error")
        self.assertIn("getprop", report["error"])
        self.assertNotIn(PRIVATE, out)
        self.assertEqual([call[1] for call in calls], list(ADB_PROPERTIES))

    def test_timeout_remains_a_hard_error_even_after_a_partial_failure(self):
        code, report, out, err, calls = run_local(failed={"ro.product.device"}, timeout_at="ro.product.model")
        self.assertEqual((code, err), (3, ""))
        self.assertEqual(report["status"], "error")
        self.assertIn("timed out", report["error"])
        self.assertNotIn(PRIVATE, out)
        self.assertEqual(calls[-1][1], "ro.product.model")

    def test_one_successful_but_empty_command_is_still_a_partial_unknown(self):
        failed = set(ADB_PROPERTIES) - {"ro.hardware"}
        code, report, _, _, _ = run_local(failed=failed, values={})
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "unknown")
        self.assertEqual(report["failed_properties"], [key for key in ADB_PROPERTIES if key in failed])
        self.assertTrue(all(value is None for value in report["properties"].values()))

    def test_empty_success_is_not_reported_as_a_failed_command(self):
        code, report, _, _, _ = run_local()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "supported")
        self.assertEqual(report["failed_properties"], [])
        self.assertIsNone(report["properties"]["ro.boot.flash.locked"])

    def test_partial_failure_downgrades_even_a_selected_profile_mismatch(self):
        values = {**VALUES, "ro.product.device": "other", "ro.build.product": "other"}
        code, report, _, _, _ = run_local(failed={"ro.boot.flash.locked"}, values=values,
                                           extra=("--profile", "sweet"))
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "unknown")
        self.assertTrue(any(check["result"] == "different" for check in report["checks"]))

    def test_real_subprocess_with_partial_failure_and_private_values(self):
        with tempfile.TemporaryDirectory() as temp:
            fake = Path(temp) / "getprop"
            log = Path(temp) / "commands.jsonl"
            values = {**VALUES, "ro.hardware": "SYNTHETIC-PRIVATE-HARDWARE"}
            fake.write_text(
                f"#!{sys.executable}\n"
                "import json, sys\n"
                f"values = {values!r}\n"
                f"with open({str(log)!r}, 'a', encoding='utf-8') as stream:\n"
                "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "if len(sys.argv) != 2:\n"
                "    sys.exit(99)\n"
                "if sys.argv[1] == 'ro.boot.flash.locked':\n"
                f"    print({PRIVATE!r}, file=sys.stderr)\n"
                "    sys.exit(1)\n"
                "print(values.get(sys.argv[1], ''))\n", encoding="utf-8")
            fake.chmod(0o755)
            for show in (False, True):
                out, err = io.StringIO(), io.StringIO()
                args = ["--transport", "local", "--json"]
                if show:
                    args.append("--show-properties")
                with patch("devicecheck.transport.ANDROID_GETPROP", str(fake)), \
                     contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = main(args)
                report = json.loads(out.getvalue())
                self.assertEqual((code, err.getvalue()), (1, ""))
                self.assertEqual(report["status"], "unknown")
                self.assertEqual(report["failed_properties"], ["ro.boot.flash.locked"])
                self.assertEqual("SYNTHETIC-PRIVATE-HARDWARE" in out.getvalue(), show)
                self.assertNotIn(PRIVATE, out.getvalue())
            commands = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(commands, [[key] for key in ADB_PROPERTIES] * 2)

    def test_adb_property_failures_remain_hard_errors(self):
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            if argv[1:] == ["devices"]:
                return subprocess.CompletedProcess(argv, 0, "List of devices attached\nPRIVATE\tdevice\n", "")
            if argv[-1] == "ro.boot.flash.locked":
                return subprocess.CompletedProcess(argv, 1, PRIVATE, PRIVATE)
            return subprocess.CompletedProcess(argv, 0, VALUES.get(argv[-1], "") + "\n", "")

        out, err = io.StringIO(), io.StringIO()
        with patch("devicecheck.transport.shutil.which", return_value="/mock/adb"), \
             patch("devicecheck.transport.subprocess.run", side_effect=run), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--transport", "adb", "--json"])
        self.assertEqual((code, err.getvalue()), (3, ""))
        self.assertEqual(json.loads(out.getvalue())["status"], "error")
        self.assertNotIn(PRIVATE, out.getvalue())
        self.assertEqual(calls[-1][-1], "ro.boot.flash.locked")


if __name__ == "__main__":
    unittest.main()
