secondary_init:
 lea (-60,SP),SP
 movem.l { D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 },(SP)
 jsr @INIT_C
 move.l #@secondary_irq,D0
 move.l D0,(0x40000180).l
 move.l #0x53503233,D0
 move.l D0,(0x8).l
 movem.l (SP),{ D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 }
 lea (60,SP),SP
 rts
secondary_irq:
 lea (-60,SP),SP
 movem.l { D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 },(SP)
 moveq 1,D0
 move.b D0,(0xfc070003).l
 jsr @RENDER_C
 movem.l (SP),{ D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 }
 lea (60,SP),SP
 rte
