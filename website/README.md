# Browser core patcher

The browser page follows [PX-RE](https://water-feature.github.io/PX-RE/): plain HTML, native controls, local firmware processing and explicit downloads after verification. It converts stock or compatible modified Digitakt 1.53/1.54 inputs using the **current core patcher**. It does not build the archived `--release` recipe or the extended package.

## Build and preview

From the repository root:

```sh
python3 tools/build_website.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory dist
```

Open `http://127.0.0.1:8765`. A first build downloads about 14 MB of pinned Pyodide 0.27.7 runtime assets into `.cache/pyodide-0.27.7/`; subsequent builds use the hash-checked cache. All served runtime assets and Python sources are local to `dist/`. The site makes no CDN requests. HTTPS or localhost is required for Web Crypto; opening `index.html` directly as a file is unsupported.

`dist/` and the runtime cache are ignored. Never place firmware in `website/` or `dist/`. The builder selects Python sources, recipe JSON and license/notice files from `taktone-core/internal/`; it does not copy firmware directories, generated candidates, emulator data or reports other than the required measured panel map.

`.github/workflows/pages.yml` builds the static artifact and deploys it to GitHub Pages on relevant pushes to `main`, or manual dispatch. Configure repository **Settings → Pages → Source → GitHub Actions** before deploying. The workflow needs no stock firmware or secrets. Local work is not deployed until committed and pushed.

## Execution and verification

`ui.js` checks original stock file hashes. Three separate pickers accept modified Digitakt firmware, original Digitone OS, and factory Digitakt OS. The modified input is optional: leaving it empty converts the selected factory Digitakt OS. No RAM-map upload is shown. It starts a fresh worker for each build. `worker.js` loads the self-hosted Python/WebAssembly runtime, checks the bundled source archive against `source-manifest.json`, and creates a disposable RAM filesystem. Firmware is passed to the worker in memory; filenames are data, never executable code.

`browser_bridge.py` invokes the existing `convert.main()` with explicit input/reference/output arguments. The bundled Python source is the current repository source; there is no independent JavaScript implementation of firmware rules. Assertions remain enabled. The converter retains base fingerprinting, source/recipe equivalence, loader recognition, conflict detection, RAM placement, instruction audits, stock round trips and verification of both output envelopes. The source archive includes the historical recipe because stock 1.53 conversion also checks its archived release hashes.

Both outputs must pass the converter before the worker returns any bytes. The UI verifies the returned output length/hash before exposing download links. Conversion errors expose no firmware downloads. Downloads include both receiver envelopes and the core conversion report. A new selection revokes prior download URLs. Cancel terminates the worker, releases its RAM filesystem and restores the form. Each retry starts cleanly.

The output version label is preserved from the input, as in the Python patcher. Filenames retain ASCII letters, digits, dots, underscores and hyphens (up to 160 characters); other characters are removed by the browser bridge. Firmware contents are unaffected by filename normalization.

The CSP allows scripts, worker and runtime downloads only from this site, plus WebAssembly compilation. Source archive hashes detect stale/corrupt staging, not a compromised hosting origin. Runtime asset hashes are pinned and checked during the site build. No analytics, accounts, uploads, MIDI transmission or device installation are implemented.

## Checks

The usual core tests require the user-supplied stock firmware in `taktone-core/firmware/`:

```sh
python3 -m unittest discover -s taktone-core/internal -p 'test_*.py'
```

For the browser checks, install the optional development dependency and a Chromium browser:

```sh
npm ci --prefix tools
cd tools
npx playwright install chromium
cd ..
node tools/test_browser.cjs
```

Run the local HTTP server first. `PATCHER_URL` overrides its default URL. `CHROMIUM_PATH` selects an existing browser executable; `PYTHON` overrides the desktop Python command. Optional `MOD_FILE=/absolute/path/to/a/1.53-based-mod.syx` adds an end-to-end modified-firmware case.

The test builds desktop references in a temporary directory and compares both downloaded browser outputs by SHA-256. It also checks wrong stock references, cancellation, rejection of invalid factory firmware, source ZIP corruption, clearing stale downloads, mobile overflow and requests staying on the site with GET only. Browser and desktop checks do not establish instrument compatibility or physical audio/storage reliability.

The recorded local results are in [VERIFICATION.md](VERIFICATION.md).

## Credits

Layout and style follow PX-RE; its MIT license and notice are retained as `PX-RE-LICENSE` and `PX-RE-NOTICE`. The converter and bundled upstream code retain their original component licenses. The site ships Pyodide's license and the CPython 3.12.7 license alongside its runtime. No Elektron firmware is included in the source or deployed site.
