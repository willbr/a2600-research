start:  LDA #$05    ; Load 5 into accumulator
        ADC #$03    ; Add 3
        STA $20     ; Store result in zero page
        JMP start   ; Loop forever

