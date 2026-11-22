# Browser verification — 2026-11-23

Validated locally with Chromium 144 and the self-hosted Pyodide 0.27.7 / CPython 3.12.7 runtime. These are software checks; no instrument was connected or flashed.

- All 28 existing core unit tests passed.
- End-to-end browser conversions of stock Digitakt 1.53 and 1.54 each produced both receiver envelopes with SHA-256 values matching fresh desktop conversions.
- An existing Modwerk Digichain 1.53-based input also produced both envelopes matching fresh desktop conversions, including core relocation/startup adaptation. This covers one actual modified input; it does not establish support for every mod.
- The files saved through the browser's download mechanism were checked, not only in-memory outputs. Each success also produced a conversion report.
- Browser conversion took 39 seconds for stock 1.53 and 31 seconds each for stock 1.54 and the modified case in this run. These timings are machine-dependent.
- Wrong Digitone stock identity was rejected at selection. A mismatched Digitakt base passed to the real converter was rejected with no downloads.
- A corrupted source archive was rejected before conversion.
- Cancel restored controls and left no downloads. Changing inputs cleared previous downloads.
- At a 375px viewport, expanded modified-firmware options produced no horizontal overflow. Desktop and mobile screenshots were inspected.
- No page errors, off-site requests or non-GET requests were observed during the browser suite. Downloaded firmware was never sent to a server.
- Two successive site builds produced identical source archive hashes. The source archive and staged site contained no firmware, compiled candidates or emulator snapshots. Runtime files matched the committed SHA-256 pins; component notices were present.
- JavaScript syntax checks, Python compilation and `git diff --check` passed.

Reproduction commands and test dependency setup are in [README.md](README.md). The optional modified-input check uses a local user-supplied file. Inputs, outputs and browser test artifacts are not committed. Firefox, Safari, GitHub Pages deployment and physical hardware were not tested in this change.
