"""Small assembler for the integer adapters used by this patch."""
import struct


class Assembler:
    def __init__(self, address):
        self.address = address
        self.words = []
        self.labels = {}
        self.fixups = []

    def emit(self, word): self.words.append(word)
    def d(self, op, rt, ra, imm): self.emit(op << 26 | rt << 21 | ra << 16 | (imm & 65535))
    def li(self, rt, imm): self.d(14, rt, 0, imm)
    def lwz(self, rt, offset, ra): self.d(32, rt, ra, offset)
    def stw(self, rt, offset, ra): self.d(36, rt, ra, offset)
    def cmp(self, reg, imm): self.d(11, 0, reg, imm)
    def andi(self, dest, source, imm): self.d(28, source, dest, imm)
    def ori(self, dest, source, imm): self.d(24, source, dest, imm)
    def label(self, name): self.labels[name] = len(self.words)
    def jump(self, label, opcode=0x41820000):
        self.fixups.append((len(self.words), label)); self.emit(opcode)
    def branch(self, target, link=False):
        delta = target - self.address - len(self.words)*4
        if delta % 4 or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('Branch out of range')
        self.emit(0x48000000 | (delta & 0x3fffffc) | int(link))
    def pointer(self, reg, address):
        self.d(15, reg, 0, (address + 0x8000) >> 16)
        self.d(14, reg, reg, address & 65535)
    def finish(self):
        for index, name in self.fixups:
            delta = (self.labels[name] - index)*4
            unconditional = self.words[index] >> 26 == 18
            limit = 0x2000000 if unconditional else 0x8000
            if not -limit <= delta < limit: raise ValueError('Label out of range')
            self.words[index] |= delta & (0x3fffffc if unconditional else 0xfffc)
        return b''.join(struct.pack('>I', word) for word in self.words)
