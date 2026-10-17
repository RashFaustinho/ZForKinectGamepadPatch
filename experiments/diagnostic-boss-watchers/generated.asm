825ebe40 lis r11, -0x7d9b
825ebe44 lwz r11, -0x6d68(r11)
825ebe48 cmpwi r11, 0
825ebe4c beq 0x825ebf2c
825ebe50 lwz r11, 0x54(r11)
825ebe54 cmpwi r11, 0
825ebe58 beq 0x825ebf2c
825ebe5c lwz r11, 0xc(r11)
825ebe60 cmpwi r11, 1
825ebe64 bne 0x825ebf2c
825ebe68 lis r11, -0x7d9b
825ebe6c lwz r11, -0x6e28(r11)
825ebe70 cmpwi r11, 0
825ebe74 beq 0x825ebf2c
825ebe78 lwz r10, 0x24(r11)
825ebe7c cmpwi r10, 0
825ebe80 beq 0x825ebf2c
825ebe84 lis r9, -0x7d9b
825ebe88 lwz r9, -0x6f24(r9)
825ebe8c cmpwi r9, 0
825ebe90 beq 0x825ebf2c
825ebe94 lwz r9, 0x98(r9)
825ebe98 cmpwi r9, 0
825ebe9c beq 0x825ebf2c
825ebea0 lis r7, -0x7da1
825ebea4 addi r7, r7, -0x4500
825ebea8 lis r11, -0x7da2
825ebeac ori r11, r11, 0xbfc0
825ebeb0 li r6, 0x43
825ebeb4 mtctr r6
825ebeb8 lhz r8, 0(r11)
825ebebc cmpwi r8, 0
825ebec0 beq 0x825ebf10
825ebec4 lwz r5, 0(r7)
825ebec8 lwz r4, 4(r7)
825ebecc cmpwi r4, 0x1000
825ebed0 beq 0x825ebee4
825ebed4 cmpwi r4, 0x1004
825ebed8 beq 0x825ebef0
825ebedc lwzx r4, r9, r4
825ebee0 b 0x825ebef8
825ebee4 lis r6, -0x7d99
825ebee8 lwz r4, -0x1e54(r6)
825ebeec b 0x825ebef8
825ebef0 lis r6, -0x7d99
825ebef4 lwz r4, -0x1e50(r6)
825ebef8 and. r4, r4, r5
825ebefc beq 0x825ebf08
825ebf00 li r4, 3
825ebf04 b 0x825ebf0c
825ebf08 li r4, 0
825ebf0c stwx r4, r10, r8
825ebf10 addi r7, r7, 8
825ebf14 addi r11, r11, 2
825ebf18 bdnz 0x825ebeb8
825ebf1c lis r11, -0x7d99
825ebf20 lwz r7, -0x1e44(r11)
825ebf24 addi r7, r7, 1
825ebf28 stw r7, -0x1e44(r11)
825ebf2c b 0x825eb600
