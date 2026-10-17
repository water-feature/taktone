# Secondary CPU and Sophie integration

The original Digitone already contains the second CPU, shared-memory bridge and FPGA. “Connecting” it means bringing up those existing interfaces from Digitakt main firmware; no added chip or wiring modification is part of this project. TT2A uses it to render eight Sophie voices. Main runs the Digitakt sequencer, modulation, track UI and downstream audio processing; the secondary receives control snapshots and returns voice audio. TT1A leaves the secondary idle.


## How Sophie is integrated

The implementation lives in `internal/prototype/sophie-secondary-v4/`. The engine comes from [soejrd/digisophie](https://github.com/soejrd/digisophie), based on Matt Estela’s Sophie algorithm; see [acknowledgements and licenses](../../README.md#acknowledgements).

1. [The builder](../internal/prototype/sophie-secondary-v4/build.py) compiles `upstream/sophie.c` with the secondary adapter in `kernel.c`. It adds the engine and interrupt wrapper to a copy of stock Digitone section 7. Expected-byte checks guard the three substitution sites: initialization at `0x40000B7A`, the stock engine-init call at `0x40000B80`, and render entry at `0x400008FA`. Stock CPU, SRAM and FPGA initialization stay in place.
2. [The main driver](../internal/prototype/sophie-secondary-v4/main.s) boots that modified program over the existing serial link. The upload streams are embedded in main’s reserved memory; the firmware container’s stock sections 6 and 7 are preserved. Startup advances from the UI frame callback, with a limit of 120 polls, and waits for the custom ready tag before permitting audio requests.
3. [Machine registration and UI](../internal/prototype/sophie-secondary-v4/ui.c), together with `ui.s` and `upstream/machines.s`, expose SOPHIE as native machine ID 7. Each audio track selects it independently, and native sound/kit storage retains the selection. Seven synthesis controls supply tune, model, fold, sweep, metal, feedback and color; D is unassigned. See [Sophie controls](SOPHIE.md).
4. [The main audio adapter](../internal/prototype/sophie-secondary-v4/audio.c) identifies selected Sophie tracks from active or kit sounds. It reads effective native parameters after modulation, captures triggers before native source processing consumes them, and builds one control record per track. Main retains sequencing, parameter locks, LFOs, gate/level information and native sound persistence.
5. [The secondary adapter](../internal/prototype/sophie-secondary-v4/kernel.c) validates and copies each new packet, then renders up to eight independent Sophie voice states. Each enabled voice receives gate/level state, the trigger and synthesis controls. Rendering produces 32 signed 32-bit mono samples per track, including Sophie folding. Disabled voices are reset; inactive or sleeping voices without a trigger produce silence.
6. Main consumes only matching completed output and substitutes Sophie PCM at hook `0x40077FBA`, before native filter, AMP, sends and mix. Sample tracks keep native audio. This is a one-block pipeline: approximately 0.667 ms at 48 kHz. The audio callback never waits for the secondary.

## Control and audio exchange

[protocol.h](../internal/prototype/sophie-secondary-v4/protocol.h) defines eight 28-byte control records, each containing enabled/trigger flags, level, phase, Sophie parameters and deterministic padding. Main views shared RAM at `0x10000000`; the secondary views it at zero.

| Shared offset | Purpose |
| --- | --- |
| `0x008` | Custom ready tag `0x53503233` |
| `0x100` | Committed request sequence |
| `0x104` | Completed sequence |
| `0x108..0x1e7` | Eight control records, 224 bytes total |
| `0x1e8` | XOR checksum of the sequence and 56 control longwords |
| `0x3a0..0x79f` | Eight 32-frame mono output blocks |

Main assembles controls locally, writes aligned longwords with readback, writes the checksum, commits the sequence and toggles PA4. Secondary DTIM0 capture enters the render wrapper, which preserves D0–D7/A0–A6. The renderer rejects zero, repeated, unstable or checksum-invalid sequences. It writes PCM before publishing completion and signals main through PG2/EPORT4.

Only one packet can be outstanding. Main consumes output only for the completed sequence and tracks included in its submitted mask. Selected Sophie tracks produce silence while output is unavailable; they do not fall back to samples. Missing output increments counters and stops submission after 64 consecutive misses. Pending triggers coalesce while a packet is outstanding. A shared-write readback mismatch stops submission before committing a new request.

See [extension architecture](DEVELOPMENT.md) for reserved memory, hook addresses and scene integration, and [Sophie diagnostics](SOPHIE.md#ram-diagnostics) for status and failure counters. To add an engine, follow [machine development](MACHINE-DEVELOPMENT.md).

## Board interface

| Function | Main CPU | Secondary CPU |
| --- | --- | --- |
| Reset | PB6: low holds reset | Starts serial boot on release |
| Upload | DSPI2 slave, eDMA 29, vector 149 | Supplies SPI clocks; section 6 loads section 7 |
| Shared SRAM | FlexBus at `0x10000000` | FlexBus at `0x00000000` |
| Notification | EPORT4, vector 68 | PG2 edge |
| Audio render request | PA4 edge | DTIM0 capture, vector 96 |

Shared addresses are CPU-relative views of the same storage. The native protocol uses offsets below `0x7a0`; the emulator's larger mapping does not establish usable hardware capacity beyond it.

Digitone FlexBus settings are CS0 base `0x10000000`, mask `0x00010001`, control `0x780`; CS1 base zero, mask `0x00010001`, control `0xfd80`. Pin mux, GPIO direction and interrupt setup must agree with these settings. Set PB6 direction with a read/modify/write preserving existing Digitakt GPIO users, especially PB0.

The complete register order, DMA descriptors, IRQ handlers and timeout logic are in the [main-side reference](../internal/reference/secondary-link/main.s). Its [integration notes](../internal/reference/secondary-link/README.md) explain the required callbacks/constants. This is an engine-independent integration template. The installed Sophie driver is [main.s](../internal/prototype/sophie-secondary-v4/main.s) in the implementation directory.

## Boot sequence

1. Reserve main-side code, state and serial staging buffers. Hold PB6 low; install upload/notification handlers; configure pin mux, FlexBus and DSPI2. Clear stale shared ready/sequence words, which can survive a main reset.
2. Prepare section 6 from the user-supplied Digitone container: eight leading `FF` bytes, the stock loader, and four trailing zero bytes. Set byte 9 of this framed stream to `0F`. The implemented stream is 1,504 bytes. Follow the native transfer descriptor and reset-release ordering.
3. Start DMA 29 and release PB6. The secondary supplies clocks for the DSPI2 slave transfer. The upload IRQ advances to the section-7 stream, prefixed by `AA`. The implementation uses the native rolling DMA stream with a `0x6000` iteration count; it is not a one-shot section-length descriptor.
4. Section 7 loads at secondary `0x40000400`, entering at `0x40000B92`. Retain its stock CPU/SRAM initialization and FPGA programming.
5. Wait for shared words `HO` (`0x484f`) at +0 and `HA` (`0x4841`) at +2. Write **1 to +2 before writing `B0` (`0x4230`) to +0**.
6. The stock secondary writes `A5A5` at +4 and installs its render path. A custom engine must initialize local state, install vector 96 and then publish its own ready tag. The working implementation uses `0x53503233` at +8. Wait for this tag before sending PA4 edges.
7. Disable upload submission after readiness. Continue output requests only while the engine is healthy. On bounded startup failure, disable DMA submission and hold reset; retries or restart work belong outside the audio callback.

The working main driver polls startup at UI frames and limits progress to 120 polls. This is a bounded polling count rather than a calibrated time duration. Use diagnostics to distinguish stages; a stage does not identify an electrical cause.

Do not send block edges before custom readiness. The initial stock vector-96 handler restarts FPGA initialization. `A5A5` alone does not establish that the final render handler is installed.

## FPGA

Stock section 7 decompresses the bitstream from `0x400077A0` to `0x40009000`: 54,664 bytes, sent as 27,332 16-bit words over secondary DSPI1, followed by trailing clocks `0x1800ffff`. GPIO H4 is pulsed, E0 is awaited, and F7 is checked. PROGRAM_B/INIT_B/DONE are inferred signal roles; no board-level net trace is included.

FPGA setup completes before HO/HA. Retain this path when substituting an engine. INIT-related failures return codes 1–3; missing DONE returns 4. SPI FIFO/completion polling can stall indefinitely in stock secondary code, so the main-side timeout must remain independent. Emulation supplies status pins and does not execute the FPGA as logic.

The custom build retains stock container sections 6 and 7. Its modified secondary program is embedded in main's payload and uploaded at runtime, preserving the stock boot/update sections.

## Audio boundary

Native Digitone exchanges a 928-byte parameter packet at shared `0x000..0x39f`, then receives eight mono voices of 32 signed 32-bit samples at `0x3a0..0x79f`. Native main uses DMA 47, parameter SRAM `0x80001C00` and voice SRAM `0x80004110`. Those are **Digitone-main** addresses, not addresses to transplant into Digitakt.

Main owns sequencing, modulation, voice selection, filter/AMP processing, effects, mix and codec output. Keep Digitakt's SSI1 DMA 52/54 and native buffer addresses. Its audio IRQ timing/mixer entry points are `0x40076C38` and `0x40077420` for the 1.53-derived application. DMA 30 is already used. Peripheral availability must be checked across recording, storage and Transfer, not inferred from one idle snapshot.

At 48 kHz and 32 frames, one block is 666.7 microseconds. The native packet plus voice payload is about 2.928 MB/s before bus overhead. Treat both as interface budgets, not measured hardware throughput.

For a new synth, send controls and return voice PCM. For an effect, also transfer input audio and account for pipeline latency. Do not wait in the audio IRQ for late secondary output. Publish controls before the request sequence, validate on the receiver, publish output before completion, and consume only matching completed output. Aligned longword shared writes with readback are the proven implementation choice. The electrical reason individual byte stores were unreliable has not been established.

## Reusing native FM

Starting stock section 7 is not enough to create a playable FM machine in Digitakt. Digitone main builds the parameter packet, handles note/voice allocation and performs downstream processing. MIDI bytes and Digitakt sample parameters are not its packet format.

The native renderer exposes these partial boundaries:

| Offset | Observed consumer |
| --- | --- |
| `0x000` | Eight `0x4a`-byte per-voice records |
| `0x250` | Eight `0x18`-byte records |
| `0x310` | Output initialization data |
| `0x330` | Eight per-voice longwords |
| `0x350` | Engine pointer argument |
| `0x370`, `0x374` | Engine longword arguments |
| `0x37c` | Eight three-byte records |
| `0x394` | Signed-word engine argument |

These are structural observations; musical parameter meanings remain undecoded. Capture a continuous known-audible native note stream, trace main's packet writers, and replay into fresh secondary state before implementing a translator. There is no validated native-FM patcher in these packages. Stock FM processes all eight voices per block, including silent voices, so using fewer musical tracks does not establish spare compute capacity.
