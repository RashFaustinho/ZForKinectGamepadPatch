"""Select Xenia's simulated HDD without invoking a Kinect system dialog.

Only device selection is replaced. Signed-in profile validation, native file
I/O, error handling and save checksums remain in the game/emulator.
"""
from ppc_emit import Assembler

ENTRY = 0x82193038


def build():
    a = Assembler(ENTRY)
    a.li(11, 0); a.stw(11, 0, 3)
    a.pointer(11, 0x82649180); a.lwz(11, 0, 11)
    a.cmp(11, 0); a.jump('fail')
    a.lwz(9, 0x21c, 11); a.emit(0x28090004); a.jump('fail', 0x40800000)
    a.d(7, 9, 9, 0x38); a.emit(0x7d2b4a14); a.lwz(9, 0x28, 9)
    a.cmp(9, 0); a.jump('fail')
    a.li(11, 1)
    for off in (0, 0x24, 0x2c, 0x30): a.stw(11, off, 3)
    a.li(11, 0)
    for off in (4, 8, 12, 0x28): a.stw(11, off, 3)
    a.li(3, 1); a.emit(0x4e800020)
    a.label('fail'); a.li(3, 0); a.emit(0x4e800020)
    return a.finish()
