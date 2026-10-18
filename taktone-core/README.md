# taktone patcher

Run Digitakt firmware on an original Digitone. The patcher supports Digitakt OS 1.53 and 1.54, including mods made with Modwerk or elekloader.

It keeps the supplied firmware's mods and boot version, and adapts the buttons, LEDs, audio and shutdown saving for Digitone hardware. It detects the underlying OS version even when a mod has its own version label.

These packages target the original Digitone. Digitone Keys is untested. Digitone II is not a build target.

Before starting read [recovery.md](../recovery.md), prepare firmware files and backup your machine data as everything will be erased. Ensure you have a midi cable and a midi interface for restoring the original DN firmware.

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

The patcher converts one firmware file at a time. If you added one modified firmware to `firmware/`, it selects that file automatically. If there are several modified files, it displays a numbered list in the terminal: enter the number of the file you want to convert. 

The finished files are saved in `converted/`.

## Choose the output file

| File | When to use it |
| --- | --- |
| `taktone-<input filename>-recovery.syx` | First installation from running stock Digitone through Transfer over USB, or startup upgrade over DIN MIDI |
| `taktone-<input filename>.syx` | Updating a Digitone already running taktone, including through Elektron Transfer over USB |
| `conversion-report.json` | Checking whether conversion succeeded or why it was refused |

Both SysEx files install the same firmware. The output name uses your input filename without its `.syx` extension. The firmware keeps its boot version: an input labelled `1.54` or `2.0a` keeps that label. The `-recovery` suffix identifies Digitone addressing; DIN MIDI is required only when using the startup menu.

## First installation: format the +Drive

**After first switching from stock Digitone firmware to taktone, format the +Drive before recording or transferring samples. Formatting erases the selected data; back up anything you want to keep before installing.**

1. Boot into taktone after flashing.
2. Open **SETTINGS > SYSTEM > FORMAT +DRIVE**.
3. Select **PROJECTS+SOUNDS** and **SAMPLES**, then choose **ERASE SELECTED DATA** and confirm.
4. Wait for formatting to finish before recording or transferring samples.

This creates the sample filesystem taktone needs. Reaching the main screen does not mean sample storage is ready; skipping this step can leave recording saves and sample transfers unable to write to the drive.

This is a first-installation step when switching from stock Digitone. Routine updates to an already working taktone installation, including switching between core and extended, do not require another format.

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
