# taktone patcher

Run Digitakt firmware on an original Digitone. The patcher supports **stock Digitakt OS 1.53 and 1.54**, plus compatible modified firmware. The same patcher handles supported inputs, including mods made with Modwerk or elekloader.

It keeps the supplied firmware's mods and boot version, and adapts the buttons, LEDs, audio and shutdown saving for Digitone hardware. It detects the underlying OS version even when a mod has its own version label.

This is for the original Digitone. Digitone II is not supported; Digitone Keys has not been tested.

## What you need

Install Python 3.12 or later. Put these original, unmodified files in the `firmware/` folder:

- `Digitone_and_Digitone_Keys_OS1.43.syx`
- `Digitakt_OS1.53.syx` or `Digitakt_OS1.54.syx`, matching the firmware you want to convert. You can keep both there.

Put the stock or modified Digitakt firmware you want to convert in that same `firmware/` folder. Keep the required original files there too.

## Run the patcher

From the `taktone-core` folder, run:

```sh
python3 patch.py
```

The patcher converts one firmware file at a time. If you added one modified firmware to `firmware/`, it selects that file automatically. If there are several modified files, it displays a numbered list in the terminal: enter the number of the file you want to convert. If there are no modified files, it uses the available stock Digitakt firmware, or offers the same numbered choice when both 1.53 and 1.54 are present.

The finished files are saved in `converted/`.

## Choose the output file

| File | When to use it |
| --- | --- |
| `taktone-<input filename>-recovery.syx` | Installing from stock Digitone firmware through the startup recovery menu, using DIN MIDI IN |
| `taktone-<input filename>.syx` | Updating a Digitone already running taktone, including through Elektron Transfer over USB |
| `conversion-report.json` | Checking whether conversion succeeded or why it was refused |

Both SysEx files install the same firmware. The output name uses your input filename without its `.syx` extension. The firmware keeps its boot version: an input labelled `1.54` or `2.0a` keeps that label.

Back up your instrument first. Setting up Digitakt sample storage may require formatting the drive, which erases its contents. Existing Digitone projects are not converted into Digitakt projects.

## Controls

| Digitone button | Action |
| --- | --- |
| MIDI | TRK |
| SYN1 | SRC |
| VOICE | SAMPLE/recording screen |
| SYN2, NOTE/KEYBOARD, T1–T4 | Unassigned |

Shared transport, menu, trig and encoder controls retain their corresponding actions. A supplied mod may add its own button behavior.

## Compatibility

The patcher checks the input and stops when it finds an unsupported firmware layout or a conflict with the Digitone adaptations. It cannot convert every mod, and a successful conversion does not guarantee that every feature will work on hardware.

The supplied 1.53-based mods have run successfully on hardware. The 1.54 builds still need hardware testing, including Outbox operation. The separate taktone-extended package, which adds scenes and Sophie, remains based on 1.53.

[Using your converted firmware](converted/README.md) · [Developer build guide](docs/BUILDING.md) · [Technical details](docs/ARCHITECTURE.md) · [Acknowledgements and licenses](../README.md#acknowledgements)
