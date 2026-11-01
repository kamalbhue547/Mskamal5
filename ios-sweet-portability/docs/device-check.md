# Device-check contract

The checker is a **read-only identity comparison**, not a compatibility
validator. It sends no unlock, reboot, flash, erase, push, arbitrary shell or
filesystem-writing commands. Termux setup and Python's ordinary cache files may
write to the app's own storage; the checker does not write directly to device
partitions. It never installs iOS. Upstream's separate root flash erases Android
`userdata`; unlocking may erase data. Even a `supported` result does not make
either operation safe.

## Exact operations

- In adb mode: `adb devices`, then, for one selected authorized Android device,
  `adb -s <local-serial> shell getprop <allowlisted-property>`. The 13 keys are
  in [`devicecheck/transport.py`](../devicecheck/transport.py); they cover
  codenames, product/model, reported SoC, board/hardware, 64-bit ABI, Android
  version, and boot-state properties. Each property is queried separately, not
  by collecting the full property dump. Boot-state values are unverified
  software reports, **not** an authoritative unlock or AVB assessment.
- In local mode on Android: `/system/bin/getprop <allowlisted-property>` for
  each of the same 13 keys. No adb, fastboot, USB debugging, root, full
  property dump, or serial query is used. Some vendors may restrict access or
  omit properties. Android's source describes `getprop` as reading a named
  property [here][getprop]. See the [phone setup guide](android-phone.md).
- In fastboot mode: `fastboot devices` only. Product, chipset, unlock state and
  partition data remain unknown. Upstream explicitly says **never `fastboot
  getvar`** in its phone workflow; the note gives no reason, so we do not
  speculate, and we avoid `getvar` for every device. [Source][fastboot-note].
- In auto mode: try adb first; if no matching device or adb is unavailable,
  try fastboot. An unauthorized, offline, connecting, ambiguous or non-Android
  adb device is an error, not a reason to silently select a different device.
  Unrecognized device states still count toward selection; an unparseable
  device list fails closed. Auto stops after a successful adb selection; it
  does not also probe fastboot. Auto does not select local mode; use
  `--transport local` explicitly on the phone.

The runner enforces this command allowlist before execution. Tools are invoked
directly (no host shell) with an 8-second timeout per command. An adb server
may start on the **host** and an authorization prompt
may appear on the phone. Recovery/sideload properties are rejected because they
may describe the recovery environment rather than installed Android. Read-only
commands still cannot guarantee that every vendor's software behaves correctly.

When one or more local `getprop` commands exit nonzero, the checker continues
reading the other allowlisted keys, records the failed property names, and
returns a partial **unknown** result. It cannot determine whether the cause was
permissions or something else, and it suppresses the tools' output. If all local
commands fail, the executable cannot run, or any command times out, the check
is a hard error. A successful command that returns an empty property is simply
missing, not a command failure. In adb mode any property-command failure
remains a hard error: a disconnected or unauthorized device must not yield a
partial match from earlier reads.

## Selection and privacy

For adb/fastboot, exactly one device needs no serial argument. Multiple devices
cause an error; disconnect extras or use `--serial <value>` locally. A serial is
used internally to target a device and is not printed by this tool or included
in JSON; values containing the selected adb serial are suppressed. The value can
still be visible to the host OS or in a process list. Do not put a serial in an
issue, log, test fixture or shell history you intend to publish.

On-phone local mode does not query a hardware serial and rejects `--serial`.
Because it does not know the serial, it **cannot recognize or redact one** if a
custom property happens to contain it. Raw tool diagnostics are suppressed in
all modes.

The checker compares the actual values in memory but hides them in its default
text and JSON reports. `[hidden]` means a valid property value was present;
`unknown` in text or `null` in JSON means missing, invalid or failed. Opt in to
view the values locally with `--show-properties` (including with `--json`).
Selected adb serials and values containing them are still suppressed, and
malformed/invalid values remain unknown. Do not share unreviewed output when
values are shown.

Hiding values is **not an anonymity guarantee**: property availability,
comparison results, profile details, error messages and custom profile data can
still identify a person or device. Review and redact every report before
sharing; never publish serials, IMEIs, private logs or firmware.

## Matching rules

Matching is literal and case-insensitive; no board aliases are guessed. The
text label **reference identity match** and the JSON status `supported` have the
same identity-only meaning; `supported` is retained for existing JSON clients.
For `sweet`, **all** of the following Android values must equal the corresponding
upstream identity string before that result is possible:

| Android property | Required literal |
| --- | --- |
| `ro.product.device` | `sweet` |
| `ro.build.product` | `sweet` |
| `ro.product.manufacturer` | `Xiaomi` |
| `ro.product.model` | `Redmi Note 10 Pro` |
| `ro.soc.model` | `SM7150` **or** `Snapdragon 732G` |

Upstream's [shim uses arm64][arm64]. If `ro.product.cpu.abilist64` is
available, the checker additionally expects `arm64-v8a` in that ROM's
comma-separated 64-bit ABI list. A different or unrecognized nonempty list
downgrades an otherwise positive result to `unknown`. A missing ABI does not
by itself prevent the **identity-only** result; it remains unknown. This is a
software ABI heuristic, not proof of the CPU or of boot compatibility.

The identity values are sourced from [upstream's identity description][identity], not
from an upstream transcript of those exact `getprop` fields. The mapping to
fields is a conservative comparison heuristic, not independently verified
hardware evidence. They may be ROM-dependent, absent (especially
`ro.soc.model`), modified, or spoofed, and the two codename fields may share a
common software origin. The Indian/global scope mentioned upstream does not
justify inventing an additional codename or model alias. Missing, malformed,
unrecognized, or conflicting required identity values yield **unknown**, not a
guessed match. Any nonzero local property read also forces a partial **unknown**
result, even if the other identity strings appear to match.

Without `--profile`, an unmatched codename is **unknown** even if the chipset
looks similar. With `--profile sweet`, **incompatible** means the two codename
fields agree on a different value: only a mismatch with that *selected
profile*, not a judgment about whether future engineering could port the phone.
A `research_only` profile can never yield `supported`. The schema's source
links and labels require human review; the program cannot validate the truth
of an evidence URL or a claimed hardware test. See [profile rules](../profiles/README.md).

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | `supported`: reference identity match only |
| 1 | `unknown`: not enough evidence, a partial local read, or fastboot enumeration only |
| 2 | `incompatible`: mismatch with explicitly selected profile; argparse usage errors also use 2 |
| 3 | tool, device-selection, connection or profile error |

For device checks, `--json` emits one JSON object with the existing `status`,
`properties`, checks and unknowns, plus `result_label`, `properties_hidden` and
`failed_properties`. By default each present value in `properties` is the string
`[hidden]`; missing/invalid/failed values are `null`. **Migration:** scripts
that previously consumed property values must explicitly opt in with
`--show-properties`. Status strings and their exit-code meanings have not
changed, but a partial local read now returns `unknown`/1 instead of an error/3.
Tool, device and profile errors have `status: "error"` and an error message rather
than a comparison report. Argument-parser usage errors still produce ordinary
argparse text on stderr and exit 2, even with `--json`; `--help` produces text.
Do not interpret a zero exit status as permission to flash. If tools are
missing, install Platform Tools; if access is unauthorized, approve the
debugging prompt; if offline or missing, check the cable, USB permissions and
mode. The checker does not change device mode.

[fastboot-note]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/NOTES.md#L39-L46
[identity]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L1-L9
[arm64]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/shim/start.S#L1-L4
[getprop]: https://github.com/aosp-mirror/platform_system_core/blob/a3b721a32242006b59cb12bd62c9133632af3a2d/toolbox/getprop.cpp#L74-L78
