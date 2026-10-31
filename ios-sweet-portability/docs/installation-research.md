# Upstream build and installation research — sweet only

> **Do not treat this as an installer or a procedure for a different phone.**
> Upstream's root-image flash overwrites **Android `userdata` and erases its
> data**. Unlocking a bootloader may erase data too. A `fastboot boot` of a
> kernel is temporary only with respect to boot partitions; the code it runs
> may still write storage. Read [safety and recovery](safety-recovery.md).

The steps below summarize the [upstream README at the inspected commit][readme]
and explain **why** each stage exists. They have **not been independently
executed or verified** in this project. They refer to a Redmi Note 10 Pro
`sweet` and specific upstream artifacts, not a generic Android recipe. Consult
the linked, pinned upstream commands and its detailed notes; check changes if
using a different upstream revision. We do not provide a one-click installer
or generated images.

## Stages and dependencies

| Stage | What upstream describes and why | Evidence / verification boundary |
| --- | --- | --- |
| 0. Recoverability and stock DTB | Back up personal data and device-specific calibration/boot-critical partitions; the stock boot image supplies a DTB to the shim build. Unlocking is a separate potentially data-erasing prerequisite. The upstream extractor only handles boot headers v0–v2. | [Backups and DTB][backup], [extractor][unpack]. Whether a backup can be read or restored depends on the device, encryption, firmware and recovery access. We have not validated a restore. |
| 1. Kernel | The upstream GitHub Actions workflow uses a macOS 14 runner, `MACOS_VERSION=13.5` (xnu-8796 generation), SWEET configuration, pinned `blacktop/darwin-xnu-build`, staged open-source libpthread/HFS/BearSSL, and the patch series. The built kernel supplies XNU plus sweet platform and driver changes. | [Workflow][workflow], [staging scripts][staging], [patch overview][patches]. A workflow uploading an artifact under `if: always()` does **not** itself prove a successful build; inspect the actual run conclusion, logs and checksums. We did not run it. |
| 2. Proprietary root inputs | Upstream instructs the user to obtain the iPhone X (`iPhone10,3`) iOS 16.7.16 / 20H392 IPSW from Apple and identify OS, SystemOS and AppOS images via `BuildManifest.plist`. `mkiosroot.sh` uses apfs-fuse, HFS+ tools, rsync, mounts and privileges to copy them into one case-sensitive journaled HFS+ image (16 GiB default), preserve metadata, and set up cache links and directories. | [README root stage][root-stage], [builder][root-script]. The README does not give a complete, independently verified extraction procedure for each named DMG or an acquisition URL. Availability, permissions, licensing, filesystem support and exact dependencies must be checked locally; we have not obtained or processed the IPSW. |
| 3. Root tweaks and sparse format | Upstream repairs/checks and mounts the image, runs `sweet-root-tweaks.py`, unmounts it, and converts it to Android sparse format with `img2simg`. The script adjusts daemon/configuration state, creates expected directories, disables problematic services and skips parts of setup; the resulting root configuration is **modified**, even where upstream describes userland binaries as unmodified. | [Root commands][root-stage], [tweaks and rationale][tweaks]. These are bring-up compromises, not a secure or production iOS configuration. No root image was built or examined here. |
| 4. iPhone X ADT input | The upstream ADT builder copies `/product` from the Apple D22AP tree to support MobileGestalt's iPhone X identity. Upstream describes `remotezip.py` plus `ipsw` extraction to obtain it locally. | [ADT extraction][adt-stage], [generator][adt-script]. `mkadt.py` only warns when the tree is absent and continues without `/product`; absence is an unresolved input, **not** evidence the resulting image will reach the home screen. Apple artifacts stay out of Git. |
| 5. Boot payload and shim | `mkadt.py --highmem` describes sweet's upper RAM bank and hardware; `mkpayload.py` packages the kernel, ADT and boot arguments; `shim/build.sh` compiles the arm64 shim and packages a boot image v2 with the locally extracted stock DTB. It expects the aarch64 GNU toolchain, binutils, `mkbootimg`, and host build utilities. | [README boot stage][boot-stage], [payload][payload], [shim build][shim-build]. The exact header, addresses, stock DTB and arguments are board/firmware dependent. We did not build or test them. |
| 6. Destructive storage flash; temporary boot | Upstream's command flashes the sparse root image to `userdata`, **destroying Android user data**, then uses temporary `fastboot boot` for the shim. This distinction explains why the root persists while boot partitions need not be flashed. | [Upstream commands and warning][flash]. We intentionally do not reproduce a copy-paste flash command here. No device has been flashed or booted by this project. |
| 7. Diagnostics/recovery | Upstream keeps a kernel log ring at the end of `userdata` and describes booting recovery temporarily to retrieve it. Logs and backups may contain personal or device-specific data. | [Logging instructions][logs], [notes and fastboot restriction][notes]. Recovery availability, log contents and restoration have not been independently verified. |

## Testing and unresolved questions

- Upstream provides a [QEMU guide][qemu] and notes for kernel-only testing. A
  QEMU pass does not prove real bootloader behavior, UFS writes, panel or input.
  We did not run QEMU or upstream Actions.
- Upstream notes explicitly say **never `fastboot getvar`** in their phone
  workflow, without giving a reason. This project avoids it altogether; our
  fastboot mode can establish only that a device is present. [Source][notes].
- The README and later notes differ about CPU count and navigation. Patch
  presence and uploaded artifacts are not a substitute for a reproduced test;
  see [sources.md](sources.md#status-discrepancies-and-verification-limits).
- The upstream README mentions variant/firmware changes may be necessary. We
  have not verified this process on any variant, nor confirmed whether a
  particular backup/recovery plan survives unlocking or re-locking.

Apple's open-source XNU and separately licensed libraries are not a license to
redistribute proprietary iOS firmware, userland, the extracted Apple device tree,
or a generated root. Obtain and use inputs only as legally permitted; review
all applicable licenses. See [third-party notices](../THIRD_PARTY_NOTICES.md).

[readme]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L50-L143
[backup]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L50-L62
[unpack]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/unpack_bootv2.py#L1-L25
[workflow]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/.github/workflows/xnu.yml
[staging]: https://github.com/dipa-studio/ios-sweet/tree/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches
[patches]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L165-L188
[root-stage]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L75-L89
[root-script]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/mkiosroot.sh
[tweaks]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/sweet-root-tweaks.py#L1-L29
[adt-stage]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L91-L96
[adt-script]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/mkadt.py#L44-L63
[boot-stage]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L98-L119
[payload]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/mkpayload.py
[shim-build]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/build.sh
[flash]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L121-L129
[logs]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L131-L139
[notes]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/NOTES.md#L39-L48
[qemu]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/docs/QEMU_TESTING.md
