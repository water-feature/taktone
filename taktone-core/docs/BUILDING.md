# Developer source build

`patch.py` is the end-user patcher and requires Python alone. It reconstructs a pinned release from `internal/patch-data.json`, verifies source and final application hashes, packages both receiver envelopes and checks exact release hashes before writing outputs.

Put the stock `Digitakt_OS1.53.syx` and `Digitone_and_Digitone_Keys_OS1.43.syx` files in this repository's `firmware/` folder. To change the firmware, edit the included patch/assembly/C sources and run from the repository's directory:

```sh
python3 internal/build_from_source.py
```

Outputs are written to this repository’s `firmware/` folder.

The core source builder also uses only Python; it emits the small crossport stubs directly.

Update `internal/release.json` with the source build’s version and output hashes, then export the patch recipe from the recovery candidate:

```sh
python3 internal/export_patch.py --digitakt firmware/Digitakt_OS1.53.syx \
  --digitone firmware/Digitone_and_Digitone_Keys_OS1.43.syx \
  --candidate firmware/TT1A-recovery.syx
```

The exporter round-trips the recipe against the candidate image. Run `patch.py` to confirm both output hashes match. Audit and qualify changed firmware before assigning it release status. Modifying a recipe without updating its pinned image/output hashes is rejected.

A recipe consists of copies from hashed stock sections and zlib-compressed replacement runs. The embedded secondary loader and stock portions of the secondary program are copied from the user's Digitone sections 6 and 7. The published source package excludes firmware inputs, compiled candidates and intermediate files. Keep user-supplied stock inputs in `firmware/` locally.
