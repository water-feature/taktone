/* SPDX-License-Identifier: MIT */
#include "protocol.h"
extern uint8_t core_track_machine[TRACKS];
static uint32_t selected(void) {
    uint32_t m=0;
    for(unsigned t=0;t<TRACKS;t++) {
        uint32_t sound=REG32(0x800019b4u+4*t);
        if(!sound && REG32(0x800019acu)) sound=REG32(0x800019acu)+32+162*t;
        if(sound && REG8(sound+126)==7) m|=1u<<t;
    }
    return m;
}
static uint32_t u7(unsigned t,unsigned o) {
    return (*(volatile uint16_t *)(0x80002794u+106*t+o)>>8)&127;
}
static void controls(unsigned t,struct control *c,uint32_t mask) {
    int32_t pitch=((int32_t)*(volatile int16_t *)(0x80002794u+106*t)-0x4000)*256
        + *(volatile int32_t *)(0x80001f28u+4*t)+0x30000;
    if(pitch<0) pitch=0;
    if(pitch>0x570000) pitch=0x570000;
    uint32_t inc=((const uint32_t *)0x4019b1c0u)[(uint32_t)pitch/384]>>23;
    c->enabled=(mask>>t)&1;
    c->trigger=(DIAG->pending>>t)&c->enabled;
    c->level=*(volatile int32_t *)(0x4199df58u+12*t);
    c->phase=*(volatile int32_t *)(0x4199df54u+12*t);
    c->params.phase_inc=inc<8?8:inc;
    c->params.model=u7(t,2)>>3;
    c->params.fold=u7(t,4);
    c->params.sweep=(int32_t)u7(t,8)-64;
    c->params.metal=u7(t,10);
    c->params.feedback=u7(t,12);
    c->params.color=u7(t,14);
    c->params.velocity=(*(volatile uint16_t *)(0x80001f18u+2*t)>>8)&127;
    /* Wire padding is included in checksum: always write deterministically. */
    ((volatile uint8_t *)&c->params)[9]=0;
    ((volatile uint8_t *)c)[26]=0;
    ((volatile uint8_t *)c)[27]=0;
}
void audio_c(void) {
    uint32_t mask=selected(), seq=DIAG->seq;
    DIAG->selected=mask;
    DIAG->pending=(DIAG->pending|REG32(0x4b584038u))&mask;
    int ready=DIAG->status==4;
    int complete=ready && seq && REG32(SHARED_MAIN+0x104)==seq;
    for(unsigned t=0;t<TRACKS;t++) if(mask&(1u<<t)) {
        volatile int32_t *dst=(volatile int32_t *)(0x80001a18u+128*t);
        volatile int32_t *src=(volatile int32_t *)(SHARED_MAIN+0x3a0+128*t);
        for(unsigned i=0;i<32;i++) dst[i]=complete && (DIAG->submitted&(1u<<t))?src[i]:0;
    }
    /* Selected Sophie tracks stay silent on failure; never substitute a sample. */
    if(!ready) return;
    if(seq && !complete) {
        DIAG->misses++;
        if(++DIAG->miss_run>=64) { DIAG->fail_stage=4; DIAG->status=5; }
        return;
    }
    if(complete) {DIAG->completed++;DIAG->miss_run=0;}
    /* Assemble in main RAM: shared FlexBus receives aligned longwords only.
     * Byte strobes are not established for this board's shared-memory path. */
    union { struct control track[TRACKS]; uint32_t words[56]; } packet;
    for(unsigned t=0;t<TRACKS;t++) controls(t,&packet.track[t],mask);
    DIAG->pending=0;
    if(!++seq) seq=1;
    uint32_t sum=seq;
    for(unsigned i=0;i<56;i++) {
        REG32(SHARED_MAIN+0x108+4*i)=packet.words[i];
        uint32_t readback=REG32(SHARED_MAIN+0x108+4*i);
        if(readback!=packet.words[i]) {
            REG32(0x4b584050u)=0x108+4*i;
            REG32(0x4b584054u)=packet.words[i];
            REG32(0x4b584058u)=readback;
            DIAG->fail_stage=7;DIAG->status=5;
            return;
        }
        sum^=packet.words[i];
    }
    REG32(SHARED_MAIN+0x1e8)=sum;
    DIAG->submitted=mask;
    DIAG->seq=seq;
    REG32(SHARED_MAIN+0x100)=seq;
    (void)REG32(SHARED_MAIN+0x100);
    REG32(0x4b58403cu)=REG32(0xfc07000cu);
    DIAG->pa4^=1;
    REG8(DIAG->pa4?0xec094018u:0xec094024u)=DIAG->pa4?16:239;
}
