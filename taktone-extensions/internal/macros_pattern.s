; D0=raw pattern pointer -> D0=macro pattern pointer, or zero.
macro_pattern_pointer:
 move.l (@RAM_READY).l,D1
 cmpi.l #1,D1
 bne.w @pattern_pointer_none
 movea.l (@PROJECT_GLOBAL).l,A0
 tst.l A0
 beq.w @pattern_pointer_none
 movea.l (16,A0),A0
 tst.l A0
 beq.w @pattern_pointer_none
 lea (28,A0),A0
 moveq 0,D1
pattern_pointer_scan:
 cmp.l A0,D0
 beq.w @pattern_pointer_found
 adda.l #0x1ec68,A0
 addq.l #1,D1
 cmpi.l #128,D1
 bne.w @pattern_pointer_scan
pattern_pointer_none:
 moveq 0,D0
 rts
pattern_pointer_found:
 move.l D1,D0
 lsl.l #8,D0
 lsl.l #4,D0
 addi.l #@TABLE,D0
 rts

; D0=raw clipboard data address; return corresponding macro clipboard or 0.
macro_clip_find:
 lea (@CLIP_META).l,A0
 moveq 0,D1
clip_scan:
 cmp.l (A0)+,D0
 beq.w @clip_found
 addq.l #1,D1
 cmpi.l #4,D1
 bne.w @clip_scan
 moveq 0,D0
 rts
clip_found:
 move.l D1,D0
 lsl.l #8,D0
 lsl.l #4,D0
 addi.l #@CLIP_TABLE,D0
 rts

macro_pattern_memcpy:
 lea (-24,SP),SP
 movem.l { D2 D3 D4 D5 A2 A3},(SP)
 move.l (28,SP),D2
 move.l (32,SP),D3
 move.l (36,SP),D4
 move.l D4,-(SP)
 move.l D3,-(SP)
 move.l D2,-(SP)
 jsr 0x400e88c0
 lea (12,SP),SP
 move.l D0,D5
 cmpi.l #0xfc154c,D4
 bne.w @pattern_memcpy_short
 movea.l (@PROJECT_GLOBAL).l,A0
 tst.l A0
 beq.w @pattern_memcpy_done
 cmp.l (16,A0),D2
 bne.w @pattern_memcpy_done
 cmp.l (@PENDING_OWNER).l,D3
 bne.w @pattern_memcpy_done
 move.l D2,(@PENDING_OWNER).l
 bra.w @pattern_memcpy_done
pattern_memcpy_short:
 cmpi.l #0x1ec68,D4
 bne.w @pattern_memcpy_done
 move.l D3,D0
 jsr @macro_pattern_pointer
 movea.l D0,A2
 tst.l D0
 bne.w @pattern_memcpy_source
 move.l D3,D0
 jsr @macro_clip_find
 movea.l D0,A2
pattern_memcpy_source:
 ; Unrecognised raw sources are native cache/refresh copies, not a request
 ; to erase scene data. Explicit reload/clear hooks own those operations.
 tst.l A2
 beq.w @pattern_memcpy_done
 move.l D2,D0
 jsr @macro_pattern_pointer
 movea.l D0,A3
 tst.l D0
 bne.w @pattern_memcpy_destination
 ; Copies out of a live pattern populate an independent clipboard slot.
 tst.l A2
 beq.w @pattern_memcpy_done
 move.l D2,D0
 jsr @macro_clip_find
 tst.l D0
 bne.w @pattern_memcpy_clip_known
 move.l (@CLIP_NEXT).l,D1
 andi.l #3,D1
 lea (@CLIP_META).l,A0
 move.l D2,(0,A0,D1*4)
 move.l D1,D0
 addq.l #1,D1
 move.l D1,(@CLIP_NEXT).l
 lsl.l #8,D0
 lsl.l #4,D0
 addi.l #@CLIP_TABLE,D0
pattern_memcpy_clip_known:
 movea.l D0,A3
 bra.w @pattern_memcpy_copy
pattern_memcpy_destination:
 move.l A3,D0
 jsr @macro_row_dirty
 moveq -1,D0
 move.l D0,(@HELD).l
 moveq 1,D0
 move.l D0,(@DIRTY).l
 move.l D0,(@UI_DIRTY).l
 move.l D0,(@AUDIO_DIRTY).l
pattern_memcpy_copy:
 addq.l #1,(@EDIT_SEQ).l
 move.l #1024,D1
 tst.l A2
 beq.w @pattern_memcpy_zero
pattern_memcpy_word:
 move.l (A2)+,(A3)+
 subq.l #1,D1
 bne.w @pattern_memcpy_word
 addq.l #1,(@EDIT_SEQ).l
 bra.w @pattern_memcpy_done
pattern_memcpy_zero:
 moveq 0,D0
pattern_memcpy_zero_word:
 move.l D0,(A3)+
 subq.l #1,D1
 bne.w @pattern_memcpy_zero_word
 lea (-4096,A3),A0
 moveq 4,D1
 jsr @macro_enable_empty_scenes
 addq.l #1,(@EDIT_SEQ).l
pattern_memcpy_done:
 move.l D5,D0
 movem.l (SP),{ D2 D3 D4 D5 A2 A3}
 lea (24,SP),SP
 rts

macro_pattern_clear:
 lea (-12,SP),SP
 movem.l { D2 D3 A2},(SP)
 move.l (16,SP),D2
 move.l (20,SP),-(SP)
 move.l D2,-(SP)
 jsr @pattern_clear_original
 addq.l #8,SP
 move.l D0,D3
 move.l D2,D0
 jsr @macro_pattern_pointer
 tst.l D0
 beq.w @pattern_clear_done
 jsr @macro_row_dirty
 movea.l D0,A0
 moveq 0,D0
 move.l #1024,D1
 addq.l #1,(@EDIT_SEQ).l
pattern_clear_word:
 move.l D0,(A0)+
 subq.l #1,D1
 bne.w @pattern_clear_word
 lea (-4096,A0),A0
 moveq 4,D1
 jsr @macro_enable_empty_scenes
 addq.l #1,(@EDIT_SEQ).l
 moveq -1,D0
 move.l D0,(@HELD).l
 moveq 1,D0
 move.l D0,(@DIRTY).l
 move.l D0,(@UI_DIRTY).l
 move.l D0,(@AUDIO_DIRTY).l
pattern_clear_done:
 move.l D3,D0
 movem.l (SP),{ D2 D3 A2}
 lea (12,SP),SP
 rts
pattern_clear_original:
 lea (-0x1c,SP),SP
 movem.l { D2 D3 D4 D5 D6 A2 A3},(SP)
 jmp 0x400849a8
