# taktone extensions — TT2B

Scenes and secondary-CPU Sophie machines for the original Digitone 1 running the Digitakt 1 crossport. This package builds the complete TT2B firmware from stock inputs, including the core panel/audio/autosave adaptation. It does not require a core checkout or a prebuilt scenes firmware file.


SYN2 is unassigned. All four scenes start enabled on new or cleared patterns; saved enabled states are preserved.

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

`patch.py` verifies the stock inputs, reconstructs the application using bundled `internal/patch-data.json`, and verifies both firmware envelopes against the exact release hashes before writing them. Unchanged firmware bytes, including the secondary loader and FPGA-containing secondary image, are copied from the user's stock inputs. The patch data stores source-copy references and compressed replacement bytes, not complete firmware files. Inputs are read directly without making local copies.


Outputs go to `firmware/`, or to `--out output`, with a SHA-256 build report. Run without Python `-O`.

| Output | Receiver |
| --- | --- |
| `TT2B.syx` | Already running XDT firmware, including Elektron Transfer over USB |
| `TT2B-recovery.syx` | Digitone startup recovery receiver over physical MIDI IN |

Both contain the same application and preserve all stock Digitone non-main container sections. The customized secondary program is uploaded by main at runtime. Back up before installation; stock Digitone project conversion/preservation is not established, and sample-volume formatting can erase data.

## Output verification

The patcher verifies stock input hashes, container round trips, the reconstructed application hash and both output containers. Both generated files must match these SHA-256 hashes before either is written to `firmware/`.

| Output | SHA-256 |
| --- | --- |
| `TT2B.syx` | `dddf87caee6ecb20ab0e481a53d1e824d253a9d8ba9518affc7a190ba75d35a8` |
| `TT2B-recovery.syx` | `3e67a80898a879e5a71474e25d384d721d95d3fec3296a8f91fda1fef9b4e1b7` |

Hardware testing of this release has not been performed.

## Use and develop

- [Scene controls](docs/SCENES.md)
- [Sophie controls and diagnostics](docs/SOPHIE.md)
- [Secondary CPU and Sophie integration](docs/SECONDARY-CPU.md)
- [Building new machines](docs/MACHINE-DEVELOPMENT.md)
- [Extension architecture, protocol and memory](docs/DEVELOPMENT.md)
- [Acknowledgements and licenses](../README.md#acknowledgements)

The core package documents the panel/audio/autosave crossport. This package contains the complete working source for extending scenes and machine integration. `patch.py` is the supported entry point; internal build scripts live in `internal/`.

## Rebuild modified source

Normal users run `patch.py`. Developers modifying the firmware implementation can use `internal/build_from_source.py` using the same `firmware/` folder, then regenerate `internal/patch-data.json` with `internal/export_patch.py`. See [developer build instructions](docs/BUILDING.md).

Build tools, patch data and supporting source live in `internal/`. Stock inputs and generated firmware stay in `firmware/`.
