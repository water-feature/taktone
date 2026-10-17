# Sophie machines

Select an audio track, press FUNC+SRC and choose SOPHIE. Each of the eight audio tracks can select it independently; selection uses native machine ID 7 and is stored in sound/kit data. An assigned sample is unnecessary. Other machines keep their native source.

| Knob | Control |
| --- | --- |
| A | TUNE |
| B | MODEL: FUSE, BOOM, PIPE, SHARD |
| C | FOLD, 0–127 |
| D | Unassigned |
| E | SWEEP, -64 through +63 |
| F | METAL, 0–127 |
| G | FEEDBACK, 0–127 |
| H | COLOR, 0–127 |

MODEL uses four eight-step zones in stored range 0–31. SWEEP is bipolar and its onset is easiest to hear with fresh triggers. These controls have 128 steps where specified, with a maximum of 127. Sophie-aware defaults are applied on machine initialization; existing stored sounds/targets are not rewritten. The UI, scene capture and DSP packet use the same intended ranges.

Main handles native sequencing, LFOs/plocks, filter, AMP, mixer, sends and codec. Eight independent Sophie voices render on the secondary. Use AMP HOLD=NOTE and a finite DEC when checking gate/release. The pipeline adds one 32-frame block, approximately 0.667 ms at 48 kHz; precise short-note alignment needs workload-specific checking.

D has no label, knob graphic or status popup. The seven synthesis controls use the positions listed above. The slot is available for a future synthesis parameter.

Selected Sophie tracks produce silence on engine failure and never fall back to assigned samples. Native sample tracks retain their source. After 64 consecutive missing blocks, submission is disabled. Pending triggers coalesce, so late blocks do not provide a queued record of every note.

## RAM diagnostics

Main diagnostics use uncached `0x4B584000` (physical `0x43584000`). Reading them requires an external RAM reader; this package does not add a hardware acquisition tool. Offsets below are hexadecimal.

| Offset | Value |
| --- | --- |
| `00`, `04` | Status, startup poll count |
| `08`, `0C` | Last committed sequence, pending trigger mask |
| `10`, `14`, `18` | Completed blocks consumed, total misses, consecutive misses |
| `1C`, `20` | PA4 software level, failure stage |
| `24`, `28` | Shared hello and acknowledgement |
| `2C`, `30` | Currently selected and last submitted voice masks |
| `38` | Captured native trigger word |
| `3C` | DTIM0 request-edge counter |
| `40`, `44` | Last/max request-to-notification timer delta |
| `48`, `4C` | EPORT notification count, initial DTIM0 mode |
| `50`, `54`, `58` | First failed shared offset, intended word, readback word |

Timer deltas include transfer and interrupt latency and have not been calibrated into physical rendering time. The sampled emulator estimate of 43.2% at assumed 250 MHz excludes wait states/contention and is not measured spare hardware capacity. Eight-track hardware playback succeeded in the author's workload; parameter extremes, simultaneous retriggers, heavy modulation, recording and storage can change costs.
