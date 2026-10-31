# Evidence and source index

Inspected upstream: [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet),
commit [`45263bee51df4a0f55cdf9c649af886399488ddb`](https://github.com/dipa-studio/ios-sweet/commit/45263bee51df4a0f55cdf9c649af886399488ddb)
(commit author date 2026-10-23; inspected 2026-10-31). Every source link below
is pinned to that revision. Upstream's MIT license and its third-party credits
are in [notices](../THIRD_PARTY_NOTICES.md). This project paraphrases and links
the research; it does not vendor upstream code or Apple files.

## What was inspected

| Source | Relevant evidence |
| --- | --- |
| [README][readme] | Target identity, reported milestones and limitations, boot chain, build/install, data-loss warning, hardware facts and credits. |
| [NOTES.md][notes] | Time-ordered hardware observations, bring-up history, newer work, untested work, recovery/logging and the explicit fastboot restriction. Its working handoffs are not all simultaneous current state. |
| [shim entry][entry], [loader][loader], [FDT parser][fdt], [MMU][mmu], [UFS probe][probe], [shim build][shim-build] | Bootloader handoff, live FDT initrd bounds, Mach-O payload and ADT handoff, optional MMU diagnostics, storage probe and v2 packaging. |
| [ADT generator][adt], [payload builder][payload], [root builder][root], [root tweaks][tweaks], [boot unpacker][unpack] | Hard-coded board geometry/addresses, iPhone identity, payload, HFS+ assembly, configuration modifications and v0–v2 stock-image extraction. |
| [XNU workflow][workflow], [XNU README][xnu-readme], [patch tree][patch-tree] | Pinned builder, macOS runner, staging, patch series, artifact upload and build configuration. |
| [platform expert][platform], [timer][timer], [UFS root][ufs], [UFS writes][writes], [display][display], [HID][hid], [touch][touch] | Concrete examples of device tree, interrupts, storage read/write, framebuffer and input integration. |
| [QEMU guide][qemu], [license][license], [credits][credits] | Scope of emulation and attribution/licensing. |

## Status discrepancies and verification limits

- The [README][readme-status] reports **six** A55 cores, no home navigation and
  no working Wi-Fi/Bluetooth/cellular. The later [2026-10-18 note][later-note]
  reports a home-gesture fix in a specific boot, eight-core work in another,
  and a USB ECM ping test, while stating Internet over USB was not working.
  It says a subsequent networking-trace build was **not booted**. These are
  upstream-reported, configuration-specific observations, not measurements by
  us. They should not be merged into a claim that all functions work in every
  image or variant.
- [`0078-sweet-smp-8-cores.patch`][smp] changes the CPU limit; source presence
  is evidence of code, not proof of an independently reproduced test. Similarly,
  a workflow's artifact step running after failure is not proof of a build.
- Upstream says `sweet` includes global or Indian variants but warns that
  variants or firmware may need changes. It does **not** provide a verified
  transcript for our selected Android `getprop` fields or establish additional
  codename aliases. Our strict matching is a heuristic, not hardware evidence.
- The latest upstream site discusses other device families, but we have not
  independently validated any such port or its licenses. This repository
  intentionally records no additional supported device.
- We have not run upstream kernel builds, QEMU, Apple image extraction, or any
  physical phone test. Our automated checks use mocked command output only.

[readme]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md
[notes]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/NOTES.md
[entry]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/start.S
[loader]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/loader.c
[fdt]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/fdt.c
[mmu]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/mmu.c
[probe]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/ufs.c
[shim-build]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/build.sh
[adt]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/mkadt.py
[payload]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/mkpayload.py
[root]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/mkiosroot.sh
[tweaks]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/sweet-root-tweaks.py
[unpack]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/unpack_bootv2.py
[workflow]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/.github/workflows/xnu.yml
[xnu-readme]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/README.md
[patch-tree]: https://github.com/dipa-studio/ios-sweet/tree/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches
[platform]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0016-sweet-device-tree-platform-expert.patch
[timer]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0017-sweet-device-tree-virtual-timer-irq.patch
[ufs]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0028-sweet-ufs-root-device.patch
[writes]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0030-sweet-ufs-writes.patch
[display]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0046-sweet-iosurface-iomfb.patch
[hid]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0058-sweet-hid-event-services.patch
[touch]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0063-sweet-goodix-geni-packing.patch
[qemu]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/docs/QEMU_TESTING.md
[license]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/LICENSE
[credits]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L201-L203
[readme-status]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L11-L35
[later-note]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/NOTES.md#L5-L21
[smp]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0078-sweet-smp-8-cores.patch
