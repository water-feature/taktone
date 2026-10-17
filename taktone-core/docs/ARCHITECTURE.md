# Crossport architecture

## Firmware boundary

The main processor runs Digitakt 1.53 code, loaded at `0x40000400`. The firmware container, bootstrap, updater, secondary loader, secondary image and other non-main sections come from Digitone 1.43. Only section 3 is replaced. The patcher verifies every non-main stored section against stock Digitone, checks container and packet checksums, flash bounds and safe in-place decompression, and requires byte-identical stock writer round trips.

The update receiver and the installed hardware identity are separate. A running Digitakt-based application receives Digitakt-addressed SysEx (`0x0a`, transfer type `0x05`), while Digitone startup recovery receives Digitone-addressed SysEx (`0x0d`, transfer type `0x08`). Rewrapping changes transport, retaining the Digitone hardware container.

A boot handoff alone is insufficient acceptance: the application must reach its UI, mount sample storage, operate controls and pass audio/storage checks.

## Panel

Digitakt has six key groups and Digitone seven. The patch uses a measured 56-position Digitone wire map to build forward and reverse semantic button tables. Both directions matter: native key queries, event consumption and modifier handling consult the reverse table.

| Digitone control | Digitakt action |
| --- | --- |
| MIDI | TRK |
| SYN1 | SRC |
| VOICE or SYN2 | SAMPLE |
| Shared transport, menu, trig and encoder presses | Corresponding Digitakt action |
| LEVEL push | Native code 48 |
| KEYBOARD and T1–T4 | No action in the core build |

All nine encoder rotation channels already match at the decoded event boundary. The patch leaves their rotation protocol intact. `internal/reports/panel-dn.json` supplies the measured physical key records; `internal/panel_patch.py` contains the semantic map.

LED translation happens at the outgoing UART boundary, retaining Digitakt's internal caches and LED counts. `internal/led_patch.py` translates both physical LED slot IDs and packed two-bit selectors. LEDs without a counterpart are suppressed; unused Digitone slots are cleared once. OLED tiles and palette serialization use the existing native path. A constant LED offset cannot express the mapping.

## Audio

Digitakt main retains its own renderer, mixer, native buffer addresses and SSI1/eDMA arrangement. `internal/audio_patch.py` adapts the board-facing configuration:

- SSI1 receive clock polarity follows Digitone. `0xFC0C8020` is SSI1_RCR; bit 3 selects RSCKP.
- Codec protocol selection uses the Digitone hardware-ID threshold: revision greater than 4, subject to the existing board flag and high ID bit.
- Newer-codec reset uses Digitone PF7. The output latch is cleared before output direction is enabled, then reset is released in native order.
- The older codec is programmed after SSI startup and a settling delay, following Digitone sequencing.

Retain Digitakt's SSI buffers and DMA descriptors. Digitone buffer addresses describe its software layout and must not replace them. Do not globally flip hardware flags to force a codec branch: those flags also select unrelated board initialization.

TT1A has working analog audio without starting the secondary CPU. Booting that CPU is an independent step for additional DSP; it is not required to make the core codec path work.

## Storage and shutdown

Digitakt requires its ekFS sample volume. FORMAT +DRIVE provisions it; a live UI does not prove the sample filesystem mounted. Sample transfer uses the running Digitakt application. There is no preservation/conversion guarantee for an existing Digitone filesystem.

`internal/autosave_patch.py` changes the readiness function at `0x40001FA6` to read Digitone GPIO G3 (`0xEC09401E`, mask 8), rather than Digitakt GPIO A5. This feeds the native save-arming mechanism.

`internal/shutdown_patch.py` changes the aligned 32 KiB buffer copy at `0x4008D5AE` to 8,192 longword transfers. The eMMC commands, snapshot bytes and native slot format are retained. The reduced copy loop uses about 85% fewer instructions; that figure does not describe total shutdown time. The native snapshot is about 3.45 MiB, so physical hold-up time remains a real resource.

## RAM and instruction constraints

Both stock main-CPU bootstraps configure 128 MiB at `0x40000000..0x48000000`. Cached/uncached aliases refer to the same physical RAM. The secondary has a separate address space.

| Main-CPU area | Ownership |
| --- | --- |
| `0x43BAF5F0..0x47BAF640` | Digitakt sample pool, 64 MiB plus 80 bytes; end exclusive |
| `0x47BE0000` | TT1A copied panel/audio payload |
| `0x47C00000..0x48000000` | Native audio-input ring; end exclusive |

TT1A retains its original small payload placement. Do not grow this into the audio-input ring. The extension build instead explicitly reserves RAM from the native heap. An idle or empty sample buffer is not available mod memory. A stock Digitone mod layout is incompatible with the Digitakt sample pool.

The MCF5441x has no FPU. Assembler or emulator acceptance alone does not establish valid device instructions. The included audit rejects FPU/line-F encodings, instructions longer than six bytes, unsupported longword multiply addressing and prohibited MOVE source/destination combinations. Use register intermediates for immediate-to-absolute stores and load multiply constants into registers. Keep stack and callee-saved register preservation explicit at every hook.

## Source map

| Module | Responsibility |
| --- | --- |
| `internal/panel_patch.py` | Button tables and startup copy |
| `internal/led_patch.py` | LED IDs, slot selectors and small instruction emitter |
| `internal/autosave_patch.py` | Digitone capacitor-ready input |
| `internal/audio_patch.py` | Codec selection, reset, ordering and SSI receive edge |
| `internal/recovery_patch.py` | Core instruction-corrected audio layer |
| `internal/shutdown_patch.py` | Longword shutdown copy |
| `internal/retarget_transport.py` | Receiver envelope conversion |
| `internal/audit_added_code.py` | ColdFire instruction checks |
| `patch.py` | Python-only application of pinned patch data, packaging and release-hash verification |
| `internal/build_from_source.py` | Developer rebuild of the core patch from source |
