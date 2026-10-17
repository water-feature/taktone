.include "os153.inc"
.section .run,"ax"
        .balign 4
        .globl ds_machine
ds_machine:
        .long   7, ds_name, ds_short, ds_icon_bmp, 3, 7
ds_name: .asciz "SOPHIE"
ds_short: .asciz "SOPH"
        .balign 4
ds_icon_bmp:
        .long BMP_VT, 11, 7, 1, ds_icon_px, ds_icon_mask, 0
ds_icon_px:
        .long 0x10400000,0x28a00000,0x55400000,0xaa800000
        .long 0x55400000,0x28a00000,0x10400000,0x00000000
        .long 0x00000000,0x00000000,0x00000000
ds_icon_mask:
        .long 0xfe000000,0xfe000000,0xfe000000,0xfe000000
        .long 0xfe000000,0xfe000000,0xfe000000,0x00000000
        .long 0x00000000,0x00000000,0x00000000

| Dedicated SOPHIE SRC layout. Seven synthesis controls retain native storage;
| D is unassigned.
        .equ DS_ID,7
        .equ P_TUNE,0x84
        .equ P_MODEL,0x85
        .equ P_BR,0x86
        .equ P_SAMP,0x87
        .equ P_SWEEP,0x88
        .equ P_METAL,0x89
        .equ P_FEEDBACK,0x8a
        .equ P_COLOR,0x8b
        .section .bss,"aw"
        .balign 4
        .globl ds_page_m
ds_page_m: .long 0
ds_lay_ok: .long 0
ds_lay: .space 44
ds_txt: .space 12
        .section .run,"ax"
        .globl ds_layout
ds_layout:
        move.l 4(%sp),%d0
        move.l %d0,ds_page_m
        cmpi.l #DS_ID,%d0
        beq.s 1f
        moveq #3,%d1
        jmp LAYOUT_ON
1:      tst.l ds_lay_ok
        bne.s 3f
        lea LAY_SLICE,%a0
        lea ds_lay,%a1
        moveq #11,%d0
2:      move.l (%a0)+,(%a1)+
        subq.l #1,%d0
        bne.s 2b
        moveq #1,%d0
        move.l %d0,ds_lay_ok
3:      move.l #ds_lay,%d0
        rts

ds_pick:
        moveq #DS_ID,%d1
        cmp.l ds_page_m,%d1
        bne.s 8f
        move.l 12(%sp),%d0
        subi.l #P_TUNE,%d0
        cmpi.l #7,%d0
        bhi.s 8f
        lsl.l #2,%d0
        move.l 0(%a0,%d0.l),%d0
        rts
8:      moveq #0,%d0
        rts
        .globl ds_lab_short,ds_lab_long
ds_lab_short:
        lea ds_short_tab,%a0
        bsr.s ds_pick
        bne.s 9f
        move.l 8(%sp),%d1
        cmpi.l #164,%d1
        jmp LAB_SHORT_ON
ds_lab_long:
        lea ds_long_tab,%a0
        bsr.s ds_pick
        bne.s 9f
        move.l 8(%sp),%d1
        cmpi.l #164,%d1
        jmp LAB_LONG_ON
9:      rts

| The LFO destination renderer reads the shared SLICE parameter descriptor
| directly, bypassing ds_lab_short.  Keep its target ID and drawing path,
| replacing only the displayed name while Sophie's layout is active.
        .globl ds_lfo_label
ds_lfo_label:
        moveq #DS_ID,%d1
        cmp.l ds_page_m,%d1
        bne.s 8f
        move.l %d0,%d1              | mapped destination parameter ID
        subi.l #P_TUNE,%d1
        cmpi.l #7,%d1
        bhi.s 8f
        lsl.l #2,%d1
        lea ds_short_tab,%a0
        move.l 0(%a0,%d1.l),%d1
        beq.s 8f                   | SAMP keeps its stock label
        lea DESC_TAB,%a0
        move.l %d1,(%sp)            | replace the stock name argument
        jmp LFO_LABEL_ON             | resume drawing at the next instruction
8:      lea DESC_TAB,%a0
        jmp LFO_LABEL_ORIG             | original descriptor lookup

| The destination popup formats rows separately as MACHINE:Parameter.
| Its first and fallback draws both need Sophie's full parameter names.
ds_chooser_name:
        move.l %d1,-(%sp)
        move.l %a0,-(%sp)
        move.l %d0,%d1              | descriptor byte offset
        subi.l #(P_TUNE*52),%d1
        cmpi.l #(7*52),%d1
        bhi.s 1f
        moveq #DS_ID,%d0
        cmp.l ds_page_m,%d0
        bne.s 1f
        divu #52,%d1
        andi.l #0xffff,%d1
        lsl.l #2,%d1
        lea ds_chooser_tab,%a0
        move.l 0(%a0,%d1.l),%d0
        move.l #ds_short,%d6
        bra.s 2f
1:      lea DESC_TAB_40,%a0          | descriptor table +40
        move.l 0(%a0,%d0.l),%d0
2:      move.l (%sp)+,%a0
        move.l (%sp)+,%d1
        rts
        .globl ds_lfo_popup_name,ds_lfo_popup_fallback
ds_lfo_popup_name:
        bsr ds_chooser_name
        move.l %d0,-(%sp)
        move.l %d6,-(%sp)
        jmp POPUP_NAME_ON
ds_lfo_popup_fallback:
        move.l %d2,%d0
        bsr ds_chooser_name
        move.l %d0,-(%sp)
        move.l %d6,-(%sp)
        jmp POPUP_FALLBACK_ON

| The LFO overview uses descriptor fields +44 and +48 for its two-line DEST.
        .globl ds_lfo_overview_group,ds_lfo_overview_name
ds_lfo_overview_group:
        move.l %d1,-(%sp)
        moveq #DS_ID,%d1
        cmp.l ds_page_m,%d1
        bne.s 1f
        cmpi.l #P_TUNE,%d3
        bcs.s 1f
        cmpi.l #P_COLOR,%d3
        bhi.s 1f
        move.l #ds_short,%d0
        bra.s 2f
1:      move.l 44(%a0,%d0.l),%d0
2:      move.l (%sp)+,%d1
        move.l %d0,-(%sp)
        move.l %d2,-(%sp)
        jmp OVERVIEW_GROUP_ON
ds_lfo_overview_name:
        moveq #52,%d0
        muls.l %d0,%d3
        move.l %d1,-(%sp)
        move.l %a0,-(%sp)
        move.l %d3,%d1
        divu #52,%d1
        andi.l #0xffff,%d1
        moveq #DS_ID,%d0
        cmp.l ds_page_m,%d0
        bne.s 1f
        subi.l #P_TUNE,%d1
        cmpi.l #7,%d1
        bhi.s 1f
        lsl.l #2,%d1
        lea ds_overview_tab,%a0
        move.l 0(%a0,%d1.l),%d0
        bra.s 2f
1:      lea DESC_TAB_48,%a0          | descriptor table +48
        move.l 0(%a0,%d3.l),%d0
2:      move.l (%sp)+,%a0
        move.l (%sp)+,%d1
        move.l %d0,-(%sp)
        jmp OVERVIEW_NAME_ON

ds_is_control:
        moveq #DS_ID,%d1
        cmp.l ds_page_m,%d1
        bne.s 8f
        cmpi.l #P_TUNE,%d0
        bcs.s 8f
        cmpi.l #P_COLOR,%d0
        bhi.s 8f
        cmpi.l #P_BR,%d0
        beq.s 8f
        moveq #1,%d1
        rts
8:      moveq #0,%d1
        rts
        .globl ds_knob_gfx
ds_knob_gfx:
        move.l 8(%sp),%d0
        cmpi.l #P_SAMP,%d0
        bne.s ds_knob_active
        moveq #DS_ID,%d1
        cmp.l ds_page_m,%d1
        beq.s ds_knob_empty
ds_knob_active:
        bsr.s ds_is_control
        beq.s 2f
        cmpi.l #P_TUNE,%d0
        beq.s 2f
        cmpi.l #P_MODEL,%d0
        beq.s 5f
        cmpi.l #P_SWEEP,%d0
        beq.s 3f
1:      move.l #P_BR,%d0
        bra.s 4f
3:      move.l #P_TUNE,%d0
        bra.s 4f
5:      move.l 12(%sp),%d0
        lsr.l #3,%d0
        mulu.w #42,%d0
        move.l %d0,12(%sp)
        move.l #P_BR,%d0              | ordinary four-position knob
4:
        move.l %d0,8(%sp)
2:      lea -20(%sp),%sp
        movem.l %d2-%d6,(%sp)
        jmp KNOB_GFX_ON
ds_knob_empty:
        rts
        .globl ds_ui_rec
ds_ui_rec:
        move.l 4(%sp),%d0
        bsr.w ds_is_control
        beq.s 1f
        cmpi.l #P_TUNE,%d0
        beq.s 1f
        cmpi.l #P_MODEL,%d0
        beq.s 4f
        cmpi.l #P_SWEEP,%d0
        beq.s 3f
        move.l #P_BR,%d1
        bra.s 2f
3:      move.l #P_TUNE,%d1
        bra.s 2f
4:      move.l #P_BR,%d1              | ordinary four-position knob
        bra.s 2f
1:      move.l 4(%sp),%d1
2:      cmpi.l #164,%d1
        jmp UI_REC_ON

| Range lookup is reached by display, stepper, setter and validator.
        .globl ds_prange,ds_prange_f
ds_prange:
        movea.l %a2,%a1
        bra.s 1f
ds_prange_f:
        movea.l 36(%sp),%a1
1:      move.l %a1,-(%sp)
        move.l %a0,-(%sp)
        move.l 12(%sp),-(%sp)
        jsr PRANGE_FN
        addq.l #4,%sp
        movea.l (%sp)+,%a0
        movea.l (%sp)+,%a1
        move.l 4(%sp),%d1
        cmpi.l #P_MODEL,%d1
        bcs.s 9f
        cmpi.l #P_COLOR,%d1
        bhi.s 9f
        move.l (%a1),%d0
        cmpi.l #PARAM_VT,%d0
        bne.s 9f
        movea.l 16(%a1),%a1
        move.l (%a1),%d0
        cmpi.l #SNDREF_VT,%d0
        bne.s 9f
        movea.l 16(%a1),%a1
.global ds_range_sound
ds_range_sound:
        moveq #0,%d0
        move.b 126(%a1),%d0
        cmpi.l #DS_ID,%d0
        bne.s 9f
        cmpi.l #P_SAMP,%d1
        bne.s 8f
        clr.l (%a0)
        clr.l 4(%a0)
        clr.l 8(%a0)                   | unassigned D slot has no editable range
        bra.s 9f
8:
        subi.l #P_MODEL,%d1
        lsl.l #3,%d1
        lea ds_range_tab,%a1
        clr.l (%a0)
        move.l 0(%a1,%d1.l),%d0
        move.l %d0,4(%a0)
        move.l 4(%a1,%d1.l),%d0
        move.l %d0,8(%a0)
9:      move.l %a0,%d0
        rts

        .globl ds_val_text,ds_pop_text
ds_val_text:
        move.l 8(%sp),%d0
        cmpi.l #P_SAMP,%d0
        beq.w ds_empty_val_text
        cmpi.l #P_MODEL,%d0
        beq.s 2f
        cmpi.l #P_SWEEP,%d0
        beq.s 4f
        cmpi.l #P_COLOR,%d0
        beq.s 5f
        cmpi.l #P_FEEDBACK,%d0
        beq.s 5f
        cmpi.l #P_METAL,%d0
        bne.s 1f
5:      move.l #ds_fmt_u7,%a0
        bra.s 3f
4:
        move.l #ds_fmt_sweep,%a0
        bra.s 3f
2:      move.l #ds_fmt_model,%a0
3:
        moveq #DS_ID,%d1
        cmp.l ds_page_m,%d1
        bne.s 1f
        move.l 12(%sp),-(%sp)
        move.l 20(%sp),-(%sp)
        jsr (%a0)
        addq.l #8,%sp
        move.l 16(%sp),%d0
        rts
1:      lea -20(%sp),%sp
        movem.l %d2-%d4/%a2-%a3,(%sp)
        jmp VAL_TEXT_ON
ds_pop_text:
        move.l 4(%sp),%d0
        cmpi.l #P_SAMP,%d0
        beq.w ds_empty_pop_text
        cmpi.l #P_MODEL,%d0
        beq.s 2f
        cmpi.l #P_SWEEP,%d0
        beq.s 4f
        cmpi.l #P_COLOR,%d0
        beq.s 5f
        cmpi.l #P_FEEDBACK,%d0
        beq.s 5f
        cmpi.l #P_METAL,%d0
        bne.s 1f
5:      move.l #ds_fmt_u7,%a0
        bra.s 3f
4:
        move.l #ds_fmt_sweep,%a0
        bra.s 3f
2:      move.l #ds_fmt_model,%a0
3:
        moveq #DS_ID,%d1
        cmp.l ds_page_m,%d1
        bne.s 1f
        move.l 8(%sp),-(%sp)
        pea ds_txt
        jsr (%a0)
        addq.l #8,%sp
        move.l #ds_txt,%d0
        rts
1:      move.l 4(%sp),%d1
        cmpi.l #164,%d1
        jmp POP_TEXT_ON
.global ui_code_end
ui_code_end:
        .balign 4
ds_short_tab: .long ds_s_tune,ds_s_model,ds_s_fold,ds_s_samp,ds_s_sweep,ds_s_metal,ds_s_feedback,ds_s_color
ds_long_tab: .long ds_l_tune,ds_l_model,ds_l_fold,ds_s_samp,ds_l_sweep,ds_l_metal,ds_l_feedback,ds_l_color
ds_chooser_tab: .long ds_l_tune,ds_l_model,ds_l_fold,ds_s_samp,ds_l_sweep,ds_l_metal,ds_l_feedback,ds_l_color
ds_overview_tab: .long ds_s_tune,ds_s_model,ds_s_fold,ds_s_samp,ds_s_sweep,ds_s_metal,ds_s_feedback,ds_s_color
ds_range_tab: .long 0x1f00,0x0000,0x7f00,0x0000,0x7f00,0x2800,0x7f00,0x4000,0x7f00,0x2800,0x7f00,0x2000,0x7f00,0x4000
ds_s_tune: .asciz "TUNE"
ds_s_model: .asciz "MODEL"
ds_s_fold: .asciz "FOLD"
ds_s_samp: .asciz ""
ds_s_color: .asciz "COLOR"
ds_s_metal: .asciz "METAL"
ds_s_sweep: .asciz "SWEEP"
ds_s_feedback: .asciz "FBK"
ds_l_tune: .asciz "Tune"
ds_l_model: .asciz "Model"
ds_l_fold: .asciz "Fold"
ds_l_color: .asciz "Color"
ds_l_metal: .asciz "Metal"
ds_l_sweep: .asciz "Sweep"
ds_l_feedback: .asciz "Feedback"


.balign 2
ds_empty_val_text:
        moveq #DS_ID,%d1
        cmp.l ds_page_m,%d1
        bne.w ds_empty_val_stock
        movea.l 16(%sp),%a0
        clr.b (%a0)
        move.l %a0,%d0
        rts
ds_empty_val_stock:
        lea -20(%sp),%sp
        movem.l %d2-%d4/%a2-%a3,(%sp)
        jmp VAL_TEXT_ON
ds_empty_pop_text:
        moveq #DS_ID,%d1
        cmp.l ds_page_m,%d1
        bne.w ds_empty_pop_stock
        move.l #ds_s_samp,%d0
        rts
ds_empty_pop_stock:
        move.l 4(%sp),%d1
        cmpi.l #164,%d1
        jmp POP_TEXT_ON

| Sample-list comparisons adapted from elekloader machine-pages (GPL-2.0-or-later).
.global ds_samp_d0,ds_samp_d2
ds_samp_d0:
        cmpi.l #0x87,%d0
        bne.s 9f
        bsr.s ds_samp_ours
        bne.s 1f
        tst.l %d0
        rts
1:      cmpi.l #0x87,%d0
9:      rts
ds_samp_d2:
        cmpi.l #0x87,%d2
        bne.s 9f
        bsr.s ds_samp_ours
        bne.s 1f
        tst.l %d2
        rts
1:      cmpi.l #0x87,%d2
9:      rts
ds_samp_ours:
        move.l %d0,-(%sp)
        moveq #7,%d0
        cmp.l ds_page_m,%d0
        movem.l (%sp),%d0
        lea 4(%sp),%sp
        rts


| Native machine-switch defaults: a2 is the track object, not a SRC provider.
.global ds_init_range
ds_init_range:
        move.l %a0,-(%sp)
        move.l 8(%sp),-(%sp)
        jsr PRANGE_FN
        addq.l #4,%sp
        move.l %a2,-(%sp)
        movea.l (%a2),%a1
        movea.l 40(%a1),%a1
        jsr (%a1)
        addq.l #4,%sp
        movea.l %d0,%a1
        movea.l (%sp)+,%a0
        tst.l %a1
        beq.s 1f
        move.l 4(%sp),%d1
        cmpi.l #P_MODEL,%d1
        bcs.s 1f
        cmpi.l #P_COLOR,%d1
        bhi.s 1f
        jmp ds_range_sound
1:      move.l %a0,%d0
        rts

| Scene capture reserves two output longs; use a complete local range object.
.global ds_scene_range
ds_scene_range:
        lea -16(%sp),%sp
        move.l %a0,12(%sp)
        lea (%sp),%a0
        move.l 20(%sp),-(%sp)
        jsr ds_prange
        addq.l #4,%sp
        movea.l 12(%sp),%a1
        move.l (%sp),%d0
        move.l %d0,(%a1)
        move.l 4(%sp),%d0
        move.l %d0,4(%a1)
        movea.l %a1,%a0
        move.l %a0,%d0
        lea 16(%sp),%sp
        rts
.global ui_status_end
ui_status_end:
