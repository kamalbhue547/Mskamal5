"""Read-only device checker for Linux hosts and Android terminals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .matching import adb_report, fastboot_report
from .profiles import ProfileError, load_profiles
from .transport import (
    SelectionError, ToolError, discover, read_adb_properties, read_local_properties,
)


# Keep machine-readable statuses and exit codes stable; the human label makes
# clear that a positive result is an identity comparison, not device support.
EXIT = {"supported": 0, "unknown": 1, "incompatible": 2, "error": 3}
RESULT_LABEL = {
    "supported": "reference identity match",
    "unknown": "unknown",
    "incompatible": "reference profile mismatch",
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="devicecheck",
        description=(
            "Read-only identity comparison; "
            "no unlock, reboot, flash, erase or installation."
        ),
    )
    result.add_argument(
        "--version", action="version", version=f"devicecheck {__version__}"
    )
    mode = result.add_mutually_exclusive_group()
    mode.add_argument(
        "--transport", choices=("auto", "adb", "fastboot", "local"),
        default="auto",
        help=("auto prefers adb (default); local reads this phone; "
              "fastboot only enumerates devices"),
    )
    mode.add_argument(
        "--list-profiles", action="store_true",
        help="list bundled reference profiles without connecting to a device",
    )
    result.add_argument("--profile-dir", type=Path, help="load profiles from this directory instead of bundled profiles")
    result.add_argument("--explain", "--dry-run", action="store_true",
                        help="show comparison checks (already shown by default; all operations are read-only)")
    result.add_argument(
        "--profile",
        help="compare against a specific profile ID, such as sweet",
    )
    result.add_argument(
        "--serial",
        help=("select one adb/fastboot device; not used in local mode; "
              "do not publish it"),
    )
    result.add_argument(
        "--json", action="store_true",
        help="emit JSON; review it for identifying details before sharing",
    )
    result.add_argument(
        "--show-properties", action="store_true",
        help=("show reported property values locally; "
              "they may identify the device"),
    )
    return result


def _prepare_report(report: dict, show_properties: bool) -> dict:
    """Hide observed property values after matching, without claiming anonymity."""
    output = dict(report)
    output["result_label"] = RESULT_LABEL[report["status"]]
    output["properties_hidden"] = not show_properties
    output["properties"] = {
        key: value if show_properties or value is None else "[hidden]"
        for key, value in report["properties"].items()
    }
    output["warnings"] = list(report["warnings"])
    if not report["properties"]:
        output["warnings"].append("Report details may identify a device; review before sharing.")
    elif show_properties:
        output["warnings"].append(
            "Reported property values are displayed and may identify a device; review before sharing."
        )
    else:
        output["warnings"].append(
            "Property values are hidden, but other report details may identify a device; review before sharing."
        )
    return output


def _print_report(report: dict) -> None:
    print(f"Result: {report['result_label'].upper()}")
    print(f"Transport: {report['transport']}")
    print(report["summary"])
    if report["profile"]:
        profile = report["profile"]
        print(f"Reference: {profile['name']} ({profile['id']}; {profile['support_level']})")
    if report["properties"]:
        if report["properties_hidden"]:
            print("\nReported Android properties ([hidden] = present; unknown = missing/invalid/failed):")
            print("  Values are hidden; use --show-properties only for private inspection.")
        else:
            print("\nReported Android properties (missing/invalid/failed values shown as unknown):")
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
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    if args.list_profiles and (
        args.profile is not None or args.serial is not None
        or args.show_properties
    ):
        argument_parser.error(
            "--list-profiles cannot be combined with --profile, --serial, "
            "or --show-properties"
        )
    try:
        profiles = load_profiles(args.profile_dir)
        if args.list_profiles:
            entries = [
                {"id": p.id, "name": p.name, "support_level": p.support_level}
                for p in profiles
            ]
            if args.json:
                print(json.dumps(
                    {"schema_version": 1, "profiles": entries}, indent=2, ensure_ascii=True
                ))
            else:
                for entry in entries:
                    print(
                        f"{entry['id']}: {entry['name']} "
                        f"({entry['support_level']})"
                    )
            return 0
        selected = next((p for p in profiles if p.id == args.profile), None)
        if args.profile is not None and selected is None:
            raise ProfileError(
                "requested profile is not available; "
                "use --list-profiles to view reviewed IDs"
            )
        if args.transport == "local":
            if args.serial is not None:
                raise SelectionError("--serial is for adb/fastboot selection and cannot be used with local mode")
            properties = read_local_properties()
            warnings = (
                "Local mode does not query a serial; property values can still contain identifying details.",
            )
            report = adb_report(properties.values, profiles, args.profile, warnings, transport="local")
            if properties.failed:
                report["failed_properties"] = list(properties.failed)
                report["warnings"].append(
                    "Local property commands failed for: " + ", ".join(properties.failed)
                    + ". The cause is unknown; those values are unavailable and raw diagnostics are suppressed."
                )
                # A partial comparison must not be confused with a complete
                # identity match or an unqualified profile mismatch.
                report["status"] = "unknown"
                report["summary"] = (
                    "Some local property reads failed. This partial comparison is unknown, "
                    "not a compatibility or flash-safety verdict."
                )
        else:
            connection = discover(args.transport, args.serial)
            if connection.transport == "adb":
                values = read_adb_properties(connection.device.serial)
                report = adb_report(values, profiles, args.profile, connection.warnings)
            else:
                report = fastboot_report(connection.warnings, selected)
    except (ProfileError, SelectionError, ToolError) as exc:
        if args.json:
            print(json.dumps({"schema_version": 1, "status": "error", "error": str(exc)}, indent=2, ensure_ascii=True))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return EXIT["error"]
    report = _prepare_report(report, args.show_properties)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        _print_report(report)
    return EXIT[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
