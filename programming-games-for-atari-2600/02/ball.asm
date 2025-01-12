;
; Ball demo
;
; by Oscar Toledo G.
; http://nanochess.org
;
    ; Creation date: Jun/01/2022.
;

processor 6502
include "vcs.h"

    org $f000
start:
    sei
    cld
    ldx #$ff
    txs
    lda #$00
clear:
    sta 0,x
    dex
    bne clear

show_frame:
    lda #$88 ; blue
    sta colubk ; background colour
    lda #$0f ; white
    sta colupf ; playfield colour

    sta wsync
    lda #2      ; start of vertical retrace
    sta vsync
    sta vsync
    sta vsync
    sta vsync
    lda #0     ; end of vertial retrace
    sta vsync

    ; Ball horizontal position (23 NOPs for center)
    sta wsync ; cycle 3
    nop ; 5
    nop ; 7
    nop ; 9
    nop ; 11
    nop ; 13
    nop ; 15
    nop ; 17
    nop ; 19
    nop ; 21
    nop ; 23
    nop ; 25
    nop ; 27
    nop ; 29
    nop ; 31
    nop ; 33
    nop ; 35
    nop ; 37
    nop ; 39
    nop ; 41
    nop ; 43
    nop ; 45
    nop ; 47
    nop ; 49
    sta resbl ; 52

    ldx #35
top:
    sta wsync
    dex
    bne top
    lda #0
    sta vblank
    ldx #95
visible:
    sta wsync
    dex
    bne visible
    sta wsync  ; one scanline
    lda #$02   ; ball enable
    sta enabl

    sta wsync ; one scanline
    lda #$00
    sta enabl

    lda #$f8   ; sand colour
    sta colubk
    ldx #95    ; 95 scanlines
visible2:
    sta wsync
    dex
    bne visible2
    lda #2     ; enable blanking
    sta vblank
    ldx #30    ; 30 scanlines of bottom border
bottom:
    sta wsync
    dex
    bne bottom

    jmp show_frame

    org $fffc
    .word start
    .word start


