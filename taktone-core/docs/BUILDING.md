# Developer source build

`patch.py` is the unified end-user patcher for stock/compatible modified 1.53 and 1.54 applications and requires only Python. It detects a pinned stock base, applies that base’s recipe, adapts recognized mod loaders and verifies both receiver envelopes. `convert.py` is a compatibility alias. `patch.py --release` retains the historical exact-hash stock-1.53 TT1A release workflow.

Put the stock `Digitakt_OS1.53.syx` and `Digitone_and_Digitone_Keys_OS1.43.syx` files in this repository's `firmware/` folder. To change the firmware, edit the included patch/assembly/C sources and run from the repository's directory:

```sh
python3 internal/build_from_source.py
```

Outputs are written to this repository’s `firmware/` folder.

The core source builder also uses only Python; it emits the small crossport stubs directly.

Keep the historical `internal/release.json` and `internal/patch-data.json` unchanged. Export a reviewed current source candidate into its version-specific conversion recipe:

```sh
python3 internal/export_patch.py --digitakt firmware/Digitakt_OS1.53.syx \
  --digitone firmware/Digitone_and_Digitone_Keys_OS1.43.syx \
  --candidate firmware/TT1A-recovery.syx \
  --out internal/patch-data-1.53.json
```

The exporter round-trips the recipe against the candidate image. Run the unified patcher to validate the updated current recipe. `patch.py --release` separately confirms the immutable historical TT1A hashes; do not replace its archived recipe or release hashes with development output. Audit and qualify changed firmware before assigning it release status. Modifying a recipe without updating its pinned image/output hashes is rejected.

A recipe consists of copies from hashed stock sections and zlib-compressed replacement runs. The embedded secondary loader and stock portions of the secondary program are copied from the user's Digitone sections 6 and 7. The published source package excludes firmware inputs, compiled candidates and intermediate files. Keep user-supplied stock inputs in `firmware/` locally.


## Version profiles and conversion validation

`firmware_profiles.py` pins each complete stock file and decoded application. Source patch modules select that profile from the exact original stock application, map moved dependencies individually, and retain existing assertions on patch sites and pointer counts. `patch-data-1.53.json` and `patch-data-1.54.json` hold the current profiles, with SYN2 unassigned and VOICE retained as SAMPLE. `patch-data.json` is the immutable historical TT1A recipe used by `--release`, retaining its original SYN2 mapping. Both recipes are verified against source generation by the tests. The source build entry point above targets 1.53; its current source output is not the immutable TT1A release. Use the unified patcher for 1.54.

After a reviewed source change, build the selected stock candidate and export the corresponding recipe, explicitly choosing its output path for 1.54:

```sh
python3 internal/export_patch.py --digitakt firmware/Digitakt_OS1.54.syx \
  --digitone firmware/Digitone_and_Digitone_Keys_OS1.43.syx \
  --candidate converted/stock-1.54/taktone-Digitakt_OS1.54-recovery.syx \
  --out internal/patch-data-1.54.json
```

The unified patcher uses pinned recipes; for a source change, first produce the candidate using `shutdown_patch.make_shutdown_patch` with the exact selected stock image and the existing container writer, then audit/verify it before exporting. Exporting an old candidate does not incorporate a source edit.

With both exact stock Digitakt references and stock Digitone 1.43 in `firmware/`, run:

```sh
python3 -m unittest discover -s internal -p 'test_*.py' -v
python3 patch.py firmware/Digitakt_OS1.53.syx --out converted/stock-1.53
python3 patch.py firmware/Digitakt_OS1.54.syx --out converted/stock-1.54
```

Tests cover both source/recipe pairs, base recognition independent of display labels, wrong-reference/forged-metadata rejection, both loader variants, preservation, context conflicts, stock initialization, declared RAM placement, exhaustion and unknown template rejection. The mod tests use synthetic loader instances; these do not constitute testing an independently produced 1.54 mod.

Optional `internal/verify_adapter_startup.py INPUT.syx OUTPUT_DIRECTORY` requires a locally installed ColdFire-capable Unicorn build. It checks core/mod copies, BSS clearing, D0/A0/A1 at initializer handoff, a balanced stack and return to the original caller on both loader hardware-branch paths. It also accepts stock conversion reports. Stock initialization is replaced with RTS in emulator memory; this is not full-boot, audio, storage or Outbox qualification.


## Required stock file hashes

The patcher checks these complete-file SHA-256 hashes before using stock references:

| File | SHA-256 |
| --- | --- |
| `Digitakt_OS1.53.syx` | `9bdd44bb6102fb25c143cfab97bc92b7a89c463f795d3112dce89771e29bcc92` |
| `Digitakt_OS1.54.syx` | `f78ba80fa7b1da5fb0e1ff61ad61e9e71aafe79f4364fc49679f3651353e3cf6` |
| `Digitone_and_Digitone_Keys_OS1.43.syx` | `c5a54cc05b921f2e4bd814834c5365c2a5aa01d7772a9a2961fac1c3095bf9aa` |
