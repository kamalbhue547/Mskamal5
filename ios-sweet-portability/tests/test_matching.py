import unittest
from dataclasses import replace
from typing import ClassVar

from devicecheck.matching import adb_report, fastboot_report
from devicecheck.profiles import Profile, load_profiles


SWEET = {
    "ro.product.device": "sweet",
    "ro.build.product": "sweet",
    "ro.product.manufacturer": "Xiaomi",
    "ro.product.model": "Redmi Note 10 Pro",
    "ro.soc.model": "SM7150",
}


class MatchTests(unittest.TestCase):
    profiles: ClassVar[tuple[Profile, ...]]

    @classmethod
    def setUpClass(cls):
        cls.profiles = load_profiles()

    def result(self, changes=None, selected=None, profiles=None):
        values = {**SWEET, **(changes or {})}
        return adb_report(values, profiles or self.profiles, selected)

    def test_only_complete_identity_matches_are_supported(self):
        report = self.result()
        self.assertEqual(report["status"], "supported")
        self.assertEqual(report["profile"]["id"], "sweet")
        self.assertEqual(len(report["checks"]), 6)
        self.assertTrue(all(check["result"] == "match" for check in report["checks"][:5]))
        self.assertEqual(report["checks"][-1]["result"], "missing")  # ABI is optional, not proof of CPU
        self.assertIn("not permission to flash", report["unknowns"][-1])
        self.assertTrue(report["evidence"])

    def test_matching_is_case_insensitive_and_soc_alias_is_sourced(self):
        report = self.result({"ro.product.device": "SWEET", "ro.build.product": "Sweet",
                              "ro.product.manufacturer": "xiaomi", "ro.product.model": "redmi note 10 pro",
                              "ro.soc.model": "Snapdragon 732G"})
        self.assertEqual(report["status"], "supported")

    def test_every_required_property_must_be_present(self):
        for prop in SWEET:
            with self.subTest(prop=prop):
                report = self.result({prop: None}, selected="sweet")
                self.assertEqual(report["status"], "unknown")
                self.assertEqual(next(c for c in report["checks"] if c["field"] == prop)["result"], "missing")

    def test_unknown_soc_alias_does_not_prove_incompatibility(self):
        report = self.result({"ro.soc.model": "vendor-board-alias"})
        self.assertEqual(report["status"], "unknown")
        self.assertEqual(next(c for c in report["checks"] if c["field"] == "ro.soc.model")["result"], "different")

    def test_reported_arm64_abi_is_checked_but_not_hardware_proof(self):
        report = self.result({"ro.product.cpu.abilist64": "arm64-v8a"})
        self.assertEqual(report["status"], "supported")
        self.assertEqual(report["checks"][-1]["result"], "match")
        self.assertIn("not proof of CPU", report["checks"][-1]["expected"])

    def test_contradictory_or_unrecognized_abi_downgrades_identity_match(self):
        for value in ("x86_64", "unknown-abi"):
            with self.subTest(value=value):
                report = self.result({"ro.product.cpu.abilist64": value})
                self.assertEqual(report["status"], "unknown")
                self.assertEqual(report["checks"][-1]["result"], "different")
                self.assertIn("not proof", report["summary"])

    def test_same_soc_different_codename_is_not_automatically_supported(self):
        report = self.result({"ro.product.device": "other", "ro.build.product": "other"})
        self.assertEqual(report["status"], "unknown")
        self.assertIsNone(report["profile"])

    def test_explicit_profile_with_agreeing_different_codenames_is_profile_incompatible(self):
        report = self.result({"ro.product.device": "other", "ro.build.product": "other"}, selected="sweet")
        self.assertEqual(report["status"], "incompatible")
        self.assertIn("profile only", report["summary"])
        self.assertIn("not impossible to port", report["summary"])

    def test_only_one_different_codename_is_not_a_conclusive_mismatch(self):
        report = self.result({"ro.product.device": "other", "ro.build.product": None}, selected="sweet")
        self.assertEqual(report["status"], "unknown")

    def test_contradictory_codenames_are_unknown(self):
        report = self.result({"ro.product.device": "sweet", "ro.build.product": "other"}, selected="sweet")
        self.assertEqual(report["status"], "unknown")

    def test_wrong_manufacturer_is_unknown_not_incompatible(self):
        report = self.result({"ro.product.manufacturer": "Other"})
        self.assertEqual(report["status"], "unknown")

    def test_wrong_model_is_unknown_not_incompatible(self):
        report = self.result({"ro.product.model": "Other phone"})
        self.assertEqual(report["status"], "unknown")

    def test_sweetin_alias_is_recognized(self):
        report = self.result({"ro.product.device": "sweetin", "ro.build.product": "sweetin"})
        self.assertEqual(report["status"], "supported")

    def test_research_only_cannot_be_promoted_by_matching_properties(self):
        p = replace(self.profiles[0], support_level="research_only")
        report = self.result(profiles=(p,))
        self.assertEqual(report["status"], "unknown")
        self.assertIn("research-only", report["summary"])

    def test_incomplete_research_profile_stays_unknown_even_when_explicitly_selected(self):
        p = replace(self.profiles[0], support_level="research_only", codename=None,
                    manufacturer=None, model=None, soc_labels=(), cpu_arch=None)
        report = self.result(selected="sweet", profiles=(p,))
        self.assertEqual(report["status"], "unknown")
        self.assertTrue(all(c["result"] == "unverified" for c in report["checks"]))

    def test_ambiguous_profiles_are_unknown(self):
        duplicate_codename = replace(self.profiles[0], id="other")
        report = self.result(profiles=(self.profiles[0], duplicate_codename))
        self.assertEqual(report["status"], "unknown")
        self.assertIn("More than one", report["summary"])

    def test_stock_android_11_regional_model(self):
        report = self.result({"ro.product.model": "M2101K6G", "ro.soc.model": None,
                              "ro.build.version.sdk": "30", "ro.product.marketname": "Redmi Note 10 Pro"})
        self.assertEqual(report["status"], "supported")
        self.assertEqual(next(c for c in report["checks"] if c["field"] == "ro.soc.model")["result"], "not available")
        self.assertTrue(any("not verified" in w for w in report["warnings"]))

    def test_variant_and_fallbacks(self):
        for field in ("ro.product.vendor.device", "ro.product.odm.device"):
            report = self.result({"ro.product.device": None, field: "sweetin", "ro.build.product": "sweetin",
                                  "ro.product.model": "M2101K6I", "ro.soc.model": None,
                                  "ro.build.version.release": "11"})
            self.assertEqual(report["status"], "supported")
            self.assertEqual(report["checks"][0]["field"], field)
        report = self.result({"ro.product.model": None, "ro.product.marketname": "Redmi Note 10 Pro"})
        self.assertEqual(report["status"], "supported")

    def test_unknown_version_or_modern_missing_soc_does_not_match(self):
        for sdk in (None, "31", "invalid"):
            report = self.result({"ro.soc.model": None, "ro.build.version.sdk": sdk})
            self.assertEqual(report["status"], "unknown")

    def test_conflicting_marketing_name_does_not_match(self):
        report = self.result({"ro.product.model": "M2101K6G", "ro.product.marketname": "Other"})
        self.assertEqual(report["status"], "unknown")

    def test_fastboot_always_unknown_without_getvar(self):
        report = fastboot_report()
        self.assertEqual(report["status"], "unknown")
        self.assertEqual(report["properties"], {})
        self.assertIn("never to use fastboot getvar", report["warnings"][0])


if __name__ == "__main__":
    unittest.main()
