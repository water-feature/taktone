/* SPDX-License-Identifier: MIT */
#include "protocol.h"
/* Explicit secondary-local state; no reliance on the stock BSS clear extent. */
#define VOICES ((struct ds_voice *)0x40024000u)
#define LOCAL ((struct control *)0x40024400u)
#define LAST REG32(0x40024500u)
void init_c(void) {
    for(unsigned t=0;t<TRACKS;t++) ds_voice_init(&VOICES[t]);
    LAST=0;REG32(0x104)=0;
}
void render_c(void) {
    uint32_t seq=REG32(0x100);
    if(!seq || seq==LAST) return;
    uint32_t sum=seq;
    for(unsigned i=0;i<56;i++) {
        uint32_t v=REG32(0x108+4*i);
        ((uint32_t *)LOCAL)[i]=v;sum^=v;
    }
    if(sum!=REG32(0x1e8) || seq!=REG32(0x100)) return;
    for(unsigned t=0;t<TRACKS;t++) {
        struct control *c=&LOCAL[t];struct ds_voice *v=&VOICES[t];
        int32_t *out=(int32_t *)(0x3a0+128*t);
        if(!c->enabled) ds_voice_init(v);
        else ds_voice_gate(v,c->level,c->phase);
        if(!c->enabled || (!c->trigger && (!v->active || v->sleeping))) {
            for(unsigned i=0;i<32;i++) out[i]=0;
        } else {
            ds_voice_render(v,&c->params,c->trigger,out,32);
            ds_fold_block(out,32,c->params.fold);
        }
    }
    LAST=seq;
    /* Volatile completion follows all PCM writes. */
    __asm__ volatile ("" ::: "memory");
    REG32(0x104)=seq;
    ((void (*)(void))0x400008d4u)();
}
