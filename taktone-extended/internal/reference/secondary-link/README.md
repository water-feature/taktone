# Secondary link assembly template

These transport and IRQ routines are separated from the engine. They are reference source, not installed by the core patcher. They require main callbacks/state, a reserved upload region and a compiled secondary engine. The complete linked implementation is in [the Sophie source directory](../../prototype/sophie-secondary-v4/). See [secondary CPU and Sophie integration](../../../docs/SECONDARY-CPU.md) for the boot and audio flow.

`main.s` expects these link constants (addresses belong to the extension memory layout and are not free-space claims in TT1A):

| Symbol | Value / purpose |
| --- | --- |
| `STATUS` | `0x4B584000` |
| `BOOT_TICKS`, `SEQ`, `PENDING_TRIG` | Status +4, +8, +12 |
| `COMPLETED`, `MISSES`, `MISSES_RUN`, `PA4` | Status +16, +20, +24, +28 |
| `FAIL_STAGE`, `HELLO`, `ACK` | Status +32, +36, +40 |
| `S6`, `S7` | `0x4B585000`, `0x4B586000`: uncached framed serial streams |
| `OLD_FRAME` | Displaced frame callback; tail-called after poll |
| `MACHINE_TICK` | Machine lifecycle callback, must preserve the expected ABI |
| `AUDIO_C` | Main block callback to transfer controls and consume completed PCM |

The driver also uses diagnostic words through status +`0x58`. Reserve/initialize the whole state region, not only named constants. Its main code lives at physical `0x43580000`; all these placements rely on the extension build's reserved native heap. TT1A does not reserve them.

`secondary.s` expects `INIT_C` and `RENDER_C` function addresses. Initialization writes vector 96 at `0x40000180` and the ready tag at shared +8; IRQ entry preserves D0–D7/A0–A6 and returns with RTE. The supplied callback ABI requires C functions that return normally. Engine code must handle any additional special/EMAC state it uses.

The ready tag is `0x53503233` on both CPUs. Change both checks if changing its protocol meaning. Initialize main state and clear shared readiness before reset release. Preserve stock section-7 initialization through the engine substitution points (`0x40000B7A`, `0x40000B80`, `0x400008FA`); see the complete extensions builder for expected-byte checks and patch lengths.

The reference uses the project's Ghidra-style assembly syntax. The taktone-extended package's `assemble.py` translates this driver syntax for GNU binutils. Its main audio hook restores displaced `LEA 0x4199E444,A4`; do not reuse that wrapper at another site without preserving that site's original operation.
