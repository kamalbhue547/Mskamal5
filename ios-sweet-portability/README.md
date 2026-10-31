# ios-sweet portability lab

A **research and device-identification toolkit**, not an iOS installer. It studies
[dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet), an experimental
XNU and iOS userland bring-up for the **Redmi Note 10 Pro (`sweet`)**. This
project does not build a kernel, create an iOS image, unlock, reboot, flash, or
port iOS to any additional phone. **iOS cannot be assumed to run on every
Android device**; a new target requires substantial device-specific engineering
and physical testing.

> **DATA LOSS AND SECURITY:** Upstream's root-image flash overwrites Android
> **`userdata`**, erasing Android user data. Unlocking a bootloader may also
> erase data, and restoration can fail or be impossible. Upstream's experiment
> disables major security mechanisms; do not use it for personal data. Never
> flash a `sweet` image to an unverified device, including one with the same
> chipset. See [recovery and safety](docs/safety-recovery.md).

## What is implemented

- A dependency-free Python Linux CLI that selects **one** device and reads a
  short allowlist of Android properties through `adb`. It uses `fastboot`
  only to list devices already in fastboot; it **does not** query `getvar`,
  because the upstream phone workflow explicitly says not to. It never sends
  unlock, reboot, flash, erase, push or write commands.
- A sourced [`sweet` reference profile](profiles/sweet.json), strict matching,
  redacted text/JSON reports, helpful errors, and automated tests using mocked
  outputs. No extra device is claimed supported.
- A documented framework for evidence-backed research profiles. A profile file
  cannot create a driver, boot chain, recovery plan, or working port.

The reference was inspected at upstream commit
[`45263bee51df4a0f55cdf9c649af886399488ddb`](https://github.com/dipa-studio/ios-sweet/commit/45263bee51df4a0f55cdf9c649af886399488ddb)
on 2026-10-31. [Sources and conflicting status reports](docs/sources.md) and
the [architecture guide](docs/architecture.md) distinguish upstream claims
from work independently done here. No physical-device, kernel, image, QEMU, or
installation test has been performed for this project.

## Requirements and quick start

A Linux host, Python **3.10 or newer**, and Android SDK Platform Tools (`adb`
for Android mode; `fastboot` for fastboot enumeration). Tests need only Python's
standard library and no phone. On a Debian/Ubuntu system where the packages are
available:

```sh
sudo apt-get update
sudo apt-get install -y python3 adb fastboot
```

From the parent directory:

```sh
cd ios-sweet-portability
python3 --version
python3 -m unittest discover -s tests -v
python3 -m devicecheck --help
```

For a phone **already running Android**, enable USB debugging manually, connect
it, approve the computer's authorization prompt, and run:

```sh
python3 -m devicecheck --transport adb
# Optional: compare specifically to sweet and emit JSON
python3 -m devicecheck --transport adb --profile sweet --json
```

For a device **already** in fastboot, this checks presence only; it cannot
identify the product and returns `unknown`:

```sh
python3 -m devicecheck --transport fastboot
```

`--transport auto` (the default) prefers adb and otherwise enumerates fastboot.
If multiple devices are present, disconnect the extras or select one locally
with `--serial`; do not publish the serial. The tool suppresses serial numbers
and raw command errors, but review all output before sharing: customized
properties may still identify a person or device. `adb` itself may start its
local server and prompt for authorization. See the full
[CLI and privacy contract](docs/device-check.md) for timeouts and exit codes.

## What the results mean

- **supported** — only a strict *reported-identity match* to a reviewed
  supported reference profile. For `sweet`, both Android codename fields,
  manufacturer, model, and an explicitly sourced SoC label must match; a
  reported contradictory 64-bit ABI downgrades the result to unknown. The
  upstream describes these identity strings, but does not provide a verified
  transcript of these exact Android properties. They are software-reported and
  can be absent, modified, or spoofed. This is **not** validation of the actual
  hardware, firmware, bootloader, kernel, recovery, or flashing safety.
- **unknown** — not enough evidence, no profile, conflicting/unsupported
  property values, a research-only profile, or fastboot-only enumeration. This
  is expected on many phones, including a `sweet` whose ROM omits a property.
- **incompatible** — only when a specifically selected profile has two
  agreeing Android codename fields naming another device. This is an identity
  mismatch **with that profile**, not proof that the phone can never be ported.

A program error is separate from these classifications. Nothing about a
classification is an instruction to unlock or flash. The exact checks and exit
codes are described in [device-check.md](docs/device-check.md).

## Guides

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
