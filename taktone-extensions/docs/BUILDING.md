# Developer source build

`patch.py` is the end-user patcher and requires Python alone. It reconstructs a pinned release from `internal/patch-data.json`, verifies source and final application hashes, packages both receiver envelopes and checks exact release hashes before writing outputs.

Put the stock `Digitakt_OS1.53.syx` and `Digitone_and_Digitone_Keys_OS1.43.syx` files in this repository's `firmware/` folder. To change the firmware, edit the included patch/assembly/C sources and run from the repository's directory:

```sh
python3 internal/build_from_source.py
```

Outputs are written to this repository’s `firmware/` folder.

The extension source build uses Ghidra 12.1.4 with Java 21 for scene assembly, plus GNU `m68k-elf-gcc`, `m68k-elf-as`, `m68k-elf-ld`, `m68k-elf-objcopy` and `m68k-elf-nm` for Sophie and driver source. Set `GHIDRA_HOME` to the installation directory (or `GHIDRA_HEADLESS` to its launcher), configure `JAVA_HOME` as needed, and put the ColdFire tools on PATH. The source builder creates its own local Ghidra project. These tools are developer dependencies only.

Update `internal/release.json` with the source build’s version and output hashes, then export the patch recipe from the recovery candidate:

```sh
python3 internal/export_patch.py --digitakt firmware/Digitakt_OS1.53.syx \
  --digitone firmware/Digitone_and_Digitone_Keys_OS1.43.syx \
  --candidate firmware/TT2A-recovery.syx
```

The exporter round-trips the recipe against the candidate image. Run `patch.py` to confirm both output hashes match. Audit and qualify changed firmware before assigning it release status. Modifying a recipe without updating its pinned image/output hashes is rejected.

A recipe consists of copies from hashed stock sections and zlib-compressed replacement runs. The embedded secondary loader and stock portions of the secondary program are copied from the user's Digitone sections 6 and 7. The published source package excludes firmware inputs, compiled candidates and intermediate files. Keep user-supplied stock inputs in `firmware/` locally.
