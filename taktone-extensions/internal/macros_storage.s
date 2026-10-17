; Fixed project-slot extension. Native payload occupies chunks 0..110.
; Chunk 111: versioned commit header. Chunks 112..127: 512 KiB macros.
; Native COKI header binds this extension to the exact native save image.

macro_checksum:
 lea (@TABLE).l,A0
 bra.w @checksum_start
macro_checksum_buffer:
 movea.l A4,A0
checksum_start:
 move.l #0x20000,D1
 move.l #0x811c9dc5,D0
checksum_word:
 move.l (A0)+,D2
 eor.l D2,D0
 move.l #0x01000193,D2
 mulu.l D2,D0
 subq.l #1,D1
 bne.w @checksum_word
 rts

macro_clear_table:
 movea.l A4,A0
 move.l #0x20000,D1
 moveq 0,D0
clear_table_word:
 move.l D0,(A0)+
 subq.l #1,D1
 bne.w @clear_table_word
 rts

macro_project_slot:
 cmpi.l #128,D0
 bhi.w @project_slot_bad
 beq.w @project_slot_temporary
 lsl.l #8,D0
 lsl.l #5,D0
 addi.l #0x80000,D0
 rts
project_slot_temporary:
 move.l #0x7e000,D0
 rts
project_slot_bad:
 moveq 0,D0
 rts

; D0=physical slot base, D1=1 for polling shutdown writer, else RTOS writer.
macro_store:
 lea (-36,SP),SP
 movem.l { D2 D3 D4 D5 A2 A3 A4},(SP)
 lea (@TABLE).l,A4
 bra.w @store_common
macro_store_buffer:
 lea (-36,SP),SP
 movem.l { D2 D3 D4 D5 A2 A3 A4},(SP)
 movea.l D2,A4
store_common:
 move.l D0,D3
 move.l D1,D4
 tst.l D4
 bne.w @store_guard_ready
 lea (28,SP),A0
 jsr @macro_io_lock
store_guard_ready:
 ; Snapshot live edits before performing normal I/O. An odd/changing edit
 ; sequence rejects the store before any chunk is written. No long IRQ mask.
 tst.l D4
 bne.w @store_snapshot_ready
 move.l A4,D0
 cmpi.l #@TABLE,D0
 bne.w @store_snapshot_ready
 move.l (@EDIT_SEQ).l,D5
 btst.l #0,D5
 bne.w @store_error
 movea.l A4,A0
 lea (@STAGING).l,A1
 move.l #0x20000,D1
store_snapshot_word:
 move.l (A0)+,(A1)+
 subq.l #1,D1
 bne.w @store_snapshot_word
 cmp.l (@EDIT_SEQ).l,D5
 bne.w @store_error
 lea (@STAGING).l,A4
store_snapshot_ready:
 lea (@HEADER).l,A2
 tst.l D4
 beq.w @store_header_selected
 lea (@SHUT_HEADER).l,A2
store_header_selected:
 movea.l A2,A0
 move.l #8192,D1
 moveq 0,D0
store_clear_header:
 move.l D0,(A0)+
 subq.l #1,D1
 bne.w @store_clear_header
 tst.l D4
 bne.w @store_poll_header
 pea (@NATIVE_HEADER).l
 pea (512).w
 move.l D3,-(SP)
 jsr 0x400e29ec
 lea (12,SP),SP
 move.l D0,D1
 moveq 6,D0
 jsr @macro_diag
 move.l D1,D0
 tst.l D0
 bne.w @store_error
 lea (@NATIVE_HEADER).l,A0
 bra.w @store_copy_header
store_poll_header:
 lea (0x406480e8).l,A0
store_copy_header:
 lea (0x100,A2),A1
 moveq 68,D1
store_copy_word:
 move.l (A0)+,(A1)+
 subq.l #1,D1
 bne.w @store_copy_word
 moveq 0,D0
 move.l D0,(24,A2)
 move.l D0,(28,A2)
 jsr @macro_checksum_buffer
 move.l D0,(12,A2)
 not.l D0
 move.l D0,(16,A2)
 move.l #0x584d4143,D0
 move.l D0,(A2)
 moveq 4,D0
 move.l D0,(4,A2)
 move.l #0x80000,D0
 move.l D0,(8,A2)
 move.l (@PROJECT_ID).l,D0
 move.l D0,(20,A2)
 lea (@PACK).l,A3
 tst.l D4
 beq.w @store_pack_selected
 lea (@SHUT_PACK).l,A3
store_pack_selected:
 jsr @macro_pack
 move.l D3,D5
 addi.l #0x1c00,D5
 move.l (52,A2),D2
 beq.w @store_commit
store_chunk:
 move.l A3,-(SP)
 tst.l D4
 bne.w @store_poll_chunk
 pea (0x8000).l
 move.l D5,-(SP)
 jsr 0x400e2bd2
 lea (12,SP),SP
 move.l D0,D1
 moveq 7,D0
 jsr @macro_diag
 move.l D1,D0
 tst.l D0
 bne.w @store_error
 bra.w @store_chunk_next
store_poll_chunk:
 move.l D5,-(SP)
 jsr 0x4008d5a0
 addq.l #8,SP
store_chunk_next:
 adda.l #0x8000,A3
 addi.l #64,D5
 subq.l #1,D2
 bne.w @store_chunk
store_commit:
 ; Commit the header only after the complete table has reached storage.
 move.l A2,-(SP)
 addi.l #0x1bc0,D3
 tst.l D4
 bne.w @store_poll_commit
 pea (0x8000).l
 move.l D3,-(SP)
 jsr 0x400e2bd2
 lea (12,SP),SP
 move.l D0,D1
 moveq 7,D0
 jsr @macro_diag
 move.l D1,D0
 tst.l D0
 bne.w @store_error
 bra.w @store_success
store_poll_commit:
 move.l D3,-(SP)
 jsr 0x4008d5a0
 addq.l #8,SP
store_success:
 moveq 0,D0
 move.l D0,(@ERROR).l
 bra.w @store_done
store_error:
 moveq 1,D0
 move.l D0,(@ERROR).l
store_done:
 move.l D0,D1
 moveq 5,D0
 jsr @macro_diag
 move.l D1,D0
 move.l D0,D2
 tst.l D4
 bne.w @store_guard_released
 pea (28,SP)
 jsr 0x401385e6
 addq.l #4,SP
store_guard_released:
 move.l D2,D0
 movem.l (SP),{ D2 D3 D4 D5 A2 A3 A4}
 lea (36,SP),SP
 rts

 ; All reads validate in STAGING. Publish only a complete valid image.
; LOAD_STATUS: 1 valid/published, 2 absent/foreign, 3 read/corruption failure.
macro_load:
 lea (-36,SP),SP
 movem.l { D2 D3 D4 D5 A2 A3 A4},(SP)
 move.l #@TABLE,D5
 bra.w @load_setup
macro_load_buffer:
 lea (-36,SP),SP
 movem.l { D2 D3 D4 D5 A2 A3 A4},(SP)
 move.l D2,D5
load_setup:
 move.l D0,D3
 move.l (36,SP),D1
 moveq 3,D0
 jsr @macro_diag
 lea (@STAGING).l,A4
load_common:
 lea (28,SP),A0
 jsr @macro_io_lock
 moveq 3,D0
 move.l D0,(@LOAD_STATUS).l
 moveq 1,D0
 move.l D0,(@LOAD_REASON).l
 jsr @macro_clear_table
 pea (@HEADER).l
 pea (0x8000).l
 move.l D3,D0
 addi.l #0x1bc0,D0
 move.l D0,-(SP)
 jsr 0x400e29ec
 lea (12,SP),SP
 move.l D0,D1
 moveq 6,D0
 jsr @macro_diag
 move.l D1,D0
 tst.l D0
 bne.w @load_error
 lea (@HEADER).l,A2
 move.l (A2),D0
 cmpi.l #0x584d4143,D0
 bne.w @load_magic_absent
 move.l (4,A2),D0
 cmpi.l #4,D0
 beq.w @load_schema_ok
 cmpi.l #3,D0
 bne.w @load_schema_absent
load_schema_ok:
 moveq 6,D0
 move.l D0,(@LOAD_REASON).l
 move.l (8,A2),D0
 cmpi.l #0x80000,D0
 bne.w @load_empty
 move.l (12,A2),D0
 not.l D0
 cmp.l (16,A2),D0
 bne.w @load_error
 move.l (20,A2),D0
 cmp.l (@PROJECT_ID).l,D0
 beq.w @load_native_bound
 ; A known Save As UUID edge may leave the temporary checkpoint under its
 ; predecessor. Only partial operations on that same temporary slot accept it.
 cmpi.l #@SAVED_TABLE,D5
 bne.w @load_owner_absent
 cmpi.l #0x7e000,D3
 bne.w @load_owner_absent
 cmp.l (@PREVIOUS_ID).l,D0
 bne.w @load_owner_absent
load_native_bound:
 moveq 6,D0
 move.l D0,(@LOAD_REASON).l
 addi.l #0x1c00,D3
 lea (@PACK).l,A3
 move.l (52,A2),D4
 cmpi.l #16,D4
 bhi.w @load_error
 tst.l D4
 beq.w @load_unpack
load_chunk:
 move.l A3,-(SP)
 pea (0x8000).l
 move.l D3,-(SP)
 jsr 0x400e29ec
 lea (12,SP),SP
 move.l D0,D1
 moveq 6,D0
 jsr @macro_diag
 move.l D1,D0
 tst.l D0
 bne.w @load_error
 adda.l #0x8000,A3
 addi.l #64,D3
 subq.l #1,D4
 bne.w @load_chunk
load_unpack:
 jsr @macro_unpack_rows
 tst.l D0
 bne.w @load_error
 jsr @macro_validate_table
 tst.l D0
 bne.w @load_error
 moveq 7,D0
 move.l D0,(@LOAD_REASON).l
 jsr @macro_checksum_buffer
 cmp.l (12,A2),D0
 bne.w @load_error
 ; Publication is explicit here, after all structural/checksum checks.
 cmpi.l #@TABLE,D5
 bne.w @load_publish_ready
 moveq -1,D0
 move.l D0,(@HELD).l
 moveq 0,D0
 move.l D0,(@AUDIO_PTR).l
load_publish_ready:
 addq.l #1,(@EDIT_SEQ).l
 movea.l A4,A0
 movea.l D5,A1
 move.l #0x20000,D1
load_publish:
 move.l (A0)+,(A1)+
 subq.l #1,D1
 bne.w @load_publish
 addq.l #1,(@EDIT_SEQ).l
 moveq 1,D0
 move.l D0,(@LOAD_STATUS).l
 cmpi.l #@TABLE,D5
 bne.w @load_success
 moveq -1,D0
 move.l D0,(@HELD).l
 moveq 0,D0
 move.l D0,(@DIRTY).l
 lea (@ROW_DIRTY_MAP).l,A0
 move.l D0,(A0)+
 move.l D0,(A0)+
 move.l D0,(A0)+
 move.l D0,(A0)
 moveq 1,D0
 move.l D0,(@UI_DIRTY).l
 move.l D0,(@AUDIO_DIRTY).l
load_success:
 moveq 0,D0
 move.l D0,(@LOAD_REASON).l
 move.l D0,(@ERROR).l
 bra.w @load_done
load_magic_absent:
 moveq 3,D0
 bra.w @load_absent_reason
load_schema_absent:
 moveq 4,D0
 bra.w @load_absent_reason
load_owner_absent:
 moveq 5,D0
load_absent_reason:
 move.l D0,(@LOAD_REASON).l
load_empty:
 moveq 2,D0
 move.l D0,(@LOAD_STATUS).l
 moveq 0,D0
 move.l D0,(@ERROR).l
 bra.w @load_done
load_error:
 moveq 1,D0
 move.l D0,(@ERROR).l
load_done:
 moveq 9,D0
 move.l (@LOAD_REASON).l,D1
 jsr @macro_diag
 moveq 2,D0
 move.l (@LOAD_STATUS).l,D1
 jsr @macro_diag
 pea (28,SP)
 jsr 0x401385e6
 addq.l #4,SP
 movem.l (SP),{ D2 D3 D4 D5 A2 A3 A4}
 lea (36,SP),SP
 rts

; A saved bitmap is meaningful only in a record explicitly created by an
; encoder edit. Reject semantically invalid images even with a matching CRC.
; A4 is the destination table; D0=0 valid, 1 invalid.
macro_validate_table:
 lea (-16,SP),SP
 movem.l { D2 D3 A2 A3},(SP)
 movea.l A4,A2
 move.l #512,D3
validate_scene:
 move.l (A2),D0
 beq.w @validate_marker
 cmpi.l #0x01000000,D0
 bne.w @validate_bad
validate_marker:
 move.l (4,A2),D0
 beq.w @validate_empty
 cmpi.l #@SCENE_MAGIC,D0
 bne.w @validate_bad
 moveq 0,D0
 move.b (67,A2),D0
 andi.l #0xe0,D0
 bne.w @validate_bad
 tst.w (1022,A2)
 bne.w @validate_bad
 bra.w @validate_next
validate_empty:
 lea (8,A2),A0
 move.l #254,D1
 moveq 0,D0
validate_empty_word:
 or.l (A0)+,D0
 subq.l #1,D1
 bne.w @validate_empty_word
 tst.l D0
 bne.w @validate_bad
validate_next:
 lea (1024,A2),A2
 subq.l #1,D3
 bne.w @validate_scene
 moveq 0,D0
 bra.w @validate_done
validate_bad:
 moveq 1,D0
validate_done:
 movem.l (SP),{ D2 D3 A2 A3}
 lea (16,SP),SP
 rts

; Called from UI tick, outside the OLED/UART mutex and outside audio IRQs.
macro_storage_tick:
 lea (-20,SP),SP
 movem.l { D2 D3 D4 A2 A4},(SP)
 move.l (@GUARD_LOW).l,D0
 cmpi.l #@GUARD_MAGIC,D0
 bne.w @storage_guard_failed
 move.l (@GUARD_HIGH).l,D0
 cmpi.l #@GUARD_MAGIC,D0
 bne.w @storage_guard_failed
 movea.l (@PROJECT_GLOBAL).l,A2
 tst.l A2
 beq.w @storage_tick_done
 movea.l (16,A2),A2
 tst.l A2
 beq.w @storage_tick_done
 move.l (8,A2),D2
 tst.l (@INITIALIZED).l
 beq.w @storage_tick_load
 move.l A2,D0
 cmp.l (@PENDING_OWNER).l,D0
 beq.w @storage_tick_load
 cmp.l (@PROJECT_ID).l,D2
 beq.w @storage_tick_done
 ; A native Save As can regenerate the project UUID without loading a
 ; different project. Keep its macros; real loads carry PENDING_OWNER.
 move.l (@PROJECT_ID).l,D0
 move.l D0,(@PREVIOUS_ID).l
 move.l D2,(@PROJECT_ID).l
 moveq -1,D0
 move.l D0,(@HELD).l
 moveq 1,D0
 move.l D0,(@UI_DIRTY).l
 bra.w @storage_tick_done
storage_tick_load:
 move.l #128,D3
 move.l A2,D0
 cmp.l (@PENDING_OWNER).l,D0
 bne.w @storage_tick_choose_slot
 move.l (@PENDING_SLOT).l,D3
storage_tick_choose_slot:
 moveq -1,D0
 move.l D0,(@PREVIOUS_ID).l
 move.l D2,(@PROJECT_ID).l
 moveq 0,D0
 move.l D0,(@PENDING_OWNER).l
 move.l D3,D0
 cmpi.l #128,D0
 bls.w @storage_tick_slot
 move.l #128,D0
storage_tick_slot:
 jsr @macro_project_slot
 tst.l (@INITIALIZED).l
 bne.w @storage_tick_normal
 move.l (0x40202448).l,D1
 cmpi.l #1,D1
 bhi.w @storage_tick_normal
 lsl.l #8,D1
 lsl.l #5,D1
 move.l #0x7a000,D0
 add.l D1,D0
storage_tick_normal:
 move.l (@BOOT_RESTORED).l,D4
 moveq 0,D1
 move.l D1,(@INITIALIZED).l
 jsr @macro_load
 move.l (@LOAD_STATUS).l,D0
 cmpi.l #3,D0
 beq.w @storage_tick_failed
 cmpi.l #2,D0
 bne.w @storage_tick_ready
 lea (@TABLE).l,A4
 jsr @macro_clear_table
 moveq 0,D0
 move.l D0,(@DIRTY).l
 moveq 1,D0
 move.l D0,(@UI_DIRTY).l
 move.l D0,(@AUDIO_DIRTY).l
storage_tick_ready:
 moveq 1,D0
 move.l D0,(@INITIALIZED).l
 move.l D0,(@RAM_READY).l
 move.l D0,(@BOOT_RESTORED).l
 bra.w @storage_tick_done
storage_tick_failed:
 ; First boot starts with a known empty RAM table. Storage failure does not
 ; revoke its availability. Never retry/re-publish over subsequent RAM edits.
 ; A failed different-project replacement still quarantines old-owner bytes.
 moveq -1,D0
 move.l D0,(@HELD).l
 move.l D0,(@INITIALIZED).l
 moveq 0,D0
 move.l D0,(@AUDIO_PTR).l
 tst.l D4
 bne.w @storage_failed_owner
 moveq 1,D0
 move.l D0,(@RAM_READY).l
 move.l D0,(@BOOT_RESTORED).l
 bra.w @storage_tick_done
storage_failed_owner:
 move.l D0,(@RAM_READY).l
 moveq 3,D0
 move.l D0,(@ERROR).l
 bra.w @storage_tick_done
storage_guard_failed:
 moveq 2,D0
 move.l D0,(@ERROR).l
 moveq -1,D0
 move.l D0,(@INITIALIZED).l
 move.l D0,(@HELD).l
 moveq 0,D0
 move.l D0,(@AUDIO_PTR).l
 move.l D0,(@RAM_READY).l
storage_tick_done:
 movem.l (SP),{ D2 D3 D4 A2 A4}
 lea (20,SP),SP
 rts

macro_project_load:
 lea (-16,SP),SP
 movem.l { D2 D3 D4 A2},(SP)
 move.l (24,SP),D3
 move.l (28,SP),D4
 move.l (32,SP),-(SP)
 move.l D4,-(SP)
 move.l D3,-(SP)
 move.l (32,SP),-(SP)
 jsr @project_load_original
 lea (16,SP),SP
 move.l D0,D2
 move.l D3,D1
 moveq 8,D0
 jsr @macro_diag
 move.l D2,D0
 tst.b D0
 beq.w @project_load_done
 cmpi.l #128,D3
 bhi.w @project_load_done
 ; Same-project temporary cache refreshes must not replace unsaved scenes
 ; with an older checkpoint. FUNC+NO is handled by the partial reload hook.
 tst.l (@RAM_READY).l
 beq.w @project_load_pending
 movea.l D4,A0
 move.l (8,A0),D0
 cmp.l (@PROJECT_ID).l,D0
 beq.w @project_load_done
project_load_pending:
 move.l D4,(@PENDING_OWNER).l
 move.l D3,(@PENDING_SLOT).l
 moveq -1,D0
 move.l D0,(@HELD).l
project_load_done:
 move.l D2,D0
 movem.l (SP),{ D2 D3 D4 A2}
 lea (16,SP),SP
 rts
project_load_original:
 lea (-0x20,SP),SP
 movem.l { D2 D3 A2},(SP)
 jmp 0x40092488

macro_project_save:
 lea (-20,SP),SP
 movem.l { D2 D3 A2},(SP)
 move.l (24,SP),D2
 move.l (28,SP),D3
 lea (12,SP),A0
 jsr @macro_io_lock
 ; Native boot/load workers can save the temporary project before the
 ; next UI tick. Synchronize macro ownership before that checkpoint.
 cmp.l (@PROJECT_GLOBAL).l,D2
 bne.w @project_save_initialized
 jsr @macro_storage_tick
project_save_initialized:
 move.l (32,SP),-(SP)
 move.l D3,-(SP)
 move.l D2,-(SP)
 jsr @project_save_original
 lea (12,SP),SP
 move.l D0,(@SAVE_RESULT).l
 move.l D0,D1
 moveq 4,D0
 jsr @macro_diag
 move.l (@SAVE_RESULT).l,D0
 tst.b D0
 beq.w @project_save_done
 cmp.l (@PROJECT_GLOBAL).l,D2
 bne.w @project_save_done
 move.l D3,D0
 jsr @macro_project_slot
 tst.l D0
 beq.w @project_save_done
 move.l (@INITIALIZED).l,D1
 cmpi.l #1,D1
 bne.w @project_save_done
 movea.l D2,A0
 movea.l (16,A0),A0
 move.l (8,A0),D1
 move.l D1,(@PROJECT_ID).l
 moveq 0,D1
 jsr @macro_store

project_save_done:
 move.l (@SAVE_RESULT).l,D2
 pea (12,SP)
 jsr 0x401385e6
 addq.l #4,SP
 move.l D2,D0
 movem.l (SP),{ D2 D3 A2}
 lea (20,SP),SP
 rts
project_save_original:
 lea (-0x34,SP),SP
 movem.l { D2 D3 D4 A2 A3 A4 A5 A6},(SP)
 jmp 0x40016932

; Preserve native register context. D3 already points at native slot +111*64.
; Return to old-slot invalidation only after macro table/header commit.
macro_shutdown:
 lea (-56,SP),SP
 movem.l { D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5},(SP)
 move.l (@INITIALIZED).l,D0
 cmpi.l #1,D0
 bne.w @shutdown_unready
 move.l D3,D0
 subi.l #0x1bc0,D0
 moveq 1,D1
 jsr @macro_store
shutdown_unready:
 movem.l (SP),{ D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5}
 lea (56,SP),SP
 moveq 1,D1
 move.l (0x40202448).l,D0
 jmp 0x4008da2a

; Sparse on disk, dense in RAM: each occupied pattern keeps its 4096-byte row.
; At most 16 data chunks; ordinary small projects need one data chunk.
macro_pack:
 lea (-28,SP),SP
 movem.l { D2 D3 D4 D5 A2 A3 A4},(SP)
 movea.l A2,A0
 movea.l A4,A2
 movea.l A0,A4
 moveq 0,D2
 moveq 0,D3
pack_pattern:
 movea.l A2,A0
 move.l #1024,D1
 moveq 0,D0
pack_scan:
 or.l (A0)+,D0
 subq.l #1,D1
 bne.w @pack_scan
 tst.l D0
 beq.w @pack_next
 move.l D2,D0
 lsr.l #3,D0
 lea (36,A4),A0
 adda.l D0,A0
 move.l D2,D1
 andi.l #7,D1
 bset.b D1,(A0)
 movea.l A2,A0
 move.l #1024,D1
pack_copy:
 move.l (A0)+,(A3)+
 subq.l #1,D1
 bne.w @pack_copy
 addq.l #1,D3
pack_next:
 adda.l #4096,A2
 addq.l #1,D2
 cmpi.l #128,D2
 bne.w @pack_pattern
 move.l D3,(32,A4)
 ; Only the final chunk's padding needs clearing; emitted rows overwrite
 ; every other packed byte. A full-table clear would waste shutdown time.
 move.l D3,D0
 andi.l #7,D0
 beq.w @pack_no_padding
 moveq 8,D1
 sub.l D0,D1
 lsl.l #8,D1
 lsl.l #2,D1
 movea.l A3,A0
 moveq 0,D0
pack_pad_word:
 move.l D0,(A0)+
 subq.l #1,D1
 bne.w @pack_pad_word
pack_no_padding:
 addq.l #7,D3
 lsr.l #3,D3
 move.l D3,(52,A4)
 movem.l (SP),{ D2 D3 D4 D5 A2 A3 A4}
 lea (28,SP),SP
 rts

macro_unpack_rows:
 lea (-28,SP),SP
 movem.l { D2 D3 D4 D5 A2 A3 A4},(SP)
 movea.l A4,A2
 lea (@HEADER).l,A4
 move.l (32,A4),D0
 cmpi.l #128,D0
 bhi.w @unpack_rows_error
 addq.l #7,D0
 lsr.l #3,D0
 cmp.l (52,A4),D0
 bne.w @unpack_rows_error
 lea (@PACK).l,A3
 moveq 0,D2
 moveq 0,D3
unpack_rows_pattern:
 move.l D2,D0
 lsr.l #3,D0
 lea (36,A4),A0
 adda.l D0,A0
 move.l D2,D1
 andi.l #7,D1
 moveq 0,D0
 move.b (A0),D0
 btst.l D1,D0
 beq.w @unpack_rows_next
 addq.l #1,D3
 cmp.l (32,A4),D3
 bhi.w @unpack_rows_error
 movea.l A2,A0
 move.l #1024,D1
unpack_rows_copy:
 move.l (A3)+,(A0)+
 subq.l #1,D1
 bne.w @unpack_rows_copy
unpack_rows_next:
 adda.l #4096,A2
 addq.l #1,D2
 cmpi.l #128,D2
 bne.w @unpack_rows_pattern
 cmp.l (32,A4),D3
 bne.w @unpack_rows_error
 moveq 0,D0
 bra.w @unpack_rows_done
unpack_rows_error:
 moveq 1,D0
unpack_rows_done:
 movem.l (SP),{ D2 D3 D4 D5 A2 A3 A4}
 lea (28,SP),SP
 rts

; Use the existing recursive MMC-manager mutex around complete extension
; transactions. Individual driver locks are insufficient for shared scratch.
; Polling shutdown bypasses this helper and never depends on RTOS state.
; A0=8-byte ScopedLock storage, D0/D1/A0/A1 scratch.
macro_io_lock:
 move.l A2,-(SP)
 movea.l A0,A2
 jsr 0x40137822
 addi.l #0x14f74,D0
 move.l D0,-(SP)
 move.l A2,-(SP)
 jsr 0x401385c0
 addq.l #8,SP
 movea.l (SP)+,A2
 rts
