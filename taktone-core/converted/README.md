# Your converted firmware

This folder is where the taktone patcher saves firmware you convert for your Digitone.

**There is one patcher.** Give it a stock or modified Digitakt OS 1.53 or 1.54 file. The same command handles supported files, including compatible mods made with Modwerk or elekloader.

Put the firmware you want to convert and the required original files in `firmware/`. Then, from the `taktone-core` folder, run:

```sh
python3 patch.py
```

The patcher saves the finished files here in `converted/`. See the [setup instructions](../README.md) for the files you need.

## Which output to use

This folder contains two files that install the same firmware:

- **`taktone-<input filename>-recovery.syx`** — use this for first installation from running stock Digitone through Transfer over USB, confirmed working on hardware by the project author. Stock Digitone OS 1.30 or later supports this Transfer update method. Use this file for startup upgrades over DIN MIDI too.
- **`taktone-<input filename>.syx`** — use this when updating a Digitone already running taktone, including through Elektron Transfer over USB.

DIN MIDI is required for startup-menu upgrades; the `-recovery` suffix itself does not require DIN. See [firmware installation and recovery](../../recovery.md) for both installation routes and their validation status.

The input name is used without its `.syx` extension: `Digitakt_OS1.53.syx` produces `taktone-Digitakt_OS1.53.syx` and `taktone-Digitakt_OS1.53-recovery.syx`. The firmware keeps the boot version from your input file. SYN2 is unassigned; VOICE opens the SAMPLE/recording screen.

The patcher also writes `conversion-report.json`, which says whether conversion succeeded or why it was refused. If a file is unsupported or conflicts with the Digitone adaptations, the patcher stops without creating new firmware.

## After first installation

**When first switching from stock Digitone to taktone, format the +Drive before recording or transferring samples. Back up before installing: formatting erases the selected data.**

After booting into taktone, open **SETTINGS > SYSTEM > FORMAT +DRIVE**, select **PROJECTS+SOUNDS** and **SAMPLES**, then choose **ERASE SELECTED DATA** and confirm. Wait for formatting to finish. See the [first-installation instructions](../README.md#first-installation-format-the-drive).

Routine updates to an already working taktone installation do not require another format.
