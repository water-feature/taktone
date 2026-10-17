main_poll:
 lea (-60,SP),SP
 movem.l { D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 },(SP)
 move.l (@STATUS).l,D0
 beq.w @main_setup
 cmpi.l #4,D0
 beq.w @main_poll_done
 cmpi.l #5,D0
 beq.w @main_failed
 cmpi.l #1,D0
 beq.w @main_release
 addq.l #1,(@BOOT_TICKS).l
 move.l (@BOOT_TICKS).l,D1
 cmpi.l #120,D1
 bge.w @main_fail
 cmpi.l #2,D0
 bne.w @main_poll_done
 move.w (0x10000000).l,D0
 cmpi.w #0x484f,D0
 bne.w @main_check_ready
 move.w (0x10000002).l,D0
 cmpi.w #0x4841,D0
 bne.w @main_check_ready
 moveq 1,D0
 move.w D0,(0x10000002).l
 move.w #0x4230,D0
 move.w D0,(0x10000000).l
main_check_ready:
 move.l (0x10000000).l,D0
 move.l D0,(@HELLO).l
 move.l (0x10000004).l,D0
 move.l D0,(@ACK).l
 move.l (0x10000008).l,D0
 cmpi.l #0x53503233,D0
 bne.w @main_poll_done
 moveq 4,D0
 move.l D0,(@STATUS).l
 clr.l (@BOOT_TICKS).l
 moveq 29,D0
 move.b D0,(0xfc04401a).l
 bra.w @main_poll_done
main_setup:
 move.l #@main_notify_irq,D0
 move.l D0,(0x40000110).l
 moveq 0,D0
 move.w (0xfc090000).l,D0
 ori.l #0x300,D0
 move.w D0,(0xfc090000).l
 moveq 6,D0
 move.b D0,(0xfc048044).l
 moveq 4,D0
 move.b D0,(0xfc04801d).l
 moveq 0,D0
 move.b (0xfc090003).l,D0
 ori.l #0x10,D0
 move.b D0,(0xfc090003).l
 moveq 0,D0
 move.w (0xfc070000).l,D0
 move.l D0,(0x4b58404c).l
 moveq -65,D0
 move.b D0,(0xec094025).l
 moveq 0,D0
 move.b (0xec09400d).l,D0
 ori.l #0x40,D0
 move.b D0,(0xec09400d).l
 moveq -17,D0
 move.b D0,(0xec094024).l
 moveq 0,D0
 move.b (0xec09400c).l,D0
 ori.l #0x10,D0
 move.b D0,(0xec09400c).l
 moveq 0,D0
 move.b (0xec09404a).l,D0
 andi.l #0x3e,D0
 ori.l #1,D0
 move.b D0,(0xec09404a).l
 moveq 0,D0
 move.b D0,(0xec094049).l
 moveq -4,D0
 move.b D0,(0xec094048).l
 moveq 0,D0
 move.w (0xec09000e).l,D0
 ori.l #0x800,D0
 move.w D0,(0xec09000e).l
 move.l #0x10000000,D0
 move.l D0,(0xfc008000).l
 move.l #0x780,D0
 move.l D0,(0xfc008008).l
 move.l #0x10001,D0
 move.l D0,(0xfc008004).l
 clr.l (0xfc00800c).l
 move.l #0xfd80,D0
 move.l D0,(0xfc008014).l
 move.l #0x10001,D0
 move.l D0,(0xfc008010).l
 moveq 2,D0
 move.b D0,(0xec094064).l
 move.b D0,(0xec094065).l
 move.b D0,(0xec094066).l
 move.b D0,(0xfc04002d).l
 moveq 5,D0
 move.b D0,(0xec094067).l
 ; Shared SRAM can survive a main reboot. Never accept an old ready tag.
 clr.l (0x10000008).l
 clr.l (0x10000100).l
 clr.l (0x10000104).l
 moveq 0,D0
 move.b (0xec09404c).l,D0
 ori.l #0x0c,D0
 move.b D0,(0xec09404c).l
 move.l #@main_upload_irq,D0
 move.l D0,(0x40000254).l
 moveq 21,D0
 move.b D0,(0xfc04c01d).l
 moveq 1,D0
 move.b D0,(0xfc04c055).l
 moveq 85,D0
 move.b D0,(0xec094053).l
 moveq 14,D0
 move.b D0,(0xfc04002f).l
 move.l #0x38000000,D0
 move.l D0,(0xec03800c).l
 move.l #0x03000000,D0
 move.l D0,(0xec038030).l
 move.l #0x10c00,D0
 move.l D0,(0xec038000).l
 moveq 1,D0
 move.l D0,(@STATUS).l
 move.l #@S6,D0
 move.l D0,(0xfc0453a0).l
 clr.w D0
 move.w D0,(0xfc0453a4).l
 move.w D0,(0xfc0453b6).l
 moveq 1,D0
 move.w D0,(0xfc0453a6).l
 move.l D0,(0xfc0453a8).l
 move.l #-1504,D0
 move.l D0,(0xfc0453ac).l
 move.l #0xec038037,D0
 move.l D0,(0xfc0453b0).l
 clr.l (0xfc0453b8).l
 move.w #1504,D0
 move.w D0,(0xfc0453b4).l
 move.w D0,(0xfc0453bc).l
 moveq 10,D0
 move.w D0,(0xfc0453be).l
 moveq 29,D0
 move.b D0,(0xfc04401c).l
 move.b D0,(0xfc044018).l
 bra.w @main_poll_done
main_release:
 moveq 6,D0
 move.l D0,(@STATUS).l
 moveq 64,D0
 move.b D0,(0xec094019).l
 bra.w @main_poll_done
main_fail:
 move.l (@STATUS).l,D0
 move.l D0,(@FAIL_STAGE).l
 moveq 5,D0
 move.l D0,(@STATUS).l
main_failed:
 moveq 29,D0
 move.b D0,(0xfc04401a).l
 moveq -65,D0
 move.b D0,(0xec094025).l
main_poll_done:
 jsr @MACHINE_TICK
 movem.l (SP),{ D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 }
 lea (60,SP),SP
 jmp @OLD_FRAME
main_upload_irq:
 lea (-12,SP),SP
 movem.l { D0 D1 A0 },(SP)
 moveq 29,D0
 move.b D0,(0xfc04401c).l
 move.l (@STATUS).l,D0
 cmpi.l #6,D0
 bne.w @main_upload_done
 move.l (0xec038000).l,D0
 ori.l #0x400,D0
 move.l D0,(0xec038000).l
 move.l #@S7,D0
 move.l D0,(0xfc0453a0).l
 clr.l (0xfc0453b8).l
 clr.l (0xfc0453ac).l
 move.w #0x6000,D0
 move.w D0,(0xfc0453b4).l
 move.w D0,(0xfc0453bc).l
 clr.w D0
 move.w D0,(0xfc0453be).l
 moveq 2,D0
 move.l D0,(@STATUS).l
 moveq 29,D0
 move.b D0,(0xfc044018).l
main_upload_done:
 movem.l (SP),{ D0 D1 A0 }
 lea (12,SP),SP
 rte
main_audio:
 lea (-60,SP),SP
 movem.l { D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 },(SP)
 jsr @AUDIO_C
 movem.l (SP),{ D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 }
 lea (60,SP),SP
 lea (0x4199e444).l,A4
 rts

main_source:
 move.l D0,-(SP)
 move.l (0x8000122c).l,D0
 move.l D0,(0x4b584038).l
 move.l (SP)+,D0
 jmp (0x40075184).l
main_notify_irq:
 lea (-8,SP),SP
 movem.l { D0 D1 },(SP)
 moveq 16,D0
 move.b D0,(0xfc090006).l
 addq.l #1,(0x4b584048).l
 move.l (@STATUS).l,D0
 cmpi.l #4,D0
 bne.w @main_notify_done
 move.l (@SEQ).l,D0
 beq.w @main_notify_done
 cmp.l (0x10000104).l,D0
 bne.w @main_notify_done
 move.l (0xfc07000c).l,D0
 sub.l (0x4b58403c).l,D0
 move.l D0,(0x4b584040).l
 cmp.l (0x4b584044).l,D0
 bls.w @main_notify_done
 move.l D0,(0x4b584044).l
main_notify_done:
 movem.l (SP),{ D0 D1 }
 lea (8,SP),SP
 rte
