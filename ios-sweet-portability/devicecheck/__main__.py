"""Linux CLI for a deliberately non-invasive device check."""

from __future__ import annotations

import argparse
import json
import sys

from .matching import adb_report, fastboot_report
from .profiles import ProfileError, load_profiles
from .transport import SelectionError, ToolError, discover, read_adb_properties


EXIT = {"supported": 0, "unknown": 1, "incompatible": 2, "error": 3}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="python3 -m devicecheck",
        description="Read-only identity comparison; no unlock, reboot, flash, erase or installation.",
    )
    result.add_argument("--transport", choices=("auto", "adb", "fastboot"), default="auto",
                        help="auto prefers adb; fastboot only enumerates devices (default: auto)")
    result.add_argument("--profile", help="compare against a specific profile ID, such as sweet")
    result.add_argument("--serial", help="select one device locally; do not publish this identifier")
    result.add_argument("--json", action="store_true", help="emit a redacted JSON report")
    return result


def _print_report(report: dict) -> None:
    print(f"Result: {report['status'].upper()}")
    print(f"Transport: {report['transport']}")
    print(report["summary"])
    if report["profile"]:
        profile = report["profile"]
        print(f"Reference: {profile['name']} ({profile['id']}; {profile['support_level']})")
    if report["properties"]:
        print("\nReported Android properties (missing/invalid values shown as unknown):")
        for name, value in report["properties"].items():
            print(f"  {name}: {value if value is not None else 'unknown'}")
    if report["checks"]:
        print("\nComparison:")
        for check in report["checks"]:
            print(f"  {check['field']}: {check['result']} (expected: {check['expected']})")
    if report["warnings"]:
        print("\nWarnings:")
        for warning in report["warnings"]:
            print(f"  - {warning}")
    print("\nStill unknown:")
    for item in report["unknowns"]:
        print(f"  - {item}")
    if report["evidence"]:
        print("\nReference evidence:")
        for item in report["evidence"]:
            print(f"  - {item['subject']}: {item['url']}")
    print(f"\nSafety: {report['safety']}")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        profiles = load_profiles()
        selected = next((p for p in profiles if p.id == args.profile), None)
        if args.profile is not None and selected is None:
            raise ProfileError("requested profile is not available; inspect profiles/ for reviewed IDs")
        connection = discover(args.transport, args.serial)
        if connection.transport == "adb":
            values = read_adb_properties(connection.device.serial)
            report = adb_report(values, profiles, args.profile, connection.warnings)
        else:
            report = fastboot_report(connection.warnings, selected)
    except (ProfileError, SelectionError, ToolError) as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return EXIT["error"]
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        _print_report(report)
    return EXIT[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
