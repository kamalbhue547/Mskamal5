# Device profiles

Profiles are small **evidence indexes**, not drivers, images, compatibility
certificates or installation instructions. The loader validates the schema and
requires HTTPS evidence, but **cannot verify that a source is true**. Human
review and device-specific engineering/testing remain necessary.

## `sweet`: documented upstream reference

[`sweet.json`](sweet.json) records only identity labels stated by the pinned
upstream: Xiaomi Redmi Note 10 Pro, `sweet`, Qualcomm SM7150 / Snapdragon 732G.
Upstream describes global or Indian sweet and warns firmware/variants may need
changes; the profile does not invent an extra Indian codename or claim all
variants were tested. [Identity][identity], [scope][scope].

Other **upstream-reported** hardware assumptions (not auto-detected by the
checker): upper RAM bank at `0x100000000` + `0xfcc00000`, GICv3 virtual timer
INTID 19, UFS storage, ABL framebuffer 1080×2400 at `0x9c000000`, Goodix
GT9896 over I²C, and PMIC/SPMI buttons. These are board-specific observations,
not portable constants. [Hardware notes][hardware], [ADT source][adt].
See [architecture](../docs/architecture.md) for the root and actual drivers.

The upstream strings are **not** a transcript of our chosen Android properties.
The checker strictly compares those five property fields to the strings; an
identity match is not proof of actual hardware or safety. An unavailable
`ro.soc.model` is expected on some ROMs and produces `unknown`.

## Schema version 1

- A profile lives in one `profiles/<id>.json`; lowercase `id` must match the
  filename. `schema_version` is integer `1`, `name` is a display name.
- `support_level` is `research_only`, `upstream_reference`, or
  `hardware_verified`. `research_only` **never** produces `supported`.
- `identity` contains `codename`, `manufacturer`, `model`, and `soc_labels`.
  In `research_only`, unknown string values can be `null` and `soc_labels`
  can be `[]`. For a reviewed supported reference, all are required and
  `soc_labels` must contain at least one explicitly sourced label.
- Optional `platform.cpu_arch` records a sourced architecture. For `arm64`,
  the checker treats a nonempty Android 64-bit ABI list without `arm64-v8a`
  as a reason for `unknown`. Other architecture labels have no ABI comparison
  implemented; an Android ABI property is not proof of physical hardware.
- `evidence` is a non-empty list of objects with `subject`, absolute HTTPS
  `url`, and `note`. Cite an immutable revision/document and explain exactly
  which fact it supports. The program only validates the URL's shape, not the
  evidence itself. Additional board facts belong in a sourced research note.

Start with [`template.json.example`](template.json.example). It is deliberately
not loaded and deliberately has no evidence; replace placeholders and add a
real citation before creating a `.json` file. Do **not** invent missing facts.
A proposed promotion from `research_only` needs a reviewable original upstream
reference port or actual device-specific hardware testing and supporting code,
firmware/build identifiers, dates, limitations and a safe recovery plan. A
config file alone is never sufficient. See [CONTRIBUTING](../CONTRIBUTING.md).

[identity]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L1-L9
[scope]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L48-L56
[hardware]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/README.md#L190-L199
[adt]: https://github.com/dipa-studio/ios-sweet/blob/45263bee51df4a0f55cdf9c649af886399488ddb/tools/mkadt.py#L12-L37
