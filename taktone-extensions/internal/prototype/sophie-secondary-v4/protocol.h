/* SPDX-License-Identifier: MIT */
#include <stdint.h>
#include "upstream/sophie.h"
#define TRACKS 8
#define TAG 0x53503233u
#define SHARED_MAIN 0x10000000u
struct control {
    uint32_t enabled, trigger;
    int32_t level, phase;
    struct ds_params params;
    uint16_t padding;
};
_Static_assert(sizeof(struct control)==28,"wire control size");
_Static_assert(sizeof(struct control)*TRACKS+0x108==0x1e8,"wire checksum offset");
struct diagnostics {
    volatile uint32_t status, polls, seq, pending, completed, misses, miss_run, pa4;
    volatile uint32_t fail_stage, hello, ack, selected, submitted, late_irq;
};
#define DIAG ((struct diagnostics *)0x4b584000u)
#define REG32(a) (*(volatile uint32_t *)(a))
#define REG8(a) (*(volatile uint8_t *)(a))
