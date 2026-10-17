# Extension architecture

The complete build has three layers: the core crossport, four scenes per pattern, and the secondary machine integration. `internal/build_from_source.py` rebuilds each layer from stock firmware. The end-user `patch.py` applies bundled patch data with Python alone. Ghidra assembles scene runtime source; GNU tools compile/assemble the secondary driver and engine. The source builder needs no previously generated firmware. See [build workflows](BUILDING.md).

For the boot sequence and end-to-end Sophie audio path, see [secondary CPU and Sophie integration](SECONDARY-CPU.md). For new engines, see [machine development](MACHINE-DEVELOPMENT.md).

## Main/secondary split

| File | Responsibility |
| --- | --- |
| `internal/prototype/sophie-secondary-v4/main.s` | GPIO/FlexBus/DSPI2 setup, DMA 29 serial boot, bounded handshake, IRQ glue and source hook |
| `secondary.s` | Secondary engine initialization, vector-96 wrapper and custom ready tag |
| `audio.c` | Effective controls, aligned shared publication and completed voice substitution |
| `kernel.c` | Eight secondary-local voices, packet validation, render, output completion |
| `protocol.h` | Exact control/diagnostic ABI |
| `ui.s`, `ui.c` | Machine registration, defaults, labels, formatters and ranges |
| `upstream/machines.s` | Native machine selection/storage/parameter integration |
| `build.py`, `engine.ld` | Compilation, linking, memory bounds and expected-byte patch sites |

Main retains native source processing, then replaces selected Sophie voice PCM at hook `0x40077FBA`, before normal downstream filtering/AMP/mix. Hook `0x40077F8E` captures native triggers before source processing consumes them. Selected machines are checked through active sound pointers, falling back to kit sounds. The driver does not depend only on sample-renderer dispatch bytes.

The builder retains stock Digitone container sections 6/7, embeds a modified secondary image in its main payload and uploads it at runtime. It patches secondary initialization at `0x40000B7A`, skips the stock engine-init call at `0x40000B80`, and redirects render entry `0x400008FA`. Stock CPU/FPGA setup remains. Ready tag `0x53503233` at shared +8 is published after custom vector/state initialization, before main permits audio edges.

## Shared protocol

| Offset | Content |
| --- | --- |
| `0x008` | Custom ready tag `0x53503233` |
| `0x100` | Main committed sequence |
| `0x104` | Secondary completed sequence |
| `0x108..0x1e7` | Eight 28-byte controls in track order |
| `0x1e8` | XOR of sequence and 56 control longwords |
| `0x3a0..0x79f` | Eight 32-frame signed int32 mono blocks |

Main maps shared memory at `0x10000000`; secondary maps it at zero. Each control contains enabled and trigger longwords, signed level and phase longwords, a 10-byte `ds_params` structure, and explicit padding to 28 bytes. `layout.c` and `protocol.h` assert the actual ColdFire layout; the headers specify field order and widths.

Main builds all 224 control bytes in a local union with 56 longwords. It writes each aligned word to shared RAM and checks readback. Any mismatch records diagnostics, disables submission and prevents sequence commit. Padding is initialized deterministically. The checksum is calculated from intended local words.

There is one outstanding packet. Main consumes output only for matching completed sequences and voices that were enabled in the submitted mask. It writes payload and checksum before committing the new sequence, then toggles PA4. Secondary copies controls locally, checks checksum and sequence stability, renders all voices, writes PCM, then publishes completion and notifies main via PG2/EPORT4. Repeated/zero/bad sequences cannot publish output.

Do not add byte-sized shared control writes. Do not block the audio callback waiting for secondary output. Larger packets, stereo effects, buffering or new event queues require a protocol and memory review on both sides. Additional latency also needs alignment checks against sample tracks and dry paths.

## Memory

Both stock main bootstraps configure 128 MiB. Main physical `0x40000000..0x48000000` and uncached aliases are the same memory. Native Digitakt sample pool `0x43BAF5F0..0x47BAF640` and audio-input ring `0x47C00000..0x48000000` are preserved.

The build explicitly reduces the native buddy heap from 16 MiB to 8 MiB, reserving `0x4319D6B0..0x4399D6B0` (end exclusive). Buddy metadata remains outside; BSS clearing excludes this extent. Boundary guards are at `0x4319D6B0` and `0x4399D6AC`. This is an allocator reservation, not additional physical RAM.

| Region | Ownership |
| --- | --- |
| `0x431A0000` | Copied core adaptation payload |
| `0x431B0000`, `0x431B8000` | Scene runtime and state |
| `0x431B8400..0x431B93ff` | Published immutable audio overlay buffers |
| `0x431BC000`, `0x431BD000`, `0x431BE000` | Native header scratch, source-parameter restore, diagnostic ring |
| `0x431C0000..0x4323ffff` | Live 512 KiB scene table |
| `0x43240000`, `0x43248000` | Extension header, scratch |
| `0x43250000`, `0x43254000` | Pattern scene clipboard rows, scene clipboard |
| `0x432C0000..0x4333ffff` | Normal packing scratch |
| `0x433C0000..0x4343ffff` | Saved scene checkpoint table |
| `0x43440000..0x434Bffff` | Staging/snapshot table |
| `0x434C0000`, `0x43500000..0x4357ffff` | Separate shutdown header and packing scratch |
| `0x43580000..0x435C9804` | Driver/state and padded upload streams; end exclusive |

The Sophie main-side region is 301,060 bytes, mostly upload storage, inside the existing reservation. Driver state is accessed via uncached `0x4B584000`; serial streams begin at `0x4B585000`/`0x4B586000`. Startup copies through the uncached alias. The builder checks its end against the high guard.

Secondary engine code starts at `0x40020000`, IRQ wrapper at `0x40022000`, eight 82-byte voice states at `0x40024000..0x40024290` (end exclusive), local copied controls at `0x40024400`, and last sequence at `0x40024500`. Initialization explicitly clears engine state without relying on stock BSS extent.

Do not transplant stock-Digitone mod/buffer allocations: `0x43EC0000..0x44000000` and `0x44000000..0x47BE0000` overlap the Digitakt sample pool. No memory region becomes available merely because current samples are sparse. Account for reserved regions and native allocator headroom separately.

## Scene audio and UI hooks

`internal/macro_patch.py` installs expected-byte-checked main hooks. `internal/macro_runtime.py` supplies constants and generated getters; `internal/macros_runtime.s` handles UI and audio; `internal/macros_storage.s`, `internal/macros_partial.s` and `internal/macros_pattern.s` handle persistence and native operations.

| Hook | Address |
| --- | --- |
| UI key / encoder calls | `0x4000B770`, `0x4000B7BA` |
| UI tick / draw | `0x4000A770`, `0x4000A7D6` |
| Central setter | `0x4000FEF6` |
| Sound / FX getter vtables | `0x4017EB80`, `0x4017EC00` |
| Native smoother call | `0x40077E9A` |
| Project load / save | `0x40092480`, `0x4001692A` |
| Pattern save / kit save / reload | `0x400165AC`, `0x4001669A`, `0x400162A0` |
| Pattern clear / shutdown insertion | `0x400849A0`, `0x4008DA22` |

Scene capture requires both audio-track sound-provider identity and track 0–7. Numeric index alone cannot distinguish FX/master from an audio track. Unsupported providers keep native behavior. Silent editing intercepts the setter before ordinary stored-sound changes; contextual getters show learned values. Synthetic key IDs 49–52 have complete reverse-map entries, and FUNC state comes from the native physical key bitmap.

The UI compiles a sparse immutable overlay, published through double buffering. The audio hook installs targets into native smoothing input and restores source shorts afterward. It does not perform disk I/O, rebuild the full table or bypass native smoothing. Release follows current sequencer values. Sophie-specific scene range lookup shares the normal UI adapter; otherwise borrowed native machine ranges can clamp valid engine controls.

## Scene storage format and transactions

Each scene occupies 1,024 bytes: enabled state at +0, explicit `SCN3` edit marker at +4, 60-byte validity bitmap at +8, and 477 signed big-endian short targets at +68. Four scenes form a 4,096-byte pattern row; 128 rows form the 512 KiB table. The layout retains nine domains of 53 fields for compatibility; current capture admits only eight audio-track domains, with global FX/master unsupported.

Native project/autosave slots are 4 MiB. Native serialization occupies 32 KiB chunks 0–110; extension commit header uses chunk 111, with sparse rows in 112–127 (eight occupied rows per data chunk). Header magic is `XMAC`, schema 4; valid schema-3 data can migrate. A reconstructed-table checksum and semantic checks validate data. Data precedes the header commit. This detects interrupted writes but is not redundant storage guaranteeing the previous on-disk checkpoint survives every interruption.

Ordinary slots start at sector `0x80000 + slot*0x2000`; the temporary project starts at `0x7E000`; autosaves at `0x7A000`/`0x7C000`. Project UUID is an identity, not a physical slot number. Schema 4 binds to native project UUID within the slot rather than hashing the whole packed native project.

Normal I/O uses native recursive MMC-manager locking. Full saves snapshot stable live scene state before writing; partial saves update the appropriate saved rows without discarding unsaved rows. Reads reconstruct in staging and publish only after the relevant native transaction succeeds. Initial read failure retains RAM usability and suppresses full writes over the unread checkpoint. Explicit successful temporary save/reload can reconcile saved rows with locally edited rows, including intentional clears. Different-owner failures quarantine old locks.

Native persistence always runs and preserves its own return result independently of extension status. The boot worker restores scenes before its first temporary-project checkpoint. Polling shutdown uses separate header/packing scratch and no normal RTOS waits. Dense shutdown scenes add up to 17 chunks; power margin must be measured on hardware.

## Extending the engine

Change main UI descriptors/defaults/ranges, wire controls, secondary state/rendering and both protocol checks together. Seven synthesis controls are used by this Sophie release; D is unassigned and available for another synthesis parameter. Preserve native modulation, sound persistence and sample coexistence. Include control changes in timing tests, not only fixed patches.

Compile with `-mcpu=54418 -msoft-float -Os -ffreestanding -fno-builtin -fno-common -fno-pic -fwrapv -fno-jump-tables`, and audit emitted code. The toolchain can emit instructions an emulator accepts but the chip rejects, so retain the explicit ColdFire MOVE/MUL and six-byte checks. Check physical deadlines, cache/bus behavior and musical latency separately from functional emulator/host comparisons.
