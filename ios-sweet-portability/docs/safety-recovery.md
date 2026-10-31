# Recovery and safety

> **Data-loss warning:** the original sweet installation flashes an iOS root
> image into Android **`userdata`**, destroying Android user data. Bootloader
> unlocking may also wipe data, sometimes before a backup can be made. The
> original experiment has permissive/stubbed security and is not suitable for
> personal data. Temporary boot does not mean subsequent code cannot write.
> [Upstream warning][warning], [root flash][flash].

This is a planning guide, not a universal backup or restoration procedure.
Every phone's firmware, encryption, partition layout, bootloader policy,
anti-rollback, slots and recovery options differ. The authors of this project
have not verified a restore for any device.

## Before unlocking or experimenting

1. **Back up important data independently.** Use the device's supported data
   export/backup mechanisms; check that files, photos, app data and account
   recovery are actually readable elsewhere. An encrypted userdata image may
   be unusable after unlock or factory reset if its keys are destroyed. A
   backup is not proven until its restore is verified under appropriate conditions.
2. **Plan device-specific restoration.** Identify the exact model, region,
   hardware revision, currently installed firmware, slots and compatible stock
   recovery/firmware packages. Verify their authenticity and checksums using
   trustworthy vendor instructions. Understand how to reach and use recovery
   without assuming `fastboot boot` exists. Restoration itself can overwrite data
   or fail; plan and obtain explicit consent before performing it.
3. **Protect unique calibration.** Upstream mentions partitions such as
   `persist`, `modemst1`, `modemst2`, `fsg` and `fsc`, plus boot-related
   partitions. Names, access and importance vary by device. These backups can
   include serials, IMEI, radio calibration, keys and personal information;
   keep them encrypted/offline and **never commit or share** them. Do not copy
   another phone's calibration or assume a copied image restores lost keys.
   [Upstream backup note][backup].
4. **Understand irreversible conditions.** Unlocking may void support, trigger
   a wipe, change security state, require vendor approval or be impossible;
   anti-rollback and secure boot may prevent recovery. Never blindly re-lock a
   bootloader with altered or mismatched partitions: that can prevent booting.
5. **Set a stop condition.** Work with the device owner, suitable power/cable,
   a known recovery path, and a plan for a failed or interrupted operation.
   If any part is unknown, stop rather than guessing. A name match from the
   checker is not approval to proceed.

## During research

- Our tool reads a limited property allowlist and lists devices; it does not
  reboot, unlock, flash or erase. Upstream says not to use `fastboot getvar`
  in its workflow, so our tool does not do so. [Source][notes].
- Treat *all* hardware experiments as potentially risky, including code
  temporarily loaded into RAM: it may access flash, hardware registers, power
  rails or the display. Do not run sweet images on a different phone.
- The original root runs with unsealed root, permissive signing/sandbox and
  a stub keystore. Do not log in, store secrets, or regard it as protected iOS.
- Do not publish dumps, device identifiers, logs without redaction, Apple
  firmware, proprietary generated images or backups. `.gitignore` is a guard,
  not a guarantee; inspect changes and history before publishing.

## After a problem

Stop issuing commands. Record what was actually observed, without publishing
identifiers; do not guess that an erase, re-lock, different firmware or another
phone's calibration will repair it. Consult the exact model's vendor/service
recovery documentation and seek qualified help. There is no universal command
in this repository that can restore an Android device.

[warning]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L3-L9
[flash]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L121-L127
[backup]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L50-L62
[notes]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/NOTES.md#L43-L46
