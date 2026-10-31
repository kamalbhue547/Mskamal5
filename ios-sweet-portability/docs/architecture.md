# Architecture and hardware-specific dependencies

This is a **source-based explanation of upstream**, not an implemented port in
this repository. The inspected revision and evidence are indexed in
[sources.md](sources.md). Upstream reports a boot to the home screen on its
Redmi Note 10 Pro, but we have not reproduced it. Firmware and board variations
matter even within a product family.

## Boot chain: two device trees and two kinds of root

Upstream describes this sequence:

```text
unlocked Xiaomi ABL -> temporary Android boot image -> sweet shim
  -> XNU Mach-O + generated Apple Device Tree + boot arguments
  -> sweet UFS driver -> HFS+ root stored in Android userdata
  -> dyld / launchd -> iOS daemons, backboardd, SpringBoard
```

The **temporary boot image is not the root image**. The former contains a
bare-metal loader and a payload; the latter is separately placed on storage.
Temporary boot does not flash a boot partition, but **executing the kernel can
write storage**, and upstream's separate root-image flash erases `userdata`.
[Upstream boot diagram and warning][boot].

1. **ABL and the Android FDT.** On the tested board, the unlocked Qualcomm
   Android bootloader (ABL) accepts a temporary Android boot image. The shim's
   arm64 Linux Image header tells ABL how to enter it; the shim entry expects
   EL1, the MMU and data cache off, and an FDT pointer in `x0`. The upstream
   build wraps the shim with a **boot image v2** header and a DTB extracted
   from the stock boot image. Those entry conditions and image format must not
   be assumed for another device. [Entry][entry], [shim build][shim-build].
2. **Payload handoff.** `mkpayload.py` packs the XNU Mach-O segments, an Apple
   Device Tree (ADT), and boot arguments into the ramdisk; it resolves chained
   fixups. The shim reads the live FDT `/chosen` initrd bounds, copies payload
   segments and the ADT to their configured physical addresses, constructs XNU
   `boot_args` including framebuffer geometry, and jumps to the kernel entry.
   The loader's copy/handoff runs with MMU and caches off. There is also 16 KiB
   MMU diagnostic code in the shim; its existence does not mean the payload
   path uses that diagnostic. [Loader][loader], [payload][payload], [MMU][mmu].
3. **Generated ADT, not an automatic DTB conversion.** The ordinary Android
   FDT supplies the initrd location. `mkadt.py` separately synthesizes the
   Apple-format tree XNU expects from **hard-coded sweet** RAM, interrupt,
   framebuffer and UFS facts, CPU topology, and iPhone X identity. It can copy
   `/product` from an Apple D22AP device tree extracted locally; if absent,
   the script warns and omits it. Upstream says userland needs that data for
   MobileGestalt. This Apple tree is not distributed here. [ADT generator][adt].
4. **Patched XNU.** Upstream CI builds the open-source xnu-8796 generation with
   a SWEET machine configuration and an ordered patch series. The patches add
   a device-tree platform expert, non-Apple interrupt/timer support, CPU
   startup, storage, HFS, display, HID and many bring-up/security stubs. The
   workflow also stages separately sourced libpthread, HFS and BearSSL. This
   is not stock iOS's Apple-silicon kernel booting unchanged. [CI][workflow],
   [platform patch][platform], [patch overview][patches].
5. **Root and userland.** A sweet-specific UFS driver reuses the controller
   state left by ABL, finds a named GPT partition (default `userdata`), and
   exposes `ufsroot0`. The root is a case-sensitive, journaled HFS+ image
   assembled from iPhone X iOS 16.7.16 OS, SystemOS and AppOS images; dyld
   links, directories and configuration tweaks enable the bring-up. The
   boot arguments can enable UFS and root writes; a persistent log also lives
   at the end of `userdata`. [Storage patch][ufs], [root builder][root],
   [tweaks][tweaks], [upstream README][boot].

## What is sweet-specific?

| Area | Observed upstream assumptions, not reusable promises |
| --- | --- |
| Board/SoC | Xiaomi Redmi Note 10 Pro, codename `sweet`, Qualcomm SM7150 / Snapdragon 732G. A compatible SoC alone does not identify the panel, PMIC wiring or firmware. [Identity][identity] |
| Memory and CPU | High-memory bank `0x100000000` + `0xfcc00000`; protected low-memory carve-outs; 16 KiB pages; non-PAC arm64; PSCI via SMC. Memory and allowed exception levels must be rediscovered per board. [ADT][adt], [hardware notes][hardware] |
| Interrupts | GICv3 and virtual-timer INTID 19 on this board; upstream's QEMU configuration uses different values. A wrong interrupt mapping can hang boot. [ADT][adt], [timer patch][timer] |
| Storage | Qualcomm UFS host at `0x01d84000`, bootloader-initialized link, DMA/cache assumptions, GPT name and 4 KiB physical blocks. The original shim UFS probe is read-only with respect to storage; the later XNU driver **can write** when enabled. A different device may use eMMC, another UFS setup, different partitions or encryption. [Probe][probe], [UFS][ufs], [writes][writes] |
| Display | ABL's splash framebuffer is at `0x9c000000`, native 1080×2400. The kernel supplies IOSurface/IOMobileFramebuffer services and CPU-copies frames into it, presenting a 1125×2436 iPhone X canvas to userland. There is no GPU driver in the README's configuration. [Hardware][hardware], [display patch][display] |
| Touch/buttons | Goodix GT9896 at I²C `0x5d`, GENI SE7 and a PM6150L RPMh power vote; button wiring uses SPMI/PMIC paths. Kernel HID services deliver events to iOS. Another touch controller, rail, protocol or wiring needs its own driver and testing. [Hardware][hardware], [touch patch][touch], [HID patch][hid] |
| Identity/security | The ADT supplies synthetic iPhone X identity for iOS userland, not the physical Android model. Upstream disables or stubs major trust, sandbox and data-protection mechanisms; this is research, not secure production iOS. [ADT][adt], [limitations][identity] |

## Evidence and open questions

Upstream's README reports six A55 cores and no working home gesture, while its
later engineering note reports a home-gesture fix and an eight-core kernel
configuration. The note also says a later networking-trace build had **not**
been booted.
Source presence, a CI artifact, or an old note alone is not a test of every
variant. We have not resolved these discrepancies by reproducing them. See
[the evidence index](sources.md#status-discrepancies-and-verification-limits).

[identity]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L1-L35
[boot]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L37-L48
[hardware]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L190-L199
[entry]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/start.S#L1-L38
[shim-build]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/build.sh#L1-L35
[loader]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/loader.c#L1-L8
[payload]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/mkpayload.py#L1-L27
[mmu]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/mmu.c#L1-L13
[adt]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/mkadt.py
[workflow]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/.github/workflows/xnu.yml
[platform]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0016-sweet-device-tree-platform-expert.patch
[patches]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L165-L188
[timer]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0017-sweet-device-tree-virtual-timer-irq.patch
[ufs]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0028-sweet-ufs-root-device.patch#L40-L59
[probe]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/ufs.c#L1-L16
[writes]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0030-sweet-ufs-writes.patch
[display]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0046-sweet-iosurface-iomfb.patch
[touch]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0063-sweet-goodix-geni-packing.patch
[hid]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/xnu/patches/0058-sweet-hid-event-services.patch
[root]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/mkiosroot.sh#L1-L18
[tweaks]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/sweet-root-tweaks.py#L1-L29
