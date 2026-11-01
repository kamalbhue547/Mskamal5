# iOS Sweet Portability Lab

[![Parent repository CI](https://github.com/kamalbhue547/Mskamal5/actions/workflows/python-package.yml/badge.svg?branch=main)](https://github.com/kamalbhue547/Mskamal5/actions/workflows/python-package.yml)

A **research and read-only device-identification toolkit**, not an iOS
installer. It studies [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet),
an experimental XNU and iOS userland bring-up for the **Redmi Note 10 Pro
(`sweet`)**. This project does not build a kernel, create an iOS image, unlock,
reboot, flash, or port iOS to another phone. **Do not assume iOS can run on
every Android device**: a new target requires device-specific engineering and
physical testing.

> **Data loss and security:** Upstream's separate root-image flash overwrites
> Android **`userdata`**, erasing Android user data. Unlocking a bootloader may
> also erase data, and recovery can fail or be impossible. Upstream's experiment
> disables major security mechanisms; do not use it for personal data. Never
> flash a `sweet` image to an unverified device, even one with the same chipset.
> Read [safety and recovery](docs/safety-recovery.md) first.

[Android phone](#quick-start-android-phone) · [Linux computer](#quick-start-linux) ·
[More commands](#more-copy-and-paste-commands) · [Results](#understanding-the-result) ·
[Troubleshooting](#troubleshooting) · [Research guides](#research-guides)

## At a glance

| Topic | Details |
| --- | --- |
| Where to run | A Linux computer or, in local mode, an Android phone with Termux |
| Python | 3.10 or newer; the CI matrix targets 3.10–3.14 |
| Python packages | None required; the CLI and tests use the standard library |
| Phone tools | Local Android `getprop`, or computer-side `adb`; `fastboot` is only for optional enumeration |
| Reference profile | Redmi Note 10 Pro `sweet`; an identity comparison, not a flashing recommendation |
| Safety | The checker sends no unlock, reboot, flash, erase, push, or write commands |

On a computer, the tool selects one device and reads a short allowlist of
Android properties. On the phone, local mode reads the same keys using Android's
`getprop`. In fastboot mode it only lists devices; it does **not** use `fastboot
getvar`, because the upstream phone workflow explicitly says not to. An `adb`
server may start on the computer and an authorization prompt may appear on the
phone. The selected adb serial is omitted from reports; local mode does not
query one. Reports hide observed property values by default, including in JSON.
`--show-properties` displays them locally when needed, but custom properties can
contain identifiers. Other report details can also identify a device, so review
and redact all output before sharing it.

## Quick start (Android phone)

This runs the **checker**, not iOS, on a compatible Android phone. Install
Termux from its [official installation instructions](https://github.com/termux/termux-app#installation).
No computer, root, USB debugging, or Apple firmware is needed. Termux and local
property access may not work on every phone; this mode has not been tested on a
physical Android device.

For a first-time checkout, open Termux and copy and paste:

```sh
pkg update &&
pkg install -y git python &&
cd "$HOME" &&
git clone https://github.com/kamalbhue547/Mskamal5.git &&
cd Mskamal5/ios-sweet-portability &&
python3 -m devicecheck --transport local
```

**Why:** the first commands install Git and Python in Termux, Git downloads the
project, and `local` checks this phone's reported identity without adb. Package
installation and Python caches use Termux's app storage; the checker does not
flash or erase partitions. If the folder already exists, or for tests, privacy,
troubleshooting and detailed explanations, use the
[step-by-step Android guide](docs/android-phone.md). An `unknown` result is
normal for many devices and **no result authorizes flashing**.

## Quick start (Linux)

These commands are for a Linux terminal. The tests and help work without a
phone; an Android device is only needed for the device check in step 4. Run the
commands in order and stop if a step reports an error.

### 1. Install the host tools

On Debian or Ubuntu, if these tools are not installed, copy and paste the
following. This changes packages on the computer and may ask for your Linux
administrator password:

```sh
sudo apt-get update &&
sudo apt-get install -y git python3 adb fastboot
```

**Why:** the first command refreshes package lists. The second installs Git
(to download the project), Python (to run it), `adb` (to read Android
properties), and `fastboot` (for optional enumeration). `sudo` is for installing
packages on the computer; do not run the checker or tests with `sudo`.

On other Linux distributions, install Git, Python 3.10 or newer, and the
[Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools)
using your distribution's trusted packages or the official SDK. Ensure `adb`
and, if needed, `fastboot` are on your `PATH`. No third-party Python package or
`pip install` is required.

### 2. Download the project

For a first-time checkout, from the directory where you want the new `Mskamal5`
folder to be created:

```sh
git clone https://github.com/kamalbhue547/Mskamal5.git &&
cd Mskamal5/ios-sweet-portability
```

**Why:** Git downloads this public repository, and `cd` puts the terminal in the
project folder where `devicecheck` and `tests` are located. If you already
cloned it and are at the `Mskamal5` repository root, use this instead:

```sh
cd ios-sweet-portability
```

If you have this project as a standalone folder, enter the folder containing
`devicecheck/` and `tests/` instead. All remaining commands assume your terminal
is in `ios-sweet-portability/` (or that standalone project root).

### 3. Verify the installation without a phone

```sh
python3 -c 'import sys; print("Python " + sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 10) else "Python 3.10 or newer is required")' &&
python3 -m devicecheck --help &&
python3 -m unittest discover -s tests -q
```

**Why:** the first command checks that Python is at least version 3.10. The
second displays the available CLI options. The third runs the mocked tests and
should finish with `OK`. The `&&` between commands stops the sequence if a
command fails. These tests verify software behavior, not a real phone, kernel,
boot, or installation. If your default `python3` is older than 3.10, install a
newer Python from a trusted source and use that interpreter for the commands
below.

### 4. Check an Android device

1. Start Android normally on the phone. On many phones, opening **Settings →
   About phone** and tapping **Build number** seven times reveals Developer
   options; the exact names and steps vary by manufacturer. Enable **USB
   debugging** in Developer options. This is not bootloader unlocking.
2. Connect the phone with a data-capable USB cable, unlock the screen, and
   approve the computer's USB debugging authorization prompt. Only authorize
   computers you trust.
3. With one phone connected, copy and paste:

```sh
python3 -m devicecheck --transport adb
```

**Why:** `--transport adb` uses Android Debug Bridge to select the authorized
phone and read only the allowed properties. It compares the reported identity
with the included reference profile. It does not install or change the device's
software. See [what the result means](#understanding-the-result) before making
any decision; no result authorizes flashing.

## More copy-and-paste commands

Run these from `ios-sweet-portability/`. Choose the command that matches your
situation; a phone is needed except for help and tests.

### Check the phone running Termux

```sh
python3 -m devicecheck --transport local --json
```

**Why:** this reads allowlisted properties from the phone itself and outputs
JSON with property values hidden. It does not query a serial. Report details
can still identify a device, so review and redact output before sharing. See the
[Android phone guide](docs/android-phone.md) for setup, real-phone testing, and
limitations.

### Compare against the `sweet` reference

```sh
python3 -m devicecheck --transport adb --profile sweet
```

**Why:** explicitly choosing `sweet` compares the reported identity with that
profile. An `incompatible` result means a mismatch with that profile only; it
is not proof that future porting is impossible.

### Get a machine-readable report

```sh
python3 -m devicecheck --transport adb --json
```

**Why:** `--json` produces a machine-readable report. The `status` names and
their exit-code meanings remain unchanged, but partial local read failures now
return `unknown`/1 instead of error/3. Observed property values are now hidden
by default (`[hidden]` for present values, `null` for missing/invalid/failed).
Existing scripts that need the previous property values must explicitly add
`--show-properties`. The report is **not anonymous**: review and redact it
before sharing. Argument errors and `--help` still use normal text.

### Show property values privately (optional)

```sh
python3 -m devicecheck --transport local --show-properties
```

**Why:** use this only when you need to inspect your own values locally. In
local mode a custom property can contain a serial or another identifier; the
tool cannot recognize it. Do not post unreviewed output. The same option can
be combined with `--json` or `--transport adb`.

### Let the tool choose a transport

```sh
python3 -m devicecheck --transport auto
```

**Why:** `auto` tries `adb` first and can fall back to fastboot enumeration
when there is no matching adb device or adb is unavailable. An ambiguous,
unauthorized, or otherwise blocked adb device is an error; it is not silently
bypassed. This is also the default if `--transport` is omitted.

### Check for a device already in fastboot

```sh
python3 -m devicecheck --transport fastboot
```

**Why:** this only checks whether one device is visible in fastboot. It cannot
identify the product or chipset and returns `unknown`; it does not query
`getvar`, reboot, or change the device's mode. Do not enter fastboot just to
run the tests.

### Run the detailed test output

```sh
python3 -m unittest discover -s tests -v
```

**Why:** this runs the same mocked test suite as the quick-start check but shows
each test name. No phone, Apple firmware, or network is needed.

## Understanding the result

| Display label (JSON `status`) | Meaning | Exit code |
| --- | --- | --- |
| **Reference identity match** (`supported`) | Reported identity matches a reviewed profile. It is **not** a hardware, firmware, recovery, or flash-safety verification. | `0` |
| **Unknown** (`unknown`) | There is not enough evidence, some local property commands failed, or only fastboot enumeration was performed. This is normal for many phones. | `1` |
| **Reference profile mismatch** (`incompatible`) | With an explicitly selected profile, both reported codename fields agree on a different device. This is a mismatch with that profile only. | `2` |
| Error (`error`) | A tool, connection, device-selection, or profile problem prevented the check. Argument usage errors also return `2`. | `3` for program errors |

For `sweet`, a positive identity result requires both Android codename fields,
manufacturer, model, and an explicitly sourced SoC label to match; a reported
contradictory 64-bit ABI downgrades it to `unknown`. Upstream describes the
identity strings but does not provide a verified transcript of these exact
Android properties. Values are software-reported and can be missing, changed,
or spoofed. Even a `supported` result is **not permission to unlock or flash**.
Read the exact rules and privacy details in [the device-check guide](docs/device-check.md).

## Troubleshooting

- **`No module named devicecheck`:** enter the `ios-sweet-portability/` folder
  first, then rerun the command. If you are at the repository root, copy
  `cd ios-sweet-portability`.
- **Python is older than 3.10:** install a newer Python interpreter and use it
  instead of the older `python3` in the examples.
- **`adb` or `fastboot` is not installed:** install Platform Tools for your
  Linux distribution and ensure the relevant executable is on `PATH`. The
  test suite and Android local mode do not require either tool.
- **Local mode cannot run `getprop`:** run it on Android in Termux and check
  device restrictions; some vendors may block access. Do not root the phone to
  bypass this. See the [Android phone guide](docs/android-phone.md).
- **ADB is unauthorized, offline, or finds no device:** start Android normally,
  unlock the screen, enable USB debugging, approve the computer's prompt, and
  try a data-capable cable or another USB port. Check Linux USB/udev permissions
  if the device is inaccessible; do not use root as a workaround.
- **Fastboot finds no device:** the phone must already be in fastboot. Check the
  cable and Linux USB/udev permissions; do not change modes or unlock a
  bootloader just to run the tests.
- **Multiple devices:** disconnect the extras and retry. Advanced users can
  select one locally with `--serial`; never publish the serial or a shell
  history containing it.
- **`unknown`:** this is a conservative result, not necessarily a tool failure.
  A ROM may omit properties even on a `sweet`. Fastboot-only checks always
  return `unknown` because product identity is not queried.

## Scope and evidence

This project includes a sourced [`sweet` reference profile](profiles/sweet.json),
strict matching, text/JSON reports with raw tool diagnostics suppressed, mocked
tests, and a framework for evidence-backed research profiles. A profile cannot
create drivers, a boot chain, a recovery plan, or a working port; no additional
device is claimed supported.

The reference was inspected at upstream commit
[`45263bee51df4a0f55cdf9c649af886399488ddb`](https://github.com/dipa-studio/ios-sweet/commit/45263bee51df4a0f55cdf9c649af886399488ddb)
on 2026-10-31. [Sources and conflicting status reports](docs/sources.md) and
the [architecture guide](docs/architecture.md) distinguish upstream claims
from work independently done here. No physical-device, kernel, image, QEMU, or
installation test has been performed for this project.

## Research guides

- [Run the checker on an Android phone with Termux](docs/android-phone.md)
- [Device checker: commands, matching and privacy](docs/device-check.md)
- [Architecture: boot chain, hardware and iOS root](docs/architecture.md)
- [Porting a different device](docs/porting.md)
- [Upstream build and installation research](docs/installation-research.md)
- [Recovery, backup and safety](docs/safety-recovery.md)
- [Evidence index and upstream status discrepancies](docs/sources.md)
- [Adding evidence and tests](CONTRIBUTING.md)

## Attribution and licensing

Credit to **dipa-studio and ios-sweet contributors** for the original research.
The upstream project is MIT licensed, but its build also references separately
licensed third-party projects. Apple's open-source XNU is not the same thing as
proprietary iOS firmware and userland. This repository includes no Apple
firmware, generated firmware images, partition backups, or device identifiers.
See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
