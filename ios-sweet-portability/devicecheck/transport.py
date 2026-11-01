"""A narrow allowlist of adb/fastboot and Android-local read-only operations.

Do not add generic shell execution. In particular, fastboot getvar is excluded:
upstream's phone-workflow handoff says never to use it.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


# Query individually instead of downloading the entire property set, which can
# contain serial numbers, account-related state or other identifying data. The
# same narrow list is used for adb and on-phone getprop.
ADB_PROPERTIES = (
    "ro.product.device",
    "ro.build.product",
    "ro.product.manufacturer",
    "ro.product.model",
    "ro.soc.model",
    "ro.soc.manufacturer",
    "ro.board.platform",
    "ro.hardware",
    "ro.product.cpu.abilist64",
    "ro.build.version.release",
    "ro.boot.verifiedbootstate",
    "ro.boot.flash.locked",
    "ro.boot.vbmeta.device_state",
)
TIMEOUT_SECONDS = 8
# Use the Android system binary directly; Termux's PATH need not include it.
ANDROID_GETPROP = "/system/bin/getprop"


class ToolError(Exception):
    """A local tool could not be run; stderr is deliberately not exposed."""


class CommandFailed(ToolError):
    """An allowed command ran but exited unsuccessfully; its streams stay private."""


class SelectionError(Exception):
    """A connected device cannot be safely selected or accessed."""


@dataclass(frozen=True)
class Device:
    serial: str  # Only used to target an adb/fastboot device; never included in reports.
    state: str


@dataclass(frozen=True)
class Connection:
    transport: str
    device: Device
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocalProperties:
    values: dict[str, str | None]
    failed: tuple[str, ...] = ()


def _allowlisted(tool: str, args: list[str]) -> bool:
    if tool == "fastboot":
        return args == ["devices"]
    if tool == "getprop":
        return len(args) == 1 and args[0] in ADB_PROPERTIES
    if tool != "adb":
        return False
    if args == ["devices"]:
        return True
    return (len(args) == 5 and args[0] == "-s" and bool(args[1])
            and args[2:4] == ["shell", "getprop"] and args[4] in ADB_PROPERTIES)


def _run(tool: str, args: list[str], operation: str) -> str:
    if not _allowlisted(tool, args):
        raise ToolError("refusing a command outside the read-only device-check allowlist")
    path = ANDROID_GETPROP if tool == "getprop" else shutil.which(tool)
    if path is None:
        raise ToolError(f"{tool} is not installed or is not on PATH; install Android SDK Platform Tools")
    try:
        result = subprocess.run(
            [path, *args], stdin=subprocess.DEVNULL, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        hint = "Android permissions" if tool == "getprop" else "the connection and permissions"
        raise ToolError(f"{tool} timed out while {operation}; check {hint}") from exc
    except OSError as exc:
        if tool == "getprop":
            raise ToolError(
                "could not run Android /system/bin/getprop; use local mode on a "
                "compatible Android phone and check permissions"
            ) from exc
        raise ToolError(f"could not run {tool} while {operation}; check installation and permissions") from exc
    if result.returncode != 0:
        # Tool errors can include sensitive details. Never echo their raw streams.
        hint = "Android permissions" if tool == "getprop" else "the connection and permissions"
        raise CommandFailed(f"{tool} failed while {operation}; check {hint} (raw diagnostics suppressed)")
    return result.stdout


def _parse_devices(output: str, tool: str, states: set[str]) -> list[Device]:
    devices = []
    for line in output.splitlines():
        line = line.strip()
        if not line or (tool == "adb" and (line.startswith("List of devices attached") or line.startswith("*"))):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            # Do not ignore an unparseable entry and silently select another
            # device, including through auto's fallback to fastboot.
            raise SelectionError(f"{tool} returned an unrecognized device list; check the tool and connection")
        serial, state = parts
        if state.startswith("no permissions"):
            state = "no permissions"
        elif state not in states:
            # Device output is untrusted and may contain an identifier or
            # terminal control sequence; never echo an unknown state verbatim.
            state = "unrecognized"
        devices.append(Device(serial, state))
    return devices


def parse_adb_devices(output: str) -> list[Device]:
    states = {"device", "offline", "unauthorized", "recovery", "sideload",
              "bootloader", "rescue", "authorizing", "connecting"}
    devices = _parse_devices(output, "adb", states)
    has_header = any(line.strip().startswith("List of devices attached") for line in output.splitlines())
    if not devices and not has_header:
        raise SelectionError("adb returned an incomplete device list; check the adb server and connection")
    return devices


def parse_fastboot_devices(output: str) -> list[Device]:
    return _parse_devices(output, "fastboot", {"fastboot", "fastbootd"})


def _choose(devices: list[Device], serial: str | None, tool: str) -> Device | None:
    if serial is not None:
        found = [d for d in devices if d.serial == serial]
        if len(found) > 1:
            raise SelectionError(f"{tool} returned a duplicate device identifier; disconnect extras and retry")
        if not found:
            return None
        device = found[0]
    else:
        if len(devices) > 1:
            raise SelectionError(f"multiple {tool} devices detected; disconnect extras or use --serial locally (do not publish it)")
        if not devices:
            return None
        device = devices[0]

    if device.state == "unauthorized":
        raise SelectionError("adb device is unauthorized; unlock the screen and approve the computer's USB debugging prompt")
    if device.state == "offline":
        raise SelectionError("adb device is offline; check the cable, USB debugging and connection, then retry")
    if device.state == "no permissions":
        raise SelectionError(f"{tool} cannot access the USB device; check Linux USB/udev permissions")
    if device.state == "unrecognized":
        raise SelectionError(f"{tool} reported an unrecognized device state; check its mode and connection")
    if tool == "adb" and device.state in {"authorizing", "connecting"}:
        raise SelectionError("adb device is still connecting or awaiting authorization; approve USB debugging and retry")
    if tool == "adb" and device.state != "device":
        raise SelectionError(f"adb device is in {device.state} mode; Android properties from non-Android modes are not reliable. Start Android normally and retry")
    return device


def _adb_select(serial: str | None) -> Device | None:
    return _choose(parse_adb_devices(_run("adb", ["devices"], "listing devices")), serial, "adb")


def _fastboot_select(serial: str | None) -> Device | None:
    return _choose(parse_fastboot_devices(_run("fastboot", ["devices"], "listing devices")), serial, "fastboot")


def discover(mode: str, serial: str | None = None) -> Connection:
    """Select at most one device; auto never bypasses an ambiguous/blocked adb device."""
    if mode == "adb":
        device = _adb_select(serial)
        if device is None:
            raise SelectionError("no matching adb device found; connect an Android device with USB debugging enabled and authorized")
        return Connection("adb", device)
    if mode == "fastboot":
        device = _fastboot_select(serial)
        if device is None:
            raise SelectionError("no matching fastboot device found; connect a device already in fastboot and check USB permissions")
        return Connection("fastboot", device)
    if mode != "auto":
        raise ValueError("unsupported transport")

    warnings = []
    try:
        device = _adb_select(serial)
    except ToolError as exc:
        warnings.append(str(exc))
    else:
        if device is not None:
            return Connection("adb", device)
    try:
        device = _fastboot_select(serial)
    except ToolError as exc:
        warnings.append(str(exc))
    else:
        if device is not None:
            return Connection("fastboot", device, tuple(warnings))
    detail = "; ".join(warnings)
    suffix = f" {detail}." if detail else ""
    raise SelectionError(
        "no matching usable adb or fastboot device found; connect one Android device and authorize USB debugging, "
        "or connect a device already in fastboot. Check the cable and Linux USB permissions." + suffix
    )


def _property_value(output: str, serial: str | None = None) -> str | None:
    value = output.rstrip("\r\n").strip()
    # Treat placeholders, multiline responses, terminal control sequences and
    # values containing the selected serial as unknown rather than printing them.
    if (not value or len(value) > 160 or not value.isprintable()
            or value.casefold() in {"unknown", "n/a", "null", "none", "(null)", "<unknown>"}
            or (serial and serial.casefold() in value.casefold())):
        return None
    return value


def read_adb_properties(serial: str) -> dict[str, str | None]:
    values = {}
    for key in ADB_PROPERTIES:
        # Keys are constants, not user input; no shell script or arbitrary command.
        output = _run("adb", ["-s", serial, "shell", "getprop", key], f"reading {key}")
        values[key] = _property_value(output, serial)
    return values


def read_local_properties() -> LocalProperties:
    """Read local properties, retaining partial data only for nonzero exits.

    A failing property command does not tell us whether a vendor restriction or
    another problem caused it. Missing executables, OS errors and timeouts remain
    hard errors. Unlike local mode, adb stays fail-fast because a failure can
    indicate that the selected device disconnected during the comparison.
    """
    values = {}
    failed = []
    for key in ADB_PROPERTIES:
        try:
            output = _run("getprop", [key], f"reading {key}")
        except CommandFailed:
            values[key] = None
            failed.append(key)
        else:
            values[key] = _property_value(output)
    if len(failed) == len(ADB_PROPERTIES):
        raise ToolError("all Android getprop commands failed; check the phone and Android permissions (raw diagnostics suppressed)")
    return LocalProperties(values, tuple(failed))
