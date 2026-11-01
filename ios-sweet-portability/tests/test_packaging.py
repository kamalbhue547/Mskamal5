"""Tests for the bundled resources without requiring a phone or build tools."""

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

from devicecheck.profiles import ProfileError, load_profiles


class PackagingTests(unittest.TestCase):
    def test_reference_and_typing_marker_are_package_resources(self):
        profile = files("devicecheck.profile_data").joinpath("sweet.json")
        data = json.loads(profile.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "sweet")
        self.assertTrue(files("devicecheck").joinpath("py.typed").is_file())
        self.assertIn("sweet", {item.id for item in load_profiles()})

    def test_missing_bundled_package_fails_closed(self):
        error = ModuleNotFoundError("missing resource")
        with patch("devicecheck.profiles.files", side_effect=error):
            with self.assertRaisesRegex(
                ProfileError, "profile directory is unavailable"
            ):
                load_profiles()

    def test_empty_bundled_directory_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("devicecheck.profiles.files", return_value=Path(temp)):
                with self.assertRaisesRegex(
                    ProfileError, "no device profiles"
                ):
                    load_profiles()

    def test_zip_import_loads_profiles_without_a_checkout(self):
        project = Path(__file__).resolve().parents[1]
        package = project / "devicecheck"
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "devicecheck.zip"
            with zipfile.ZipFile(archive, "w") as result:
                for path in package.glob("*.py"):
                    result.write(path, path.relative_to(project).as_posix())
                for path in (package / "profile_data").iterdir():
                    if path.suffix in {".py", ".json"}:
                        result.write(
                            path, path.relative_to(project).as_posix()
                        )
            code = (
                "import json, sys; sys.path.insert(0, sys.argv[1]); "
                "from devicecheck.profiles import load_profiles; "
                "print(json.dumps([p.id for p in load_profiles()]))"
            )
            run = subprocess.run(
                [sys.executable, "-I", "-c", code, str(archive)],
                cwd=temp, text=True, capture_output=True,
                timeout=20, check=False,
            )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("sweet", json.loads(run.stdout))


if __name__ == "__main__":
    unittest.main()
