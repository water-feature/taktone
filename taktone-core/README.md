# taktone core — TT1A

taktone runs the Digitakt mk1 OS on original Digitone mk1 hardware. TT1A supplies the core crossport: button and LED translation, Digitone codec initialization, external audio I/O and shutdown autosave. The second ColdFire is idle in this build. The extensions package documents [secondary CPU and Sophie integration](../taktone-extensions/docs/SECONDARY-CPU.md).

NOTE/KEYBOARD and T1–T4 are unassigned.

## Build

Requires **Python 3.12 or later only**, using its standard library.
Place your two stock firmware files in this repository's `firmware/` folder, using these exact filenames:

```text
firmware/
  Digitakt_OS1.53.syx
  Digitone_and_Digitone_Keys_OS1.43.syx
```

Then run from this repository's directory:

```sh
python3 patch.py
```

Use the exact stock SysEx files below. The patcher checks both complete-file SHA-256 hashes before building.

| Input | SHA-256 |
| --- | --- |
| Digitakt OS 1.53 | `9bdd44bb6102fb25c143cfab97bc92b7a89c463f795d3112dce89771e29bcc92` |
| Digitone / Digitone Keys OS 1.43 | `c5a54cc05b921f2e4bd814834c5365c2a5aa01d7772a9a2961fac1c3095bf9aa` |

The stock Digitone download has Keys in its filename; Digitone Keys is untested.

The patcher reads the stock inputs directly, applies bundled `internal/patch-data.json`, and writes both verified SysEx files plus `build-report.json` to `firmware/`. Use `--out output` to choose another directory. The patch data contains references to stock bytes and compressed replacement bytes; it does not include complete firmware. Both generated files must match the release hashes before either is written. Run Python without `-O`.

| Output | Receiver |
| --- | --- |
| `TT1A.syx` | Running XDT application: Digitakt-addressed update, including USB via Elektron Transfer |
| `TT1A-recovery.syx` | Digitone startup recovery receiver: physical DIN MIDI IN |

Both files contain the same firmware container. Startup recovery also provides the Digitone-addressed route from stock hardware; the running-XDT envelope is for an already installed crossport. Back up the instrument before installation; initializing Digitakt sample storage can require FORMAT +DRIVE and erase existing data. Existing Digitone projects are not a documented conversion path.

NOTE/KEYBOARD and T1–T4 have no assigned action in the core build. NOTE/KEYBOARD is available for future features.

## Output verification

The patcher verifies stock input hashes, container round trips, the reconstructed application hash and both output containers. Both generated files must match these SHA-256 hashes before either is written to `firmware/`.

| Output | SHA-256 |
| --- | --- |
| `TT1A.syx` | `4b9d0370c10a9f9ab14423a8a3f6990984f394c155958695a8bd0c59f7567c26` |
| `TT1A-recovery.syx` | `09f8a92efb2e350540e08a2f022a72ffbbf1a1f5f378faa76987461714fb5e4d` |


## Develop

- [Architecture and core adaptations](docs/ARCHITECTURE.md)
- [Acknowledgements and licenses](../README.md#acknowledgements)

`patch.py` is the supported build entry point. The small patch modules form a layered implementation; their filenames are implementation details. The separate extensions package adds scenes and Sophie and contains the complete working custom-engine integration.

## Rebuild modified source

Normal users run `patch.py`. Developers modifying the firmware implementation can use `internal/build_from_source.py` using the same `firmware/` folder, then regenerate `internal/patch-data.json` with `internal/export_patch.py`. See [developer build instructions](docs/BUILDING.md).

Build tools, patch data and supporting source live in `internal/`. Stock inputs and generated firmware stay in `firmware/`.
