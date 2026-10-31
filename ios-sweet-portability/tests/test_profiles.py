import json
import tempfile
import unittest
from pathlib import Path

from devicecheck.profiles import PROFILE_DIR, ProfileError, load_profiles


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((PROFILE_DIR / "sweet.json").read_text(encoding="utf-8"))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def write(self, name="sweet.json"):
        (self.directory / name).write_text(json.dumps(self.data), encoding="utf-8")

    def test_checked_in_profile_is_a_sourced_reference(self):
        profiles = load_profiles()
        self.assertEqual([p.id for p in profiles], ["sweet"])
        p = profiles[0]
        self.assertEqual(p.support_level, "upstream_reference")
        self.assertEqual((p.codename, p.manufacturer, p.model), ("sweet", "Xiaomi", "Redmi Note 10 Pro"))
        self.assertEqual(p.soc_labels, ("SM7150", "Snapdragon 732G"))
        self.assertEqual(p.cpu_arch, "arm64")
        self.assertTrue(all("45263bee51df4a0f55cdf9c649af886399488ddb" in e.url for e in p.evidence))

    def test_empty_directory_fails_closed(self):
        with self.assertRaisesRegex(ProfileError, "no device profiles"):
            load_profiles(self.directory)

    def test_malformed_json_fails_closed(self):
        (self.directory / "sweet.json").write_text("{", encoding="utf-8")
        with self.assertRaises(ProfileError):
            load_profiles(self.directory)

    def test_missing_directory_fails_closed(self):
        with self.assertRaisesRegex(ProfileError, "directory is unavailable"):
            load_profiles(self.directory / "missing")

    def test_invalid_object_types_fail_closed(self):
        baseline = json.dumps(self.data)
        for field, value, error in (("identity", None, "identity must"),
                                    ("platform", "arm64", "platform must"),
                                    ("evidence", [None], "each evidence")):
            with self.subTest(field=field):
                self.data = json.loads(baseline)
                self.data[field] = value
                self.write()
                with self.assertRaisesRegex(ProfileError, error):
                    load_profiles(self.directory)

    def test_supported_profile_requires_a_soc_label_list(self):
        self.data["identity"]["soc_labels"] = []
        self.write()
        with self.assertRaisesRegex(ProfileError, "identity.soc_labels"):
            load_profiles(self.directory)

    def test_missing_evidence_fails_closed(self):
        self.data["evidence"] = []
        self.write()
        with self.assertRaisesRegex(ProfileError, "evidence"):
            load_profiles(self.directory)

    def test_untrusted_url_scheme_rejected(self):
        self.data["evidence"][0]["url"] = "file:///tmp/fake"
        self.write()
        with self.assertRaisesRegex(ProfileError, "HTTPS"):
            load_profiles(self.directory)

    def test_malformed_url_and_credentials_are_rejected(self):
        for url in ("https://[", "https://user:password@example.test/source",
                    "https://example.test:invalid/source", "https://example.test:99999/source",
                    "https://example.test/unescaped space"):
            with self.subTest(url=url):
                self.data["evidence"][0]["url"] = url
                self.write()
                with self.assertRaisesRegex(ProfileError, "HTTPS"):
                    load_profiles(self.directory)

    def test_valid_encoded_evidence_url_is_accepted(self):
        self.data["evidence"][0]["url"] = "https://example.test:443/path%20with%20spaces"
        self.write()
        self.assertEqual(load_profiles(self.directory)[0].evidence[0].url,
                         "https://example.test:443/path%20with%20spaces")

    def test_wrong_filename_fails_closed(self):
        self.write("other.json")
        with self.assertRaisesRegex(ProfileError, "filename"):
            load_profiles(self.directory)

    def test_unsupported_support_level_fails_closed(self):
        self.data["support_level"] = "assumed"
        self.write()
        with self.assertRaisesRegex(ProfileError, "support_level"):
            load_profiles(self.directory)

    def test_bool_is_not_a_schema_version(self):
        self.data["schema_version"] = True
        self.write()
        with self.assertRaisesRegex(ProfileError, "schema_version"):
            load_profiles(self.directory)

    def test_example_file_is_not_loaded(self):
        self.write()
        (self.directory / "template.json.example").write_text("not a profile", encoding="utf-8")
        self.assertEqual(len(load_profiles(self.directory)), 1)

    def test_repeated_soc_aliases_rejected(self):
        self.data["identity"]["soc_labels"] = ["SM7150", "sm7150"]
        self.write()
        with self.assertRaisesRegex(ProfileError, "duplicates"):
            load_profiles(self.directory)

    def test_control_characters_in_profile_rejected(self):
        self.data["identity"]["model"] = "model\x1b[2J"
        self.write()
        with self.assertRaisesRegex(ProfileError, "printable"):
            load_profiles(self.directory)

    def test_research_profile_can_record_unknowns_without_inventing_facts(self):
        self.data["support_level"] = "research_only"
        self.data["identity"] = {"codename": None, "manufacturer": None, "model": None, "soc_labels": []}
        self.write()
        profile = load_profiles(self.directory)[0]
        self.assertIsNone(profile.codename)
        self.assertIsNone(profile.model)
        self.assertEqual(profile.soc_labels, ())

    def test_reference_profile_cannot_omit_identity_fields(self):
        self.data["identity"]["model"] = None
        self.write()
        with self.assertRaisesRegex(ProfileError, "identity.model"):
            load_profiles(self.directory)


if __name__ == "__main__":
    unittest.main()
