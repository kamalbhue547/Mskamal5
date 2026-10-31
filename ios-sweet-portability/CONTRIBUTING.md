# Contributing

Contributions are research, not a request to flash phones. The upstream sweet
root flash destroys Android `userdata`; unlocking can wipe data. Never commit
Apple firmware, generated images, partition backups, device-specific dumps,
serials, IMEIs, MAC addresses, keys, private logs, or personal information.
Read [recovery and safety](docs/safety-recovery.md) first. `.gitignore` is not a
substitute for reviewing files and Git history before publication.

## Proposing device research

1. Identify the precise device/model, region, board revision, chipset and
   firmware **only when evidenced**. Pin public vendor sources, board/device
   trees, code or other sources to immutable commits where possible. Separate
   vendor claims, source observations, hardware measurements and hypotheses;
   list contradictions and unknowns. Redact any identifying details.
2. Start a `research_only` profile using the documented schema and a real
   evidence link. Nulls and an empty SoC label list are allowed when unknown.
   Add a sourced research note covering bootloader, DT, storage, display,
   input, kernel, security and recovery. The [porting guide](docs/porting.md)
   describes the engineering gates. A profile cannot implement a port.
3. Do not add a `supported` claim on the basis of an alias, chipset similarity,
   QEMU run, source patch, bootloader acceptance or a configuration change.
   Promotion requires reviewable evidence of an actual reference/hardware port
   for the exact device, with build/firmware versions, observed test milestones,
   limitations and recovery considerations. `hardware_verified` is a human
   evidence label, not something this tool can automatically verify.
4. Add mocked tests for matching, missing/conflicting properties, unknown
   aliases, privacy and selection. Never use real serials or proprietary inputs
   in fixtures. Proposed new commands must remain read-only and justified;
   do not add `fastboot getvar` (upstream's notes prohibit it in their workflow).

## Development and tests

From the project root (Python 3.10+, no third-party Python dependencies):

```sh
python3 -m unittest discover -s tests -v
python3 -m devicecheck --help
python3 -m compileall -q devicecheck tests
```

When this project is checked out inside the parent repository,
`.github/workflows/python-package.yml` at the parent root runs the mocked tests
and flake8 from `ios-sweet-portability/` across supported Python versions. The
parent repository also provides `pytest.ini` so contributors with pytest
installed can run `python3 -m pytest` from its root; pytest is optional and not
needed for the documented unittest command. The workflow inside this project's
own `.github/workflows/` is for when the project is published as a standalone
repository. GitHub Actions does not discover that nested workflow in the parent
repository. No physical device,
Apple firmware, sudo, or network is needed to run the tests. If you run a
physical-device test separately, state exact consent, mode, non-sensitive
firmware details, commands, observed outcomes and what was *not* tested; do not
conflate mocks, emulation and hardware results.

Before submitting, inspect the changes and ensure no sensitive artifacts or
unrelated files are included:

```sh
git status --short
git diff --check
```

Respect the applicable licenses of upstream and any third-party code or
sources. If copying code, include its original copyright and license notices;
upstream's MIT license does not replace Apple or other third-party licenses.
