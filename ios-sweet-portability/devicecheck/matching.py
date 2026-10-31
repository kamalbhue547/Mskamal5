"""Conservative matching of reported Android properties to reviewed profiles."""

from __future__ import annotations

from dataclasses import asdict

from .profiles import Profile


SAFETY = (
    "Upstream's root-image flash erases Android userdata; unlocking a bootloader may erase data. "
    "Do not flash based on this report."
)
COMMON_UNKNOWNS = [
    "Android properties are software-reported and can be missing, modified or spoofed; they do not prove physical hardware or firmware.",
    "Exact board revision, bootloader behavior, storage layout, device tree, memory, display and touch were not verified.",
    "No kernel build, boot, recovery, backup, unlock or iOS operation was attempted; a match is not permission to flash.",
]


def _same(left: str | None, right: str | None) -> bool:
    return left is not None and right is not None and left.casefold() == right.casefold()


def _check(field: str, actual: str | None, expected: tuple[str, ...]) -> dict[str, str]:
    if not expected:
        outcome = "unverified"
    elif actual is None:
        outcome = "missing"
    elif any(_same(actual, value) for value in expected):
        outcome = "match"
    else:
        outcome = "different"
    return {"field": field, "result": outcome, "expected": " or ".join(expected) or "not recorded"}


def _expected(value: str | None) -> tuple[str, ...]:
    return (value,) if value is not None else ()


def _base(transport: str, properties: dict[str, str | None], warnings: tuple[str, ...]) -> dict:
    return {
        "status": "unknown",
        "transport": transport,
        "profile": None,
        "summary": "No supported reference identity has been established.",
        "properties": properties,
        "checks": [],
        "warnings": list(warnings),
        "unknowns": list(COMMON_UNKNOWNS),
        "evidence": [],
        "safety": SAFETY,
    }


def fastboot_report(warnings: tuple[str, ...] = (), profile: Profile | None = None) -> dict:
    report = _base("fastboot", {}, warnings)
    report["summary"] = "A fastboot device was enumerated, but its product and platform were not read."
    if profile is not None:
        report["profile"] = {"id": profile.id, "name": profile.name, "support_level": profile.support_level}
        report["summary"] += " The selected profile cannot be compared in this transport."
        report["evidence"] = [asdict(item) for item in profile.evidence]
    report["checks"] = [{"field": "fastboot devices", "result": "enumerated", "expected": "one selected device"}]
    report["warnings"].append(
        "Only fastboot devices was run. Upstream's phone workflow says never to use fastboot getvar; this checker does not use it."
    )
    report["evidence"].append({
        "subject": "Upstream fastboot restriction",
        "url": "https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/NOTES.md#L43-L46",
        "note": "The upstream phone-workflow handoff says never to use fastboot getvar; no reason is given there.",
    })
    report["unknowns"].insert(0, "Product, codename, SoC and bootloader state are unknown in this transport.")
    return report


def adb_report(values: dict[str, str | None], profiles: tuple[Profile, ...],
               selected_id: str | None = None, warnings: tuple[str, ...] = ()) -> dict:
    report = _base("adb", values, warnings)
    device = values.get("ro.product.device")
    build = values.get("ro.build.product")
    if selected_id is not None:
        # CLI verifies it before contacting any devices.
        candidates = [p for p in profiles if p.id == selected_id]
    else:
        candidates = [p for p in profiles if _same(device, p.codename) or _same(build, p.codename)]

    if not candidates:
        report["summary"] = "No profile matches the reported codename; this is not a judgment about future porting."
        report["checks"] = [
            {"field": "ro.product.device / ro.build.product", "result": "no profile match", "expected": "a verified profile codename"}
        ]
        return report
    if len(candidates) != 1:
        report["summary"] = "More than one profile matches; select a profile explicitly and resolve the ambiguity."
        return report

    profile = candidates[0]
    report["profile"] = {"id": profile.id, "name": profile.name, "support_level": profile.support_level}
    report["evidence"] = [asdict(item) for item in profile.evidence]
    identity_checks = [
        _check("ro.product.device", device, _expected(profile.codename)),
        _check("ro.build.product", build, _expected(profile.codename)),
        _check("ro.product.manufacturer", values.get("ro.product.manufacturer"), _expected(profile.manufacturer)),
        _check("ro.product.model", values.get("ro.product.model"), _expected(profile.model)),
        _check("ro.soc.model", values.get("ro.soc.model"), profile.soc_labels),
    ]
    report["checks"] = list(identity_checks)
    abi_conflict = False
    if profile.cpu_arch and profile.cpu_arch.casefold() == "arm64":
        # Android ABI lists describe a ROM's userspace, not the physical CPU.
        # A missing ABI doesn't prove incompatibility, but a contradictory or
        # unrecognized nonempty list must prevent a positive identity result.
        abi = values.get("ro.product.cpu.abilist64")
        abi_values = {part.strip().casefold() for part in abi.split(",")} if abi else set()
        abi_result = "missing" if not abi else "match" if "arm64-v8a" in abi_values else "different"
        abi_conflict = abi_result == "different"
        report["checks"].append({
            "field": "ro.product.cpu.abilist64", "result": abi_result,
            "expected": "arm64-v8a if reported (ROM ABI, not proof of CPU)",
        })

    # "Incompatible" is only relative to an explicitly selected profile, and
    # only if two independent *property fields* agree on a different codename.
    # They may still be generated from the same ROM data; no hardware claim.
    if (selected_id is not None and profile.codename is not None and device and build
            and _same(device, build) and not _same(device, profile.codename)):
        report["status"] = "incompatible"
        report["summary"] = (
            "Both reported codename fields differ from the explicitly selected reference profile. "
            "Incompatible means identity mismatch with that profile only, not impossible to port."
        )
    elif all(check["result"] == "match" for check in identity_checks) and not abi_conflict:
        if profile.support_level in {"upstream_reference", "hardware_verified"}:
            report["status"] = "supported"
            report["summary"] = (
                "Reported identity matches a documented reference profile. "
                "This is not a hardware validation, installer readiness, or flash-safety verdict."
            )
        else:
            report["summary"] = "The identity matches research-only data, but no verified port is recorded."
    elif abi_conflict and all(check["result"] == "match" for check in identity_checks):
        report["summary"] = (
            "Identity strings match, but the reported 64-bit Android ABI is different or unrecognized. "
            "This is not proof of the physical CPU or hardware incompatibility."
        )
    else:
        report["summary"] = (
            "The reference profile was considered, but one or more required properties are missing, different or unverified. "
            "Different or unrecognized values are not proof of hardware incompatibility."
        )
    return report
