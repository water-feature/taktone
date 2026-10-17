; Four pattern-local macro engine. ColdFire ISA_C, no FPU/EMAC operations.
; AssembleBatch uses Ghidra syntax; @names are resolved by ghidra_assemble.py.

macro_pointer:
 move.l (@RAM_READY).l,D0
 cmpi.l #1,D0
 bne.w @pointer_none
 move.l (@HELD).l,D0
 bmi.w @pointer_none
 cmpi.l #3,D0
 bhi.w @pointer_none
 move.l (@PATTERN).l,D1
 bmi.w @pointer_none
 cmpi.l #127,D1
 bhi.w @pointer_none
 lsl.l #8,D0
 lsl.l #2,D0
 lsl.l #8,D1
 lsl.l #4,D1
 add.l D1,D0
 addi.l #@TABLE,D0
 rts
pointer_none:
 moveq 0,D0
 rts

; A0=scene. A record without an explicit edit marker owns no locks. Clear
; its unused bytes before learning/toggling; retain only a valid empty enable.
macro_prepare_scene:
 move.l (4,A0),D0
 cmpi.l #@SCENE_MAGIC,D0
 beq.w @prepare_done
 move.l (A0),D1
 cmpi.l #0x01000000,D1
 beq.w @prepare_empty
 moveq 0,D1
prepare_empty:
 addq.l #1,(@EDIT_SEQ).l
 movea.l A0,A1
 move.l #256,D0
prepare_word:
 clr.l (A1)+
 subq.l #1,D0
 bne.w @prepare_word
 move.l D1,(A0)
 addq.l #1,(@EDIT_SEQ).l
prepare_done:
 rts

sync_context:
 lea (-12,SP),SP
 movem.l { D2 D3 A2},(SP)
 movea.l (@PROJECT_GLOBAL).l,A2
 tst.l A2
 beq.w @sync_done
 tst.l (@PATTERN_GLOBAL).l
 beq.w @sync_done
 jsr 0x4006f40c
 cmpi.l #127,D0
 bhi.w @sync_done
 cmp.l (@PATTERN).l,D0
 beq.w @sync_track
 move.l D0,(@PATTERN).l
 moveq -1,D0
 move.l D0,(@HELD).l
 moveq 1,D0
 move.l D0,(@UI_DIRTY).l
 move.l D0,(@AUDIO_DIRTY).l
sync_track:
 pea (0x30,A2)
 jsr 0x4001d24e
 addq.l #4,SP
 move.l D0,(@TRACK).l
sync_done:
 movem.l (SP),{ D2 D3 A2}
 lea (12,SP),SP
 rts

macro_tick:
 move.l (4,SP),D0
 move.l D0,(@CTRL).l
 jsr @macro_storage_tick
 jsr @sync_context
 jsr @macro_rebuild_overlay
 tst.l (@UI_DIRTY).l
 beq.w @tick_stock
 movea.l (@CTRL).l,A0
 moveq 1,D0
 move.b D0,(0x20,A0)
 moveq 0,D0
 move.l D0,(@UI_DIRTY).l
tick_stock:
 jmp 0x400ca34c

macro_key:
 lea (-40,SP),SP
 movem.l { D2 D3 D4 D5 D6 D7 A2 A3 A4 A5},(SP)
 movea.l (48,SP),A2
 move.l (12,A2),D2
 move.l (16,A2),D3
 cmpi.l #1,D2
 beq.w @key_log
 cmpi.l #49,D2
 blt.w @key_log_done
 cmpi.l #52,D2
 bgt.w @key_log_done
key_log:
 move.l D2,D1
 swap D1
 or.l D3,D1
 moveq 1,D0
 jsr @macro_diag
key_log_done:
 cmpi.l #1,D2
 bne.w @key_macro_range
 moveq 0,D0
 btst.l #0,D3
 beq.w @key_func_store
 moveq 1,D0
key_func_store:
 move.l D0,(@FUNC).l
 bra.w @key_stock
key_macro_range:
 cmpi.l #9,D2
 beq.w @key_clip_copy
 cmpi.l #11,D2
 beq.w @key_clip_paste
 bra.w @key_play_range
key_clip_copy:
 moveq 0,D4
 bra.w @key_clip_event
key_clip_paste:
 moveq 1,D4
key_clip_event:
 move.l (@SCENE_TRANSPORT_MASK).l,D0
 btst.l D4,D0
 bne.w @key_clip_owned
 tst.l (@HELD).l
 bmi.w @key_stock
key_clip_owned:
 btst.l #0,D3
 beq.w @key_clip_release
 move.l (@SCENE_TRANSPORT_MASK).l,D0
 btst.l D4,D0
 bne.w @key_taken
 bset.l D4,D0
 move.l D0,(@SCENE_TRANSPORT_MASK).l
 jsr @macro_pointer
 tst.l D0
 beq.w @key_taken
 movea.l D0,A3
 tst.l D4
 bne.w @key_clip_apply
 movea.l A3,A0
 lea (@SCENE_CLIP).l,A1
 move.l #256,D1
key_clip_copy_word:
 move.l (A0)+,(A1)+
 subq.l #1,D1
 bne.w @key_clip_copy_word
 moveq 1,D0
 move.l D0,(@SCENE_CLIP_VALID).l
 bra.w @key_taken
key_clip_apply:
 tst.l (@SCENE_CLIP_VALID).l
 beq.w @key_taken
 lea (@SCENE_CLIP).l,A0
 movea.l A3,A1
 move.l #256,D1
 addq.l #1,(@EDIT_SEQ).l
key_clip_paste_word:
 move.l (A0)+,(A1)+
 subq.l #1,D1
 bne.w @key_clip_paste_word
 move.l A3,D0
 jsr @macro_row_dirty
 addq.l #1,(@EDIT_SEQ).l
 moveq 1,D0
 move.l D0,(@DIRTY).l
 bra.w @key_dirty
key_clip_release:
 move.l (@SCENE_TRANSPORT_MASK).l,D0
 bclr.l D4,D0
 move.l D0,(@SCENE_TRANSPORT_MASK).l
 bra.w @key_taken
key_play_range:
 cmpi.l #10,D2
 bne.w @key_encoder_range
 tst.l (@PLAY_CONSUMED).l
 bne.w @key_clear_play
 tst.l (@HELD).l
 bmi.w @key_stock
key_clear_play:
 btst.l #0,D3
 beq.w @key_clear_play_release
 tst.l (@PLAY_CONSUMED).l
 bne.w @key_taken
 moveq 1,D0
 move.l D0,(@PLAY_CONSUMED).l
 jsr @macro_pointer
 tst.l D0
 beq.w @key_taken
 movea.l D0,A0
 move.l #256,D1
 moveq 0,D0
 addq.l #1,(@EDIT_SEQ).l
key_clear_scene_word:
 move.l D0,(A0)+
 subq.l #1,D1
 bne.w @key_clear_scene_word
 move.l #@SCENE_MAGIC,D0
 move.l D0,(-1020,A0)
 addq.l #1,(@EDIT_SEQ).l
 jsr @macro_pointer
 jsr @macro_row_dirty
 moveq 1,D0
 move.l D0,(@DIRTY).l
 bra.w @key_dirty
key_clear_play_release:
 moveq 0,D0
 move.l D0,(@PLAY_CONSUMED).l
 bra.w @key_taken
key_encoder_range:
 ; Encoder pushes must reach the native page dispatch. The grid wrapper
 ; below receives the actual focused widget instead of a cached redraw.
 cmpi.l #40,D2
 blt.w @key_scene_range
 cmpi.l #47,D2
 bgt.w @key_scene_range
 bra.w @key_stock
key_scene_range:
 cmpi.l #49,D2
 blt.w @key_stock
 cmpi.l #52,D2
 bgt.w @key_stock
 move.l (@RAM_READY).l,D0
 cmpi.l #1,D0
 bne.w @key_taken
 move.l D2,D4
 subi.l #49,D4
 moveq 1,D5
 lsl.l D4,D5
 btst.l #0,D3
 beq.w @key_release
 move.l (@DOWN).l,D0
 and.l D5,D0
 bne.w @key_taken
 or.l D5,(@DOWN).l
 jsr @sync_context
 pea (1).w
 jsr 0x400d3774
 addq.l #4,SP
 tst.l D0
 bne.w @key_toggle
 tst.l (@HELD).l
 bpl.w @key_taken
 move.l D4,(@HELD).l
 move.l (@PATTERN_GLOBAL).l,D0
 move.l D0,(@HOLD_PATTERN_TOKEN).l
 jsr @macro_pointer
 tst.l D0
 beq.w @key_dirty
 movea.l D0,A0
 jsr @macro_prepare_scene
 bra.w @key_dirty
key_toggle:
 move.l (@PATTERN).l,D0
 bmi.w @key_taken
 cmpi.l #127,D0
 bhi.w @key_taken
 lsl.l #8,D0
 lsl.l #4,D0
 move.l D4,D1
 lsl.l #8,D1
 lsl.l #2,D1
 add.l D1,D0
 addi.l #@TABLE,D0
 movea.l D0,A0
 jsr @macro_prepare_scene
 moveq 0,D0
 move.b (A0),D0
 eori.l #1,D0
 addq.l #1,(@EDIT_SEQ).l
 move.b D0,(A0)
 move.l #@SCENE_MAGIC,D0
 move.l D0,(4,A0)
 move.l A0,D0
 jsr @macro_row_dirty
 addq.l #1,(@EDIT_SEQ).l
 moveq 1,D0
 move.l D0,(@DIRTY).l
 bra.w @key_dirty
key_release:
 not.l D5
 and.l D5,(@DOWN).l
 cmp.l (@HELD).l,D4
 bne.w @key_taken
 moveq -1,D0
 move.l D0,(@HELD).l
key_dirty:
 moveq 1,D0
 move.l D0,(@AUDIO_DIRTY).l
 jsr @macro_rebuild_overlay
 moveq 1,D0
 move.l D0,(@UI_DIRTY).l
key_taken:
 movem.l (SP),{ D2 D3 D4 D5 D6 D7 A2 A3 A4 A5}
 lea (40,SP),SP
 moveq 1,D0
 rts
key_stock:
 movem.l (SP),{ D2 D3 D4 D5 D6 D7 A2 A3 A4 A5}
 lea (40,SP),SP
 jmp 0x400084fe

; Native parameter-page key entry, reached through its normal UI dispatch.
macro_grid_key:
 pea (@grid_key_original).l
 bra.w @grid_key_common
macro_source_key:
 pea (@source_key_original).l
grid_key_common:
 lea (-40,SP),SP
 movem.l { D2 D3 D4 D5 D6 D7 A2 A3 A4 A5},(SP)
 movea.l (48,SP),A3
 movea.l (52,SP),A2
 move.l (12,A2),D2
 move.l (16,A2),D3
 tst.l (@HELD).l
 bmi.w @grid_key_stock
 cmpi.l #40,D2
 blt.w @grid_key_stock
 cmpi.l #47,D2
 bgt.w @grid_key_stock
 btst.l #0,D3
 beq.w @grid_key_taken
 btst.l #3,D3
 bne.w @grid_key_taken
 move.l D2,D0
 subi.l #40,D0
 move.l D0,-(SP)
 move.l A3,-(SP)
 movea.l (A3),A0
 movea.l (0x9c,A0),A0
 jsr (A0)
 addq.l #8,SP
 tst.l D0
 beq.w @grid_key_taken
 move.l D0,D4
 ; Resolve the grid's actual provider, not its display/value getter. Some
 ; native getter paths return values without entering our scene wrapper.
 pea (-1).w
 move.l D4,-(SP)
 move.l A3,-(SP)
 movea.l (A3),A0
 movea.l (0xa4,A0),A0
 jsr (A0)
 lea (12,SP),SP
 tst.l D0
 beq.w @grid_key_taken
 movea.l D0,A0
 move.l (A0),D0
 cmpi.l #0x4017eb58,D0
 bne.w @grid_key_taken
 move.l D4,-(SP)
 jsr 0x40078d80
 addq.l #4,SP
 tst.l D0
 bmi.w @grid_key_taken
 cmpi.l #52,D0
 bhi.w @grid_key_taken
 move.l D0,D4
 move.l (@TRACK).l,D0
 cmpi.l #7,D0
 bhi.w @grid_key_taken
 moveq 53,D1
 muls.l D1,D0
 add.l D0,D4
 jsr @macro_pointer
 tst.l D0
 beq.w @grid_key_taken
 movea.l D0,A3
 move.l (4,A3),D0
 cmpi.l #@SCENE_MAGIC,D0
 bne.w @grid_key_taken
 move.l D4,D0
 lsr.l #3,D0
 lea (8,A3),A0
 adda.l D0,A0
 moveq 7,D1
 and.l D4,D1
 addq.l #1,(@EDIT_SEQ).l
 bclr.b D1,(A0)
 lea (68,A3),A0
 moveq 0,D0
 move.w D0,(0,A0,D4*2)
 move.l A3,D0
 jsr @macro_row_dirty
 addq.l #1,(@EDIT_SEQ).l
 moveq 1,D0
 move.l D0,(@DIRTY).l
 jsr @macro_rebuild_overlay
 moveq 1,D0
 move.l D0,(@UI_DIRTY).l
grid_key_taken:
 movem.l (SP),{ D2 D3 D4 D5 D6 D7 A2 A3 A4 A5}
 lea (44,SP),SP
 moveq 1,D0
 rts
grid_key_stock:
 movem.l (SP),{ D2 D3 D4 D5 D6 D7 A2 A3 A4 A5}
 lea (40,SP),SP
 rts

grid_key_original:
 ; Displaced LINK A6,-80 and MOVEM D2-D7/A2-A5.
 lea (-4,SP),SP
 move.l A6,(SP)
 movea.l SP,A6
 lea (-80,SP),SP
 movem.l { D2 D3 D4 D5 D6 D7 A2 A3 A4 A5},(SP)
 jmp 0x4003307e
source_key_original:
 ; Displaced LINK A6,-52 and MOVEM D2-D7/A2-A4.
 lea (-4,SP),SP
 move.l A6,(SP)
 movea.l SP,A6
 lea (-52,SP),SP
 movem.l { D2 D3 D4 D5 D6 D7 A2 A3 A4},(SP)
 jmp 0x4003b27a

macro_encoder:
 lea (-8,SP),SP
 movem.l { D2 A2},(SP)
 jsr @sync_context
 movea.l (16,SP),A2
 tst.l (@HELD).l
 bmi.w @encoder_call
 move.l (12,A2),D0
 cmpi.l #9,D0
 beq.w @encoder_done
encoder_call:
 addq.l #1,(@ENC_DEPTH).l
 addq.l #1,(@UI_DEPTH).l
 move.l A2,-(SP)
 move.l (16,SP),-(SP)
 jsr 0x40008550
 addq.l #8,SP
 subq.l #1,(@UI_DEPTH).l
 subq.l #1,(@ENC_DEPTH).l
encoder_done:
 jsr @macro_rebuild_overlay
 movem.l (SP),{ D2 A2}
 lea (8,SP),SP
 rts

macro_draw:
 ; Native drawing skips clean frames. Keep the last drawn parameter grid
 ; until a real redraw replaces the page; otherwise push clearing loses it.
 movea.l (4,SP),A0
 tst.b (0x20,A0)
 beq.w @draw_keep_widget
 moveq 0,D0
 move.l D0,(@ACTIVE_WIDGET).l
draw_keep_widget:
 addq.l #1,(@UI_DEPTH).l
 move.l (8,SP),-(SP)
 move.l (8,SP),-(SP)
 jsr 0x400ca382
 addq.l #8,SP
 subq.l #1,(@UI_DEPTH).l
 rts

; The parameter grid owns the encoder -> parameter mapping. Retain only the
; grid drawn by the current UI frame; menus without a grid leave this zero.
macro_grid:
 move.l (4,SP),D0
 move.l D0,(@ACTIVE_WIDGET).l
 lea (-0x48,SP),SP
 movem.l { D2 D3 D4 D5 D6 D7 A2 A3 A4 A5 A6},(SP)
 jmp 0x4003180a

; Reuse the native parameter box renderer's inversion output. A held scene
; owns lock display, even when disabled. All other widgets use stock behavior.
macro_display:
 lea (-16,SP),SP
 movem.l { D2 D3 A2 A3},(SP)
 tst.l (@HELD).l
 bmi.w @display_stock
 movea.l (20,SP),A2
 movea.l (28,SP),A3
 moveq -1,D0
 move.l D0,(@QUERY_LOCK).l
 pea (-1).w
 move.l (28,SP),-(SP)
 move.l A2,-(SP)
 movea.l (A2),A0
 movea.l (0x54,A0),A0
 jsr (A0)
 lea (12,SP),SP
 move.l D0,D2
 move.l (@QUERY_LOCK).l,D0
 bmi.w @display_stock
 tst.l A3
 beq.w @display_done
 move.b D0,(A3)
display_done:
 move.l D2,D0
 movem.l (SP),{ D2 D3 A2 A3}
 lea (16,SP),SP
 rts
display_stock:
 movem.l (SP),{ D2 D3 A2 A3}
 lea (16,SP),SP
 jmp @display_original
display_original:
 lea (-0x28,SP),SP
 movem.l { D2 A2 A3},(SP)
 jmp 0x40031724

; Setter wrapper owns an edit before any stored sound or outgoing MIDI
; notification changes. Validity/range checks use the original firmware.
macro_set:
 lea (-40,SP),SP
 movem.l { D2 D3 D4 D5 D6 D7 A2 A3 A4 A5},(SP)
 tst.l (@ENC_DEPTH).l
 beq.w @set_stock
 jsr @macro_pointer
 tst.l D0
 beq.w @set_stock
 movea.l D0,A3
 movea.l (44,SP),A2
 move.l (48,SP),D2
 move.l (A2),D0
 cmpi.l #0x4017eb58,D0
 bne.w @set_invalid
set_domain:
 move.l (56,SP),D4
set_audio_domain:
 cmpi.l #7,D4
 bhi.w @set_invalid
set_map:
 move.l (48,SP),D2
 move.l (52,SP),D3
 move.l D2,-(SP)
 jsr 0x40078d80
 addq.l #4,SP
 move.l D0,D5
 bmi.w @set_invalid
 cmpi.l #52,D5
 bhi.w @set_invalid
 lea (-8,SP),SP
 lea (SP),A0
 move.l D2,-(SP)
 jsr 0x40078f0c
 addq.l #4,SP
 cmp.l (SP),D3
 bge.w @set_min_ok
 move.l (SP),D3
set_min_ok:
 cmp.l (4,SP),D3
 ble.w @set_max_ok
 move.l (4,SP),D3
set_max_ok:
 addq.l #8,SP
 movea.l (A2),A0
 movea.l (0x24,A0),A0
 move.l D3,-(SP)
 move.l D2,-(SP)
 move.l A2,-(SP)
 jsr (A0)
 lea (12,SP),SP
 tst.b D0
 beq.w @set_invalid
 moveq 53,D0
 muls.l D0,D4
 add.l D5,D4
 movea.l A3,A0
 jsr @macro_prepare_scene
 addq.l #1,(@EDIT_SEQ).l
 lea (68,A3),A0
 move.w D3,(0,A0,D4*2)
 move.l #@SCENE_MAGIC,D0
 move.l D0,(4,A3)
 move.l D4,D0
 lsr.l #3,D0
 lea (8,A3),A0
 adda.l D0,A0
 moveq 7,D1
 and.l D4,D1
 bset.b D1,(A0)
 move.l A3,D0
 jsr @macro_row_dirty
 addq.l #1,(@EDIT_SEQ).l
 moveq 1,D0
 move.l D0,(@DIRTY).l
 move.l D0,(@UI_DIRTY).l
 move.l D0,(@AUDIO_DIRTY).l
 move.l D3,D0
 ext.l D0
 bra.w @set_done
set_invalid:
 movea.l (A2),A0
 movea.l (0x28,A0),A0
 move.l D2,-(SP)
 move.l A2,-(SP)
 jsr (A0)
 addq.l #8,SP
set_done:
 movem.l (SP),{ D2 D3 D4 D5 D6 D7 A2 A3 A4 A5}
 lea (40,SP),SP
 rts
set_stock:
 movem.l (SP),{ D2 D3 D4 D5 D6 D7 A2 A3 A4 A5}
 lea (40,SP),SP
 jmp @set_original

; UI compiles an immutable sparse overlay only when a scene changes. The
; audio IRQ reads a published buffer and touches only actually locked fields.
; Two 2 KiB buffers fit below the native-header scratch; publish is one long.
macro_rebuild_overlay:
 tst.l (@AUDIO_DIRTY).l
 beq.w @overlay_clean
 lea (-40,SP),SP
 movem.l { D0 D1 D2 D3 D4 D5 A0 A1 A2 A3},(SP)
 moveq 0,D0
 move.l D0,(@AUDIO_DIRTY).l
 jsr @macro_pointer
 tst.l D0
 beq.w @overlay_off
 movea.l D0,A3
 move.l (4,A3),D0
 cmpi.l #@SCENE_MAGIC,D0
 bne.w @overlay_off
 moveq 0,D0
 move.b (A3),D0
 andi.l #1,D0
 beq.w @overlay_off
 lea (@AUDIO_A).l,A2
 move.l (@AUDIO_PTR).l,D0
 cmpi.l #@AUDIO_A,D0
 bne.w @overlay_buffer
 lea (@AUDIO_B).l,A2
overlay_buffer:
 move.l (@PATTERN_GLOBAL).l,D0
 move.l D0,(4,A2)
 move.l (@PATTERN).l,D0
 move.l D0,(8,A2)
 move.l A3,(12,A2)
 lea (8,A3),A0
 lea (68,A3),A1
 lea (16,A2),A3
 moveq 0,D2
 moveq 18,D4
 moveq 60,D5
overlay_byte:
 moveq 0,D3
 move.b (A0)+,D3
 beq.w @overlay_skip
 moveq 8,D1
 cmpi.l #1,D5
 bne.w @overlay_bit
 moveq 5,D1
overlay_bit:
 btst.l #0,D3
 beq.w @overlay_next_bit
 move.w D4,(A3)+
 move.w (A1),(A3)+
 addq.l #1,D2
overlay_next_bit:
 addq.l #2,A1
 addq.l #2,D4
 lsr.l #1,D3
 subq.l #1,D1
 bne.w @overlay_bit
 bra.w @overlay_next_byte
overlay_skip:
 lea (16,A1),A1
 addi.l #16,D4
overlay_next_byte:
 subq.l #1,D5
 bne.w @overlay_byte
 tst.l D2
 beq.w @overlay_off
 jsr @macro_pointer
 cmp.l (12,A2),D0
 bne.w @overlay_off
 move.l D2,(A2)
 move.l A2,(@AUDIO_PTR).l
 bra.w @overlay_done
overlay_off:
 moveq 0,D0
 move.l D0,(@AUDIO_PTR).l
overlay_done:
 movem.l (SP),{ D0 D1 D2 D3 D4 D5 A0 A1 A2 A3}
 lea (40,SP),SP
overlay_clean:
 rts

 ; Scene targets enter the native smoother's INPUT. Restore the original
; source after the call, leaving its native sequencer/base values intact.
; Only the audio IRQ owns AUDIO_RESTORE and the smoothing state.
macro_render:
 lea (-24,SP),SP
 movem.l { D2 D3 D4 A2 A3 A4},(SP)
 movea.l (28,SP),A3
 suba.l A2,A2
 moveq 0,D3
 tst.l (@HELD).l
 bmi.w @render_native
 move.l (@AUDIO_PTR).l,D0
 beq.w @render_native
 movea.l D0,A2
 move.l (@PATTERN_GLOBAL).l,D0
 cmp.l (4,A2),D0
 bne.w @render_no_overlay
 movea.l D0,A0
 adda.l #0x1ec64,A0
 move.l (A0),D0
 cmp.l (8,A2),D0
 bne.w @render_no_overlay
 move.l (A2),D3
 move.l D3,D4
 lea (16,A2),A2
 lea (@AUDIO_RESTORE).l,A4
 movea.l A2,A0
render_input:
 move.l (A0)+,D0
 move.l D0,D1
 swap D0
 andi.l #0xffff,D0
 move.w (0,A3,D0*1),(A4)+
 move.w D1,(0,A3,D0*1)
 subq.l #1,D4
 bne.w @render_input
 bra.w @render_native
render_no_overlay:
 moveq 0,D3
render_native:
 move.l A3,-(SP)
 jsr 0x40074b9e
 addq.l #4,SP
 move.l D0,D2
 tst.l D3
 beq.w @render_done
 lea (@AUDIO_RESTORE).l,A4
render_restore:
 move.l (A2)+,D0
 swap D0
 andi.l #0xffff,D0
 move.w (A4)+,(0,A3,D0*1)
 subq.l #1,D3
 bne.w @render_restore
render_done:
 move.l D2,D0
 movem.l (SP),{ D2 D3 D4 A2 A3 A4}
 lea (24,SP),SP
 rts

macro_frame:
 lea (-24,SP),SP
 movem.l { D2 D3 D4 A2 A3 A4},(SP)
 tst.b (@LED_INIT).l
 beq.w @frame_done
 move.l (@PATTERN).l,D0
 bmi.w @frame_done
 cmpi.l #127,D0
 bhi.w @frame_done
 lsl.l #8,D0
 lsl.l #4,D0
 addi.l #@TABLE,D0
 movea.l D0,A2
 moveq 0,D2
 lea (@LED_CACHE).l,A3
 lea (@LED_PACKET).l,A4
frame_macro:
 moveq 0,D3
 moveq 0,D0
 move.b (A2),D0
 andi.l #1,D0
 beq.w @frame_colour
 moveq 9,D3
frame_colour:
 cmp.b (0,A3,D2*1),D3
 beq.w @frame_next
 move.b D3,(0,A3,D2*1)
 move.l D2,D0
 addi.l #46,D0
 move.b D0,(1,A4)
 move.b D0,(4,A4)
 move.b D0,(7,A4)
 move.b D0,(10,A4)
 move.b D3,(2,A4)
 move.b D3,(5,A4)
 move.b D3,(8,A4)
 move.b D3,(11,A4)
 move.l A4,-(SP)
 pea (12).w
 jsr 0x400024c0
 addq.l #8,SP
 ; Explicitly select slot zero, preserving the neighbouring physical LEDs.
 ; In particular, the stock DT never emits the DN T3/T4 selector group.
 move.l D2,D0
 addi.l #46,D0
 move.l D0,D1
 andi.l #3,D1
 lsl.l #1,D1
 moveq 3,D4
 lsl.l D1,D4
 not.l D4
 lsr.l #2,D0
 lea (@SELECTOR_STATE).l,A0
 moveq 0,D1
 move.b (0,A0,D0*1),D1
 and.l D4,D1
 move.b D1,(0,A0,D0*1)
 lea (@LED_SELECTOR_PACKET).l,A1
 addi.l #0x20,D0
 move.b D0,(A1)
 move.b D1,(1,A1)
 move.l A1,-(SP)
 pea (2).w
 jsr 0x400024c0
 addq.l #8,SP
frame_next:
 lea (1024,A2),A2
 addq.l #1,D2
 cmpi.l #4,D2
 bne.w @frame_macro
frame_done:
 movem.l (SP),{ D2 D3 D4 A2 A3 A4}
 lea (24,SP),SP
 jmp @OLD_FRAME

; This source is extended with generated UI getters and verified displaced
; stock instructions by macro_runtime.py.

; Keep zero-filled macro RAM out of the packed OS stream. Expanding that data
; in-place at startup would otherwise overtake the unread firmware stream.
macro_startup_clear:
 lea (-16,SP),SP
 movem.l { D0 D1 A0 A1},(SP)
 lea (@TABLE).l,A0
 move.l #0xcc000,D1
 moveq 0,D0
startup_clear_word:
 move.l D0,(A0)+
 subq.l #1,D1
 bne.w @startup_clear_word
 lea (@AUDIO_A).l,A0
 move.l #0x1f00,D1
startup_clear_aux:
 move.l D0,(A0)+
 subq.l #1,D1
 bne.w @startup_clear_aux
 lea (@TABLE).l,A0
 move.l #512,D1
 jsr @macro_enable_empty_scenes
 move.l #@GUARD_MAGIC,D0
 move.l D0,(@GUARD_LOW).l
 move.l D0,(@GUARD_HIGH).l
 moveq 1,D0
 move.l D0,(@RAM_READY).l
 movem.l (SP),{ D0 D1 A0 A1}
 lea (16,SP),SP
 jmp 0x40001c94

; Stock startup zeros static RAM on both sides of the reserved buddy extent.
; Retain the stock clobber contract (A0/D1); preserve D4-D7 and the stack.
macro_bss_clear:
 lea (-16,SP),SP
 movem.l { D4 D5 D6 D7},(SP)
 moveq 0,D4
 moveq 0,D5
 moveq 0,D6
 moveq 0,D7
 lea (0x40252000).l,A0
bss_low:
 movem.l { D4 D5 D6 D7},(A0)
 lea (16,A0),A0
 cmpa.l #@RESERVE_START,A0
 bne.w @bss_low
 lea (@RESERVE_END).l,A0
bss_high:
 movem.l { D4 D5 D6 D7},(A0)
 lea (16,A0),A0
 cmpa.l #0x439d0000,A0
 bne.w @bss_high
 moveq 0,D1
 movem.l (SP),{ D4 D5 D6 D7}
 lea (16,SP),SP
 rts

; Bounded diagnostic ring: sequence, kind, value, project identity. Preserve
; all inputs. Mask IRQs only for the four stores and cursor publication.
macro_diag:
 lea (-24,SP),SP
 movem.l { D0 D1 D2 D3 A0 A1},(SP)
 move SR,D3w
 move #0x2700,SR
 move.l (@DIAG_SEQ).l,D2
 move.l D2,D0
 andi.l #255,D0
 lsl.l #4,D0
 lea (@DIAG_RING).l,A0
 adda.l D0,A0
 move.l D2,(A0)+
 move.l (SP),(A0)+
 move.l D1,(A0)+
 move.l (@PROJECT_ID).l,(A0)
 addq.l #1,D2
 move.l D2,(@DIAG_SEQ).l
 move D3w,SR
 movem.l (SP),{ D0 D1 D2 D3 A0 A1}
 lea (24,SP),SP
 rts

; D0=live scene/row address. Record edits per pattern so an explicit successful
; checkpoint read can fill unknown rows without replacing locally edited rows.
; Preserve every input, including D0 and the working address registers.
macro_row_dirty:
 lea (-12,SP),SP
 movem.l { D0 D1 A0},(SP)
 subi.l #@TABLE,D0
 cmpi.l #0x80000,D0
 bcc.w @row_dirty_done
 lsr.l #8,D0
 lsr.l #4,D0
 move.l D0,D1
 lsr.l #3,D0
 lea (@ROW_DIRTY_MAP).l,A0
 adda.l D0,A0
 andi.l #7,D1
 bset.b D1,(A0)
row_dirty_done:
 movem.l (SP),{ D0 D1 A0}
 lea (12,SP),SP
 rts
