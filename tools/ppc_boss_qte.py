"""Translate RT into the camera-derived input used by type-6 boss QTEs.

Only the input read changes. The original routine still accumulates progress,
checks its threshold, advances the gesture step, and can time out normally.
Other battle kinds retain the original camera implementation.
"""
import struct

ENTRY = 0x825EB680
HOOK = 0x8211A430


def build():
    words = []; labels = {}; fixups = []
    def emit(word): words.append(word)
    def d(op, rt, ra, imm): emit(op << 26 | rt << 21 | ra << 16 | (imm & 65535))
    def cmp(r, n): d(11, 0, r, n)
    def jump(label, opcode=0x41820000):
        fixups.append((len(words), label)); emit(opcode)
    def branch(target): emit(0x48000000 | ((target - ENTRY - len(words)*4) & 0x3fffffc))
    d(15, 11, 0, 0x8265); d(32, 11, 11, -0x6d68)
    cmp(11, 0); jump('native')
    d(32, 11, 11, 0x54); cmp(11, 0); jump('native')
    d(32, 11, 11, 0xc); cmp(11, 1); jump('native', 0x40820000)
    d(15, 11, 0, 0x8265); d(32, 11, 11, -0x6f24)
    cmp(11, 0); jump('inactive')
    d(32, 11, 11, 0x98); cmp(11, 0); jump('inactive')
    d(32, 11, 11, 0x20); d(28, 11, 11, 0x800)
    jump('ready', 0x48000000)
    labels['inactive'] = len(words); d(14, 11, 0, 0)
    labels['ready'] = len(words)
    d(15, 10, 0, 0x820e); d(14, 10, 10, 0x6c10)
    branch(0x8211A450)  # native compare, progress update and success threshold
    labels['native'] = len(words)
    d(15, 11, 0, 0x8265); branch(HOOK + 4)  # replay original entry instruction
    for index, label in fixups:
        words[index] |= ((labels[label] - index)*4) & 0xfffc
    return b''.join(struct.pack('>I', word) for word in words)
