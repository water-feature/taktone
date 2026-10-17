# Developing taktone machines

Keep the instrument integration on the main CPU and synthesis state/rendering on the secondary. Main has the sequencer, parameter locks, LFOs, machine menu, sound storage and downstream processing. Secondary receives a complete control snapshot and produces one block of PCM for each selected voice.

For a complete compiling example, use the standalone extensions package. It builds the complete extended firmware from stock inputs and includes the loader, shared protocol, machine registration, parameter UI, source substitution, scenes and Sophie engine. The [secondary-link reference](../internal/reference/secondary-link/README.md) isolates the transport assembly for reuse without requiring Sophie synthesis. See [secondary CPU and Sophie integration](SECONDARY-CPU.md) for the complete data flow.

## Implementation contract

1. Define engine init, trigger/gate and 32-sample render functions with explicit state sizes and fixed-point scaling. Allocate state and tables in secondary-local RAM. Compile for `-mcpu=54418 -msoft-float` with freestanding options; ARM/SHARC binaries are incompatible. Review helper calls, integer overflow, divisions and worst-case control recalculation costs.
2. Claim all main and secondary memory ranges. The core's small payload does not provide general-purpose storage. Use a reserved allocator region or deliberately reduce another native allocation. Never borrow the sample pool or input ring because a test snapshot looks empty.
3. Keep the established serial/FPGA startup. Replace the engine only after its hardware setup, install the render interrupt, initialize local state and publish a custom ready tag shared by both sides.
4. Define a versioned wire layout with explicit widths, alignment, deterministic padding, sequence ownership and completion. Check C layouts with static assertions. Build controls locally and publish aligned shared longwords with readback; checksum intended words. Add input PCM only if the engine needs it. Do not enlarge shared storage based solely on emulator mappings.
5. Register a machine ID, descriptor and parameter map on main. Persist selection with native sound/kit data. Supply defaults, formatters, discrete/bipolar ranges and every UI range path, including scenes. All eight knobs are available for synthesis; a dedicated status slot is optional.
6. Read native effective parameters after modulation. Capture trigger state before native source processing consumes it. Substitute secondary PCM at the existing voice source boundary and retain filter/AMP/mix/FX. Test pitch, velocity, gate, release, machine switching and sample coexistence.
7. Specify late-output behavior and track ownership. Taktone-extended uses silence for failed custom voices, one outstanding packet, per-block miss counters and shutdown after 64 consecutive misses. Pending triggers coalesce; they are not an unbounded event queue. Another design may need explicit queuing and ping-pong buffers.

## Key integration rules

Preserve scratch/callee-saved registers, stack alignment, IRQ frames and any EMAC state the hook touches. Review actual emitted ColdFire instructions independently of assembler/emulator acceptance. Disassembly is authoritative for patch operands; rebased decompiler references may be stale. Check expected stock bytes at every hook and reject unknown firmware hashes.

Scene targets must enter the native smoothing input rather than overwriting smoothed output. Restore temporary source values after processing, so release follows the current sequencer/modulation state. Parameter capture must verify the provider object's domain as well as its numeric track index; FX and audio providers can share index zero.

Native saves must retain their own return values and run regardless of extension errors. Stage and validate extension reads before publishing; preserve local edits on failed reads and background refreshes. Bind data to a stable project identity and an explicit transaction. Keep shutdown scratch separate from normal I/O scratch. A RAM-ready engine/UI and a persistence-ready extension are distinct states.

## Verification

Compare host-engine output against actual emitted secondary code for one through eight voices. Exercise simultaneous triggers, extreme controls, per-block parameter/model changes, sleep/retrigger and mixed sample/custom tracks. Fixed-parameter timing misses potentially expensive reconfiguration paths.

Exercise ordinary encoders, scene edits, modulation, sound recall, machine switching and save/reload through native UI input. Check shared write widths, bad readback, stale sequences, checksum failure, missing completion, reset and timeout. Verify boot, sample mount, full input/output audio, recording and storage activity.

Measure physical worst-case deadlines and cache/DMA visibility. Emulator cycle estimates exclude unknown wait states and contention; successful playback at a tested workload does not quantify remaining CPU capacity. Audio effects need latency and dry/wet alignment tests in addition to synth voice tests.

## Starting points in the extension source

| File | Adaptation point |
| --- | --- |
| `internal/prototype/sophie-secondary-v4/main.s` | Loader, handshake, IRQ glue and source hook |
| `audio.c`, `protocol.h` | Main effective controls, block commit and PCM substitution |
| `secondary.s`, `kernel.c` | Secondary init/IRQ, state and rendering |
| `ui.s`, `ui.c`, `upstream/machines.s` | Machine selection, native persistence, labels, defaults and ranges |
| `build.py`, `engine.ld` | Compilation, memory bounds and exact patch sites |
| `macro_patch.py`, `macro_runtime.py`, `macros_*.s` | Scene integration and persistence |

Sophie is the implemented engine. Additional engines need their own source/license review, adapter and workload measurements; their cost cannot be inferred from Sophie.
