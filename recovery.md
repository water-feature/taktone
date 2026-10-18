# Firmware installation and recovery

This guide covers the original Digitone running taktone core or extended. Back up projects and sounds before changing firmware. Digitone and Digitakt projects are not converted into one another.

## Restore stock Digitone firmware

Use the [startup upgrade procedure below](#install-or-recover-taktone-through-the-startup-menu), selecting the **original stock Digitone OS `.syx`** instead of a taktone recovery file. No separate factory recovery file is needed.

Send it through **DIN MIDI and the startup OS UPGRADE receiver**. The updater inside running taktone expects Digitakt addressing, so sending stock Digitone firmware to it over USB is not the restoration procedure.

Formatting the +Drive is not a prerequisite for receiving or validating a firmware update. Restoring the OS does not convert taktone projects into Digitone projects or restore data erased by formatting.

## Why taktone generates two SysEx files

The Digitone startup upgrade receiver and the running taktone updater expect different SysEx addressing:

| Receiver | Expected addressing | File to send |
| --- | --- | --- |
| Digitone startup **OS UPGRADE** menu | Digitone | Taktone file ending in `-recovery.syx`, or original stock Digitone OS `.syx` |
| Updater in running taktone | Digitakt | Regular taktone `.syx` without `-recovery` |

Taktone runs a Digitakt application on Digitone hardware. Its running updater therefore expects Digitakt-addressed messages, while the startup receiver retains Digitone addressing. The two generated files install the same firmware; their outer SysEx framing and transport checksums differ to match the receiver. The recovery file does not install a reduced or different edition of taktone.

Stock Digitone uses Digitone addressing in both receivers, so Elektron supplies one stock OS file rather than a separate recovery file.

## Where to find the files

Run the appropriate patcher with its required stock inputs:

- **Core:** `taktone-core/converted/taktone-<input filename>.syx` and `taktone-<input filename>-recovery.syx`.
- **Extended:** `taktone-extended/firmware/taktone-extended-<version>.syx` and `taktone-extended-<version>-recovery.syx`, unless you selected another output directory.
- **Stock Digitone:** use the original, unmodified Digitone OS `.syx` downloaded from Elektron. The stock file used by these patchers is `Digitone_and_Digitone_Keys_OS1.43.syx`. It needs no conversion or recovery suffix.

## Install or recover taktone through the startup menu

1. With the instrument off, hold **FUNC** while powering on to open the startup menu.
2. Press **TRIG 4** to enter **OS UPGRADE**.
3. Connect a physical MIDI interface's **MIDI OUT** to the Digitone's **MIDI IN**.
4. In Elektron Transfer, open **SYSEX TRANSFER**, then **OS upgrade via device startup menu**. Select the physical MIDI interface as directed.
5. Select the generated taktone **`-recovery.syx`** file and follow the transfer and instrument prompts. Let the upgrade finish before switching off.

**Startup upgrading requires DIN MIDI. The Digitone's USB port cannot receive the OS in this mode.** A USB-to-DIN MIDI interface connected to the computer is suitable; the connection into the instrument must be DIN MIDI.

After your first switch from stock Digitone to taktone, follow the +Drive formatting instructions in the [core](taktone-core/README.md#first-installation-format-the-drive) or [extended](taktone-extended/README.md#first-installation-format-the-drive) guide before recording or transferring samples. Formatting erases the selected data. Routine updates to an already working taktone installation do not require another format.

## Update an instrument already running taktone

Use the regular generated **`.syx` without `-recovery`** with the running taktone updater, including through Elektron Transfer over USB. This also applies when switching between core and extended. If the application cannot boot, use the startup procedure above with the recovery file instead.

## If you see a checksum error

First check that the file matches the receiver in the table above. A receiver mismatch is one possible explanation; the message alone does not establish the cause.

If the error persists in the startup receiver with the correct file, record the exact message, OS filename, MIDI interface and whether the failure occurs during reception or after the transfer completes. Re-download an unmodified stock file from Elektron, or check a generated taktone file against its build report. Do not format the drive or perform a factory reset to troubleshoot a firmware checksum error.

See Elektron's [SysEx upgrade instructions](https://support.elektron.se/support/solutions/articles/43000662701-how-to-update-your-device-via-sysex-transfer) and the [Digitone user manual, Startup Menu](https://www.elektron.se/wp-content/uploads/2024/09/Digitone_User_Manual_ENG_OS1.41_231108.pdf).
