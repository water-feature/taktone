# taktone extended — TT2D

Scenes and secondary-CPU Sophie machines for the original Digitone 1 running the Digitakt 1 crossport. This package builds the complete TT2D firmware from stock inputs, including the core panel/audio/autosave adaptation. It does not require a core checkout or a prebuilt scenes firmware file.

SYN2 is unassigned. All four scenes default to enabled, including untouched empty scenes in existing projects. Learned scenes retain their saved enabled state. Hold a scene and press A–H to clear that parameter’s scene lock.

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

These packages target the original Digitone. The stock download has Keys in its filename; Digitone Keys is untested. Digitone II is not a build target.

`patch.py` verifies the stock inputs, reconstructs the application using bundled `internal/patch-data.json`, and verifies both firmware envelopes against the exact release hashes before writing them. Unchanged firmware bytes, including the secondary loader and FPGA-containing secondary image, are copied from the user's stock inputs. The patch data stores source-copy references and compressed replacement bytes, not complete firmware files. Inputs are read directly without making local copies.


Outputs go to `firmware/`, or to `--out output`, with a SHA-256 build report. Run without Python `-O`.

| Output | Receiver |
| --- | --- |
| `TT2D.syx` | Already running XDT firmware, including Elektron Transfer over USB |
| `TT2D-recovery.syx` | Digitone startup recovery receiver over physical MIDI IN |

Both contain the same application and preserve all stock Digitone non-main container sections. The customized secondary program is uploaded by main at runtime. Back up before installation; stock Digitone project conversion/preservation is not established, and sample-volume formatting can erase data.

## Output verification

The patcher verifies stock input hashes, container round trips, the reconstructed application hash and both output containers. Both generated files must match these SHA-256 hashes before either is written to `firmware/`.

| Output | SHA-256 |
| --- | --- |
| `TT2D.syx` | `67a81cddb68751c4fc489b2523258a3db16a1a10e3dd2debeeed4ca88f47bf27` |
| `TT2D-recovery.syx` | `e74cc3d2a1b75dd1de06790b329fd39ddb9d88edb0aa16ee69bd0d9762df7ce9` |

Project author confirmed scene initialization and scene-held encoder-push lock clearing on hardware.

## Physical controls

The panel uses Digitakt actions on the Digitone’s printed buttons:

| Digitone control | TT2D action |
| --- | --- |
| MIDI | TRK / track selection |
| SYN1 | SRC / source page |
| VOICE | SAMPLE / recording screen |
| SYN2 | Unassigned |
| FLTR, AMP, LFO | Corresponding parameter pages |
| T1–T4 | Hold scenes 1–4; FUNC+T toggles enabled state |
| NOTE/KEYBOARD | Unassigned |

Sophie knob D is unassigned. Encoder pushes A–H clear the corresponding scene lock while a scene is held on SRC, FLTR, AMP or LFO. See the [scene guide](docs/SCENES.md) for learning, copying and clearing scenes.

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
