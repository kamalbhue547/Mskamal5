# Run the device checker on an Android phone

This guide runs the **read-only identity checker** on the phone itself using
Termux. It does **not** install iOS, unlock the bootloader, reboot, flash, erase,
or write directly to Android partitions. There is no universal iOS installer
for Android; the original experiment targets Redmi Note 10 Pro `sweet`.
Upstream's separate root-image flash erases Android `userdata`, and unlocking can
also erase data.
A checker result is never permission to flash.

## Before you start

- Use a phone running Android normally, with an internet connection for Termux
  packages and the project download. A computer, USB debugging, root, Apple
  firmware, and Android Platform Tools are not needed for this local mode.
- Termux's [official installation instructions](https://github.com/termux/termux-app#installation)
  describe full app/package support for Android 7 and newer. Termux, Python,
  property access, and vendor restrictions may still vary; this project has
  **not been tested on a physical Android device** and is not guaranteed to
  work on every phone. [Pinned Termux source][termux-install].
- Setup installs packages and copies files into Termux's app storage; Python
  may also create cache files there. The checker itself only reads a small
  allowlist of Android properties. It does not request shared-storage access or
  root.

## 1. Install and open Termux

Install Termux using a trusted source listed in the
[official Termux installation guide](https://github.com/termux/termux-app#installation),
then open the app and wait for its initial setup to finish. Do not use APKs
from unknown sources. If you already have Termux, follow its official guidance
before switching sources: app and plugin signatures differ, and uninstalling
Termux can remove its files. Back up anything important first.

## 2. Install Git and Python

In the **Termux terminal on the phone**, copy and paste:

```sh
pkg update &&
pkg install -y git python
```

**Why:** `pkg update` refreshes Termux's package lists; `pkg install` adds Git
for downloading the project and Python for running it. These commands change
Termux's packages and app storage; they do not unlock the bootloader or flash
or erase partitions. No `sudo`, `su`, `pip install`, or Termux:API plugin is
needed.

## 3. Download the project

For a first-time checkout, copy and paste:

```sh
cd "$HOME" &&
git clone https://github.com/kamalbhue547/Mskamal5.git &&
cd Mskamal5/ios-sweet-portability
```

**Why:** this downloads the public repository into Termux's home directory and
enters the project folder. If `Mskamal5` is already in your Termux home,
`git clone` will refuse to overwrite it. Instead, enter your existing copy:

```sh
cd "$HOME/Mskamal5/ios-sweet-portability"
```

The following commands must be run from that project folder. Your checkout
must include `--transport local`; use the help command in the next step to
check. If it does not, obtain an updated version of the project before
continuing.

## 4. Check Python and run the tests

```sh
python3 -c 'import sys; print("Python " + sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 10) else "Python 3.10 or newer is required")' &&
python3 -m devicecheck --help &&
python3 -m unittest discover -s tests -q
```

**Why:** the first command requires Python 3.10 or newer, the second lists the
options, and the third runs mocked tests, which should finish with `OK`. The
`&&` stops the sequence if a command fails. These tests do **not** prove that a
physical phone, an iOS build, a boot, or an installation works. A phone's OS or
Termux environment may limit subprocesses or tests.

## 5. Check this phone

```sh
python3 -m devicecheck --transport local
```

**Why:** `local` runs Android's `/system/bin/getprop` for individual allowlisted
property keys on this phone. It does not use adb, fastboot, a serial, a shell
script, or a full property dump. It compares the reported values with the
included profile; missing or inaccessible data can result in `unknown` or a
helpful error. `auto` remains the computer-oriented adb/fastboot mode, so
include `--transport local` on the phone.

To compare specifically with the `sweet` reference (not to install it):

```sh
python3 -m devicecheck --transport local --profile sweet
```

Optional JSON output:

```sh
python3 -m devicecheck --transport local --json
```

The tool does not query a hardware serial in local mode, but custom properties
can still contain serials or other identifying details. It cannot recognize a
serial embedded in those values because it does not read the serial. Review and
redact **all** output before sharing; never share an IMEI, serial, key, or
private log. `--serial` is for selecting an adb/fastboot device and is rejected
in local mode.

## Understand the result

- **`supported`** means the reported identity matches the strict `sweet`
  reference profile. It does **not** verify the physical device, a working
  iOS port, bootloader, recovery, or flash safety.
- **`unknown`** means there is not enough matching evidence. This is expected
  for most phones, and even a `sweet` ROM may omit a required property.
- **`incompatible`** can occur only when a profile was explicitly selected and
  both reported codename fields agree on a different device. It is a mismatch
  with that profile, not proof that a future port is impossible.
- **Error** means a tool, permission, or profile problem prevented the check.

See the [matching rules and exit codes](device-check.md) for details.

## Troubleshooting

- **`No module named devicecheck`:** enter the project folder in step 3 before
  running the command.
- **`invalid choice: local`:** the checkout predates local mode. Check the
  project version and obtain an updated checkout; `auto` will not read the
  phone locally.
- **`could not run Android /system/bin/getprop` or a permission error:** confirm
  you are running inside Android, not on a computer, and check your device's
  app restrictions. Some vendor builds may block access. Do not root the phone
  or weaken security just to run the checker; the [Linux adb guide](../README.md#quick-start-linux)
  is an alternative where available.
- **`unknown`:** missing or different software-reported properties are normal
  on many devices. It does not mean the checker installed or tested iOS.
- **Termux package/network problems:** use the official Termux documentation to
  troubleshoot your source and repository configuration. Do not paste
  untrusted install scripts into the terminal.

[termux-install]: https://github.com/termux/termux-app/blob/8629e632fcb95da272221be327db653fb24befe9/README.md#L51-L63
