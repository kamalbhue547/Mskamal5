import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devicecheck.__main__ import main
from devicecheck.transport import ADB_PROPERTIES


PRIVATE = "PRIVATE-DEVICE-123"
VALUES = {
    "ro.product.device": "sweet",
    "ro.build.product": "sweet",
    "ro.product.manufacturer": "Xiaomi",
    "ro.product.model": "Redmi Note 10 Pro",
    "ro.soc.model": "SM7150",
}


def run_cli(args, adb_devices=None, fastboot_devices=None, values=None, available=("adb", "fastboot")):
    commands = []
    values = VALUES if values is None else values
    adb_devices = f"List of devices attached\n{PRIVATE}\tdevice\n" if adb_devices is None else adb_devices
    fastboot_devices = "" if fastboot_devices is None else fastboot_devices

    def which(name):
        return f"/mock/{name}" if name in available else None

    def run(argv, **kwargs):
        commands.append(argv)
        tool = Path(argv[0]).name
        if tool == "adb" and argv[1:] == ["devices"]:
            out = adb_devices
        elif tool == "fastboot" and argv[1:] == ["devices"]:
            out = fastboot_devices
        elif (tool == "adb" and len(argv) == 6 and argv[1:5] == ["-s", PRIVATE, "shell", "getprop"]
              and argv[5] in ADB_PROPERTIES):
            out = values.get(argv[5], "") + "\n"
        else:
            raise AssertionError(f"unexpected command: {argv}")
        return subprocess.CompletedProcess(argv, 0, out, "")

    out, err = io.StringIO(), io.StringIO()
    with patch("devicecheck.transport.shutil.which", side_effect=which), \
         patch("devicecheck.transport.subprocess.run", side_effect=run), \
         contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue(), commands


class CliTests(unittest.TestCase):
    def test_full_adb_cli_supported_is_redacted_and_read_only(self):
        code, out, err, commands = run_cli(["--transport", "adb"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Result: REFERENCE IDENTITY MATCH", out)
        self.assertIn("not a hardware validation", out)
        self.assertIn("erases Android userdata", out)
        self.assertNotIn(PRIVATE, out)
        self.assertEqual(len(commands), 1 + len(ADB_PROPERTIES))
        for argv in commands:
            if argv[1:] != ["devices"]:
                self.assertEqual(argv[1:5], ["-s", PRIVATE, "shell", "getprop"])
                self.assertIn(argv[5], ADB_PROPERTIES)

    def test_json_unknown_when_soc_missing(self):
        values = dict(VALUES)
        values.pop("ro.soc.model")
        code, out, _, _ = run_cli(["--json", "--profile", "sweet"], values=values)
        report = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "unknown")
        self.assertIsNone(report["properties"]["ro.soc.model"])
        self.assertNotIn(PRIVATE, out)

    def test_explicit_incompatible_exit_code(self):
        values = {**VALUES, "ro.product.device": "different", "ro.build.product": "different"}
        code, out, _, _ = run_cli(["--profile", "sweet", "--json"], values=values)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["status"], "incompatible")

    def test_fastboot_only_enumerates_and_does_not_query_getvar(self):
        code, out, _, commands = run_cli(["--transport", "fastboot", "--json"], fastboot_devices=f"{PRIVATE}\tfastboot\n")
        self.assertEqual(code, 1)
        report = json.loads(out)
        self.assertEqual(report["status"], "unknown")
        self.assertEqual(report["properties"], {})
        self.assertTrue(report["properties_hidden"])
        self.assertEqual(report["failed_properties"], [])
        self.assertEqual(commands, [["/mock/fastboot", "devices"]])
        self.assertNotIn(PRIVATE, out)
        self.assertIn("never to use fastboot getvar", report["warnings"][0])
        self.assertFalse(any("values are displayed" in warning for warning in report["warnings"]))

    def test_auto_fastboot_text_explains_missing_adb_and_redacts_serial(self):
        code, out, err, commands = run_cli([], available=("fastboot",),
                                           fastboot_devices=f"{PRIVATE}\tfastboot\n")
        self.assertEqual((code, err), (1, ""))
        self.assertIn("Result: UNKNOWN", out)
        self.assertIn("adb is not installed", out)
        self.assertIn("Only fastboot devices was run", out)
        self.assertNotIn(PRIVATE, out)
        self.assertEqual(commands, [["/mock/fastboot", "devices"]])

    def test_fastboot_reports_selected_profile_without_comparing_it(self):
        code, out, _, commands = run_cli(["--transport", "fastboot", "--profile", "sweet", "--json"],
                                          fastboot_devices=f"{PRIVATE}\tfastboot\n")
        report = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(report["profile"]["id"], "sweet")
        self.assertIn("cannot be compared", report["summary"])
        self.assertTrue(any("NOTES.md#L43-L46" in item["url"] for item in report["evidence"]))
        self.assertEqual(commands, [["/mock/fastboot", "devices"]])

    def test_device_serial_in_a_property_is_not_printed(self):
        values = {**VALUES, "ro.product.model": "Custom " + PRIVATE}
        code, out, err, _ = run_cli(["--transport", "adb", "--json"], values=values)
        self.assertEqual(code, 1)
        self.assertNotIn(PRIVATE, out + err)
        self.assertIsNone(json.loads(out)["properties"]["ro.product.model"])

    def test_invalid_profile_fails_before_running_a_tool(self):
        code, out, _, commands = run_cli(["--profile", "imaginary", "--json"])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["status"], "error")
        self.assertEqual(commands, [])

    def test_json_does_not_change_argparse_usage_errors(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as context:
                main(["--json", "--transport", "invalid"])
        self.assertEqual(context.exception.code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("invalid choice", err.getvalue())

    def test_missing_executable_is_a_helpful_redacted_error(self):
        code, out, _, commands = run_cli(["--transport", "adb", "--json"], available=())
        self.assertEqual(code, 3)
        self.assertIn("adb is not installed", json.loads(out)["error"])
        self.assertEqual(commands, [])

    def test_no_device_is_a_helpful_error(self):
        code, _, err, _ = run_cli(["--transport", "adb"], adb_devices="List of devices attached\n\n")
        self.assertEqual(code, 3)
        self.assertIn("no matching adb device", err)

    def test_mock_fastboot_executable_end_to_end(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            fake = Path(temp) / "fastboot"
            fake.write_text(
                f"#!{sys.executable}\n"
                "import sys\n"
                "if sys.argv[1:] == ['devices']:\n"
                f"    print({PRIVATE!r} + '\\tfastboot')\n"
                "else:\n"
                "    sys.exit(99)\n", encoding="utf-8")
            fake.chmod(0o755)
            env = {**os.environ, "PATH": temp + os.pathsep + os.environ.get("PATH", "")}
            run = subprocess.run([sys.executable, "-m", "devicecheck", "--transport", "fastboot",
                                  "--profile", "sweet", "--json"],
                                 cwd=project, env=env, text=True, capture_output=True, timeout=20)
        report = json.loads(run.stdout)
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertEqual(report["status"], "unknown")
        self.assertEqual(report["transport"], "fastboot")
        self.assertEqual(report["profile"]["id"], "sweet")
        self.assertNotIn(PRIVATE, run.stdout + run.stderr)

    def test_mock_multiple_adb_states_do_not_fall_back_to_fastboot(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            fake_adb = Path(temp) / "adb"
            fake_adb.write_text(
                f"#!{sys.executable}\n"
                "import sys\n"
                "if sys.argv[1:] == ['devices']:\n"
                "    print('List of devices attached\\nFIRST\\tdevice\\nSECOND\\trescue')\n"
                "else:\n"
                "    sys.exit(99)\n", encoding="utf-8")
            fake_adb.chmod(0o755)
            marker = Path(temp) / "fastboot-was-called"
            fake_fastboot = Path(temp) / "fastboot"
            fake_fastboot.write_text(
                f"#!{sys.executable}\n"
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('called')\n"
                "print('THIRD\\tfastboot')\n", encoding="utf-8")
            fake_fastboot.chmod(0o755)
            env = {**os.environ, "PATH": temp + os.pathsep + os.environ.get("PATH", "")}
            run = subprocess.run([sys.executable, "-m", "devicecheck", "--json"],
                                 cwd=project, env=env, text=True, capture_output=True, timeout=20)
            self.assertFalse(marker.exists(), "auto must not fall back to another device")
        self.assertEqual(run.returncode, 3, run.stderr)
        self.assertEqual(json.loads(run.stdout)["status"], "error")
        self.assertIn("multiple adb devices", json.loads(run.stdout)["error"])
        self.assertNotIn("FIRST", run.stdout + run.stderr)
        self.assertNotIn("SECOND", run.stdout + run.stderr)

    def test_mock_executable_end_to_end(self):
        # Exercise the actual CLI + subprocess boundary without any real phone.
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            fake = Path(temp) / "adb"
            fake.write_text(
                f"#!{sys.executable}\n"
                "import json, sys\n"
                f"values = {VALUES!r}\n"
                f"serial = {PRIVATE!r}\n"
                "if sys.argv[1:] == ['devices']:\n"
                "    print('List of devices attached\\n' + serial + '\\tdevice')\n"
                "elif len(sys.argv) == 6 and sys.argv[1:5] == ['-s', serial, 'shell', 'getprop']:\n"
                "    print(values.get(sys.argv[5], ''))\n"
                "else:\n"
                "    sys.exit(99)\n", encoding="utf-8")
            fake.chmod(0o755)
            env = {**os.environ, "PATH": temp + os.pathsep + os.environ.get("PATH", "")}
            run = subprocess.run([sys.executable, "-m", "devicecheck", "--transport", "adb", "--json"],
                                 cwd=project, env=env, text=True, capture_output=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["status"], "supported")
        self.assertNotIn(PRIVATE, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
