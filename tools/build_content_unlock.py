"""Build the optional all-content variant, including a pad-operated card reader.

Uses the native unlock initializer and preserves the player's current custom
fighter and active bonus. It does not change battle HP, QTE outcomes, or scores.
The original QR camera worker is no longer created by the replacement reader;
its executable body hosts the unlock adapter.
"""
import hashlib
import json
import struct
import tomllib
from pathlib import Path
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN
from ppc_emit import Assembler

ROOT = Path(__file__).resolve().parents[1]
IMAGE = Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin')
QR = 0x82302220
UNLOCK = 0x82302508
MENU = 0x822FC450
TABLE = 0x8210EC00
STATE = 0x8266E1C0


def reader():
    a = Assembler(QR)
    a.lwz(11, 0, 3); a.cmp(11, 3); a.jump('one')
    a.pointer(11, 0x826490dc); a.lwz(11, 0, 11)
    a.cmp(11, 0); a.jump('zero')
    a.lwz(11, 0x98, 11); a.cmp(11, 0); a.jump('zero')
    a.lwz(8, 0x28, 11)
    a.andi(9, 8, 0x20); a.jump('zero', 0x40820000)  # B keeps native back
    a.andi(9, 8, 0xf40); a.jump('zero')
    a.pointer(10, STATE); a.lwz(7, 4, 10)
    a.emit(0x28070055); a.jump('index_ok', 0x41800000)  # unsigned < 85
    a.li(7, 0)
    a.label('index_ok')
    a.andi(9, 8, 0xc00); a.jump('characters')
    a.cmp(7, 67); a.jump('power_first', 0x41800000)
    a.cmp(7, 79); a.jump('power_first', 0x40800000)
    a.andi(9, 8, 0x800); a.jump('power_previous')
    a.d(14, 7, 7, 1); a.cmp(7, 79); a.jump('selected', 0x41800000)
    a.li(7, 67); a.jump('selected', 0x48000000)
    a.label('power_previous')
    a.d(14, 7, 7, -1); a.cmp(7, 67); a.jump('selected', 0x40800000)
    a.li(7, 78); a.jump('selected', 0x48000000)
    a.label('power_first')
    a.li(7, 67); a.andi(9, 8, 0x800); a.jump('selected', 0x40820000)
    a.li(7, 78); a.jump('selected', 0x48000000)
    a.label('characters')
    a.andi(9, 8, 0x200); a.jump('previous')
    a.d(14, 7, 7, 1); a.cmp(7, 85); a.jump('selected', 0x41800000)
    a.li(7, 0); a.jump('selected', 0x48000000)
    a.label('previous')
    a.andi(9, 8, 0x100); a.jump('selected')
    a.d(14, 7, 7, -1); a.cmp(7, 0); a.jump('selected', 0x40800000)
    a.li(7, 84)
    a.label('selected')
    a.stw(7, 4, 10); a.d(7, 9, 7, 8); a.pointer(11, TABLE)
    a.emit(0x7d2b4a14)  # add r9,r11,r9
    a.lwz(4, 0, 9); a.lwz(5, 4, 9)
    a.stw(4, 0xc, 3); a.stw(5, 0x10, 3)
    a.li(9, 0); a.stw(9, 0x14, 3)
    a.li(9, 1); a.stw(9, 0x18, 3)
    a.li(9, 3); a.stw(9, 0, 3)
    a.label('one'); a.li(3, 1); a.emit(0x4e800020)
    a.label('zero'); a.li(3, 0); a.emit(0x4e800020)
    return a.finish()


def unlock():
    a = Assembler(UNLOCK)
    a.emit(0x7c0802a6); a.stw(0, -8, 1); a.d(37, 1, 1, -0x80)
    a.stw(3, 0x70, 1)
    a.pointer(11, 0x8264920c); a.lwz(11, 0, 11)
    a.cmp(11, 0); a.jump('out')
    a.lwz(11, 0, 11); a.cmp(11, 0); a.jump('out')
    a.stw(11, 0x6c, 1); a.lwz(9, 0x2eec, 11); a.stw(9, 0x68, 1)
    for i in range(6):
        a.lwz(9, 0x2f00+i*4, 11); a.stw(9, 0x40+i*4, 1)
    a.d(14, 3, 11, 0x20); a.branch(0x821befc0, link=True)
    a.lwz(11, 0x6c, 1)
    for i in range(6):
        a.lwz(9, 0x40+i*4, 1); a.stw(9, 0x2f00+i*4, 11)
    a.lwz(8, 0x68, 1); a.ori(9, 8, 5); a.stw(9, 0x2eec, 11)
    a.andi(9, 8, 1); a.jump('custom_ok', 0x40820000)
    for offset, value in ((0x2ef4, 23), (0x2ef8, 391), (0x2efc, 391)):
        a.li(9, value); a.stw(9, offset, 11)
    a.label('custom_ok')
    a.andi(9, 8, 4); a.jump('finish', 0x40820000)
    a.li(9, 0); a.stw(9, 0x2f00, 11)
    a.label('finish')
    a.pointer(10, STATE); a.lwz(9, 8, 10); a.cmp(9, 1); a.jump('out')
    a.pointer(9, 0x82649358); a.lwz(9, 0, 9); a.cmp(9, 0); a.jump('out')
    a.li(11, 1); a.stw(11, 8, 9); a.stw(11, 8, 10)
    a.label('out')
    a.lwz(3, 0x70, 1); a.lwz(0, 0x78, 1); a.d(14, 1, 1, 0x80)
    a.emit(0x7c0803a6); a.emit(0x7d8802a6)  # restore LR, replay mflr r12
    a.branch(MENU+4)
    return a.finish()


def build():
    source = ROOT/'experiments/gamepad-layout-v2/4E4D084E.virtual-player.patch.toml'
    catalog = json.loads((ROOT/'experiments/content-unlock/catalog.json').read_text())
    entries = catalog['qr_entries']; assert len(entries) == 85
    image = IMAGE.read_bytes()
    original = [(QR, 608), (UNLOCK, 620)]
    # Pin complete overwritten routines to the analyzed original, not just a prologue.
    expected = {QR: '63f5b7e39219c47a5101c68bb6e37b33c371da4a542e1d8e8d8de48760eee8db',
                UNLOCK: '0c398166ea647ca593d0b5d2794fbd11e349a66e864b8e27a46b34a92e4fb609'}
    for address, size in original:
        if hashlib.sha256(image[address-0x82000000:address-0x82000000+size]).hexdigest() != expected[address]:
            raise ValueError('Unsupported original QR implementation')
    if image[MENU-0x82000000:MENU-0x82000000+4] != bytes.fromhex('7d8802a6'):
        raise ValueError('Main-menu constructor hook mismatch')
    table = b''.join(struct.pack('>2I', e['code'], e['argument']) for e in entries)
    if any(image[TABLE-0x82000000:TABLE-0x82000000+len(table)]) or any(image[STATE-0x82000000:STATE-0x82000000+16]):
        raise ValueError('Expected catalog/state padding is occupied')
    codes = [(QR, reader(), 608), (UNLOCK, unlock(), 620)]
    text = source.read_text()
    text = text.replace('EXPERIMENT: controller action bridge', 'EXPERIMENT: gamepad and optional all-content unlock')
    for address, code, limit in codes:
        if len(code) > limit: raise ValueError('Adapter exceeds the replaced camera routine')
        instructions = list(Cs(CS_ARCH_PPC, CS_MODE_32|CS_MODE_BIG_ENDIAN).disasm(code, address))
        if len(instructions)*4 != len(code): raise ValueError('Invalid adapter instructions')
        text += f'\n[[patch.array]]\naddress = 0x{address:08X}\nvalue = "{code.hex()}"\n'
    for address, data in ((TABLE, table), (STATE, b'QRP1'+bytes(12))):
        text += f'\n[[patch.array]]\naddress = 0x{address:08X}\nvalue = "{data.hex()}"\n'
    a = Assembler(MENU); a.branch(UNLOCK)
    text += f'\n[[patch.be32]]\naddress = 0x{MENU:08X}\nvalue = 0x{a.words[0]:08X}\n'
    tomllib.loads(text)
    out = ROOT/'experiments/gamepad-unlocked'; out.mkdir(exist_ok=True)
    (out/'4E4D084E.gamepad-unlocked.patch.toml').write_text(text)
    (out/'manifest.json').write_text(json.dumps({'status':'experimental; optional persistent content unlock',
        'base_patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'qr_codes':len(entries),'native_unlock_initializer':'821BEFC0',
        'replaced_camera_functions':{hex(a):len(c) for a,c,_ in codes},
        'scope':'Content availability; preserves selected fighter/bonus, HP, scores and native QTE outcomes'},indent=2)+'\n')
    print(out)


if __name__ == '__main__': build()
