# Researching a new Android target

**No additional device port exists here.** The original targets `sweet`;
sharing a chipset, CPU instruction set, Android version, or a `supported`
identity result does not make a sweet image safe on another board. This guide
is a staged engineering plan, not a flashing recipe. Record the exact model,
region, hardware revision, chipset, firmware/build and available documentation
before any claim. Leave unknown fields unknown.

## Gate 0 — ownership, evidence, recovery and consent

- Confirm you own/are authorized to work on the device; understand vendor and
  Apple licensing. Use legally obtained inputs and follow their terms.
- Read [safety and recovery](safety-recovery.md). Make and **verify** offline
  personal backups; identify per-device calibration and a model/firmware-specific
  recovery route before unlocking or modifying anything. Unlocking may wipe data.
- Find official source, bootloader documentation, board schematics if available,
  a known-good stock firmware/recovery package, and published Linux device trees
  and drivers. Cite immutable revisions and label claims vs measurements.
  Redact serials, identifiers, MAC addresses, keys and user data.
- Use this repository's checker only for a bounded read-only inventory. Its
  `unknown` result is not a request to try sweet images. Upstream's note says
  not to use `fastboot getvar` in its workflow; this checker avoids it.

## Gate 1 — bootloader and boot ABI

1. Determine whether the vendor permits unlocking, whether unlocking wipes
   data, any account/wait restrictions, anti-rollback state, AVB verification,
   lock/relock hazards, available boot modes, and whether **this firmware**
   permits a temporary boot. Do not infer these from a codename or generic
   fastboot availability. Never relock against modified or mismatched images.
2. Study boot image header/version, required signing, kernel/ramdisk/DTB and
   `vendor_boot`/`init_boot` placement, bootconfig, DTBO, A/B slots and
   dynamic partitions where applicable. Document bootloader-provided exception
   level, register contract, cache/MMU state and memory reservations.
3. A port may need a **new shim**, loader format or other boot strategy. The
   sweet shim's Android v2 assumptions and hard-coded locations are not a
   configuration-only abstraction. Use host-only tests and review first; even
   temporary code can write persistent storage or leave a device unusable.

## Gate 2 — SoC, kernel and device tree

1. Identify the actual CPU features, 16 KiB translation support, pointer
   authentication assumptions, exception level, cache coherency, boot CPU and
   PSCI/firmware behavior. Map RAM banks, protected carve-outs and permitted DMA.
2. Obtain authorized, redacted device-tree sources/blobs and cross-check them
   against vendor kernel sources, firmware and actual revision. Discover GIC
   variant, interrupt IDs, timer frequency, power domains, IOMMU and MMIO.
   Raw live trees can contain personal identifiers; keep them private.
3. Design a board-specific ADT and platform expert, not just a renamed sweet
   profile. Adapt XNU machine configuration, interrupt/timer paths, memory maps,
   CPU topology and required support libraries. Run build, patch-order, unit and
   emulated tests; record versions and checksums. QEMU cannot validate physical
   register maps, display, PMIC or recovery.

## Gate 3 — storage, display and input

- **Storage:** establish UFS/eMMC controller and firmware state, sector sizes,
  cache/DMA/IOMMU requirements, partition layout, encryption and A/B or logical
  partition scheme. Design and review a board-specific driver and bounded
  read/write strategy. A partition called `userdata` is not proof it can safely
  host the upstream image. Protect calibration and boot-critical partitions.
- **Display:** determine the panel, initialization, pixel format, stride,
  orientation, resolution, reserved framebuffer and bootloader handoff; implement
  an appropriate display pipeline and power management. A bootloader splash is
  not guaranteed to remain usable. GPU support is a separate major project.
- **Touch and keys:** identify controller and protocol, bus/interrupt/GPIO,
  firmware, regulator/PMIC and power sequencing; implement input and HID mapping.
  A shared SoC says nothing conclusive about the touch controller.
- For each, first use a reviewed non-destructive design and isolated host tests;
  only a consenting owner with a device-specific plan can authorize any
  hardware experiment. Even probes can disturb controllers.

## Gate 4 — root, userspace and recovery

- Establish legally obtained userland, filesystem, architecture, ABI, trust,
  services and image-format requirements. Do not redistribute Apple firmware or
  generated images. A different kernel/board can require significant userspace
  integration; the upstream root is not a general Android image.
- Prove recovery access, understand a device-specific restoration procedure,
  and record what a backup cannot restore (for example encryption keys lost on
  unlock). Do not assume fastboot commands or partitions are equivalent across
  vendors. Confirm the owner approves each potentially destructive step.
- Only after review and device-specific measurements, conduct staged hardware
  tests, record exact artifacts, firmware, dates and observations, and distinguish
  bootloader acceptance, kernel boot, root mount and working input. Each is a
  separate milestone, not a general support claim.

## Profile and evidence lifecycle

Add an incomplete, `research_only` profile with cited observations and `null`
unknowns as described in [profiles/README.md](../profiles/README.md). Add mocked
tests for missing values and conflicts. Promote a profile only after an actual
reference port or documented hardware-tested port exists and is reviewed. The
machine-readable file describes facts; **drivers, bootloader integration,
recovery and tests still have to be engineered**. See [CONTRIBUTING](../CONTRIBUTING.md).
