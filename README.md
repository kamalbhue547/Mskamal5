# devicecheck

[![CI](https://github.com/kamalbhue547/Mskamal5/actions/workflows/python-package.yml/badge.svg)](https://github.com/kamalbhue547/Mskamal5/actions/workflows/python-package.yml)
![Python 3.10–3.14](https://img.shields.io/badge/python-3.10--3.14-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A dependency-free Python CLI for read-only comparison of Android phone properties
with documented reference profiles. It supports adb on a host and local getprop
on Android/Termux. Fastboot mode only enumerates devices. It **does not install
iOS, unlock, reboot, erase or flash**. Reported properties can be spoofed: a
match is not a hardware verification or permission to flash. Upstream's separate
experimental root-image flash erases Android userdata.

## Install and run

Requires Python 3.10 or newer. From a checkout:

```sh
python -m pip install .
devicecheck --list-profiles
devicecheck --transport adb --explain
# On an Android phone with Termux:
devicecheck --transport local --json
```

Use `--profile-dir DIR` to load your own JSON profiles instead of bundled ones;
validation checks structure, not the truth of their evidence. Values are hidden
by default; `--show-properties` displays potentially identifying information.
Review all output before sharing. `--dry-run` is an alias for `--explain`; the
tool is always read-only and already shows comparison checks.

Example (abbreviated, synthetic):

```text
Result: REFERENCE IDENTITY MATCH
Transport: adb
Comparison:
  ro.product.device: match (expected: sweet or sweetin)
  ro.soc.model: not available (expected: SM7150 or Snapdragon 732G)
```

On Android 11 and earlier, an absent `ro.soc.model` is reported as not available;
the SoC remains unverified. This checker has not been tested on a physical
phone. Tests use synthetic and mocked output, not real device captures.

| Exit code | Meaning |
| --- | --- |
| 0 | Reference identity match (or successful profile listing) |
| 1 | Unknown / insufficient or conflicting evidence |
| 2 | Explicitly selected profile mismatch |
| 3 | Error |

See the [full guide](ios-sweet-portability/README.md),
[Android instructions](ios-sweet-portability/docs/android-phone.md), and
[contribution guide](ios-sweet-portability/CONTRIBUTING.md). Run tests with
`python -m unittest discover -q` from the repository root.
