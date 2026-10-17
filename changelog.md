# Changelog

TT1 versions identify the core firmware; TT2 versions identify the extensions firmware. Firmware binaries are built locally from user-supplied stock files.

## Taktone patcher — 2026-10-18

- Replace the core end-user workflow with one patcher for stock or compatible modified Digitakt 1.53 and 1.54 inputs; retain the historical TT1A build under `patch.py --release`.
- Detect supported bases from exact stock metadata and native application fingerprints, independently of a mod's display label.
- Add the reviewed 1.54 address profile and pinned recipe; preserve supplied boot versions and native firmware outside core patch regions.
- Leave SYN2 unassigned in both current OS profiles; retain VOICE as SAMPLE/recording access. The archived TT1A release keeps its original mapping.
- Recognize the observed Modwerk/elekloader startup template, preserve mod payloads, relocate core when needed, and chain startup initialization.
- Retain container, decompression, flash-bound and ColdFire checks; report conflicts and unsupported bases.

The user reported four supplied 1.53-based modified builds working on hardware. The 1.54 profile passed source/recipe, container and synthetic loader checks; no independently produced 1.54 mod, 1.54 hardware or Outbox qualification is claimed.

## TT2D — 2026-10-17

- Route scene-held encoder presses through the focused parameter page’s native key handler, instead of using a widget cached during drawing.
- Cover the SRC page’s own handler as well as the shared parameter-page handler, so page-specific processing cannot consume the press first.
- Add native UI replay checks for all eight encoders on SRC, FLTR, AMP and LFO, with the cached grid deliberately unavailable.

Native UI replay passed all 32 encoder presses across SRC, FLTR, AMP and LFO. Project author confirmed scene initialization and encoder-push lock clearing on hardware. Published source includes updated patch data and output hashes.

## TT2C — Local hardware test

- Enable untouched empty scenes when loading existing projects, including rows omitted from sparse scene storage.
- Retain explicit scene toggles and clears across loading, while preserving saved enabled states for learned scenes.
- Attempt to correct scene-held encoder-push clearing using the drawn grid and direct lock removal.

Hardware testing confirmed scene initialization. Lock clearing worked on the sample page but failed on filter, amp and LFO. Not published to GitHub.

## TT2B — 2026-10-17

- Disable SYN2’s SAMPLE/recording-screen action. VOICE retains SAMPLE access.
- Enable all four scenes by default on new and cleared patterns.
- Rebuild both firmware envelopes and update patch data, release hashes and documentation.

Published to GitHub in commit `8e225dd`. Existing saved empty scenes could still load disabled; addressed in TT2C.

## TT2A — 2026-10-17

- Initial taktone extended publication: the core crossport plus four scenes per pattern and eight-track Sophie synthesis on the secondary ColdFire CPU.
- Provide scene learning, enabled-state toggles, copy/paste/clear and instrument-local scene persistence.
- Expose seven Sophie synthesis controls; knob D and NOTE/KEYBOARD are unassigned.
- Use `TT2A` as the four-character firmware version label.

Published with TT1A in commit `465e572`.

## TT1A — 2026-10-17

- Initial taktone core publication: Digitakt 1.53 firmware adapted for original Digitone hardware.
- Include button and LED translation, codec initialization, external audio I/O and shutdown autosave.
- Leave the secondary ColdFire idle. NOTE/KEYBOARD and T1–T4 are unassigned.
- Use `TT1A` as the four-character firmware version label.

Published with TT2A in commit `465e572`.
