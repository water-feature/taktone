; Native partial saves must update the extension's native-data binding while
; saving only the corresponding pattern's macros. Keep live TABLE unchanged:
; a power-loss interrupt at any point must still see all unsaved edits.
macro_pattern_save:
 moveq 1,D1
 bra.w @partial_save
macro_kit_save:
 moveq 0,D1
 bra.w @partial_save
macro_pattern_reload:
 moveq 2,D1
partial_save:
 lea (-40,SP),SP
 movem.l { D2 D3 D4 D5 D6 D7 A2 A3},(SP)
 move.l D1,D7
 movea.l (44,SP),A3
 move.l (48,SP),D3
 move.l (52,SP),D4
 moveq 0,D6
 move.l (@RAM_READY).l,D0
 cmpi.l #1,D0
 bne.w @partial_passthrough
 move.l A3,D0
 cmp.l (@PROJECT_GLOBAL).l,D0
 bne.w @partial_passthrough
 cmpi.l #127,D4
 bhi.w @partial_passthrough
 tst.b D3
 bne.w @partial_temporary
 move.l A3,-(SP)
 jsr 0x400154be
 addq.l #4,SP
 tst.l D0
 bmi.w @partial_passthrough
 bra.w @partial_slot
partial_temporary:
 move.l #128,D0
partial_slot:
 jsr @macro_project_slot
 tst.l D0
 beq.w @partial_passthrough
 move.l D0,D5
 lea (32,SP),A0
 jsr @macro_io_lock
 move.l D5,D0
 move.l #@SAVED_TABLE,D2
 jsr @macro_load_buffer
 move.l (@LOAD_STATUS).l,D0
 cmpi.l #3,D0
 beq.w @partial_native
 cmpi.l #2,D0
 bne.w @partial_extension_ready
 lea (@SAVED_TABLE).l,A0
 move.l #0x20000,D1
 moveq 0,D0
partial_empty_word:
 move.l D0,(A0)+
 subq.l #1,D1
 bne.w @partial_empty_word
partial_extension_ready:
partial_native:
 move.l D4,-(SP)
 move.l D3,-(SP)
 move.l A3,-(SP)
 cmpi.l #2,D7
 beq.w @partial_native_reload
 tst.l D7
 beq.w @partial_native_kit
 jsr @pattern_save_original
 bra.w @partial_native_done
partial_native_kit:
 jsr @kit_save_original
 bra.w @partial_native_done
partial_native_reload:
 jsr @pattern_reload_original
partial_native_done:
 lea (12,SP),SP
 move.l D0,D6
 move.l D0,D1
 moveq 4,D0
 jsr @macro_diag
 move.l D6,D0
 tst.b D0
 beq.w @partial_release
 move.l (@LOAD_STATUS).l,D0
 cmpi.l #3,D0
 beq.w @partial_release
 jsr @macro_recover_checkpoint
 cmpi.l #2,D7
 beq.w @partial_restore_row
 move.l D4,D0
 lsl.l #8,D0
 lsl.l #4,D0
 lea (@TABLE).l,A0
 adda.l D0,A0
 lea (@SAVED_TABLE).l,A1
 adda.l D0,A1
 move.l #1024,D1
partial_copy_row:
 move.l (A0)+,(A1)+
 subq.l #1,D1
 bne.w @partial_copy_row
 move.l D5,D0
 moveq 0,D1
 move.l #@SAVED_TABLE,D2
 jsr @macro_store_buffer
 bra.w @partial_release
partial_restore_row:
 move.l (@LOAD_STATUS).l,D0
 cmpi.l #1,D0
 bne.w @partial_release
 moveq 0,D0
 move.l D0,(@AUDIO_PTR).l
 move.l D4,D0
 lsl.l #8,D0
 lsl.l #4,D0
 lea (@SAVED_TABLE).l,A0
 adda.l D0,A0
 lea (@TABLE).l,A1
 adda.l D0,A1
 move.l #1024,D1
 move.l A1,D0
 jsr @macro_row_dirty
 addq.l #1,(@EDIT_SEQ).l
partial_restore_word:
 move.l (A0)+,(A1)+
 subq.l #1,D1
 bne.w @partial_restore_word
 addq.l #1,(@EDIT_SEQ).l
 moveq -1,D0
 move.l D0,(@HELD).l
 moveq 1,D0
 move.l D0,(@UI_DIRTY).l
 move.l D0,(@AUDIO_DIRTY).l
partial_release:
 pea (32,SP)
 jsr 0x401385e6
 addq.l #4,SP
 move.l D6,D0
 movem.l (SP),{ D2 D3 D4 D5 D6 D7 A2 A3}
 lea (40,SP),SP
 rts
partial_passthrough:
 cmpi.l #2,D7
 beq.w @partial_passthrough_reload
 tst.l D7
 beq.w @partial_passthrough_kit
 movem.l (SP),{ D2 D3 D4 D5 D6 D7 A2 A3}
 lea (40,SP),SP
 jmp @pattern_save_original
partial_passthrough_kit:
 movem.l (SP),{ D2 D3 D4 D5 D6 D7 A2 A3}
 lea (40,SP),SP
 jmp @kit_save_original
pattern_save_original:
 lea (-0x14,SP),SP
 movem.l { D2 D3 D4 A2 A3},(SP)
 jmp 0x400165b4
kit_save_original:
 lea (-0x18,SP),SP
 movem.l { D2 D3 D4 D5 A2 A3},(SP)
 jmp 0x400166a2

partial_passthrough_reload:
 movem.l (SP),{ D2 D3 D4 D5 D6 D7 A2 A3}
 lea (40,SP),SP
 jmp @pattern_reload_original
pattern_reload_original:
 lea (-0x18,SP),SP
 movem.l { D2 D3 D4 A2 A3},(SP)
 jmp 0x400162a8

; Only an explicit partial operation may recover a failed FIRST-BOOT read.
; SAVED_TABLE is validated (status 1), or absent (status 2). Keep every locally
; edited pattern, including an intentional all-zero scene clear. Other rows
; gain their saved baseline before whole-project persistence is re-enabled.
macro_recover_checkpoint:
 lea (-24,SP),SP
 movem.l { D2 D3 D4 A2 A3 A4},(SP)
 move.l (@INITIALIZED).l,D0
 cmpi.l #1,D0
 beq.w @recover_done
 move.l (@RAM_READY).l,D0
 cmpi.l #1,D0
 bne.w @recover_done
 move.l (@LOAD_STATUS).l,D0
 cmpi.l #3,D0
 beq.w @recover_done
 moveq -1,D0
 move.l D0,(@HELD).l
 moveq 0,D0
 move.l D0,(@AUDIO_PTR).l
 addq.l #1,(@EDIT_SEQ).l
 lea (@TABLE).l,A2
 lea (@SAVED_TABLE).l,A3
 lea (@ROW_DIRTY_MAP).l,A4
 moveq 0,D2
recover_row:
 move.l D2,D0
 lsr.l #3,D0
 moveq 0,D3
 move.b (0,A4,D0*1),D3
 move.l D2,D0
 andi.l #7,D0
 btst.l D0,D3
 bne.w @recover_next
 movea.l A2,A0
 movea.l A3,A1
 move.l #1024,D1
recover_word:
 move.l (A1)+,(A0)+
 subq.l #1,D1
 bne.w @recover_word
recover_next:
 lea (4096,A2),A2
 lea (4096,A3),A3
 addq.l #1,D2
 cmpi.l #128,D2
 bne.w @recover_row
 addq.l #1,(@EDIT_SEQ).l
 moveq 1,D0
 move.l D0,(@INITIALIZED).l
 move.l D0,(@UI_DIRTY).l
 move.l D0,(@AUDIO_DIRTY).l
recover_done:
 movem.l (SP),{ D2 D3 D4 A2 A3 A4}
 lea (24,SP),SP
 rts
